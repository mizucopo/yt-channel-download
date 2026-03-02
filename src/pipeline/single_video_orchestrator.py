"""1動画単位でパイプライン全体を実行するオーケストレーター.

ストレージ節約のため、1動画の処理が完了した時点でクリーンアップを実行し、
ローカルファイルを削除する。
"""

import logging

from src.constants.stream_status import StreamStatus
from src.notifications.discord_notifier import DiscordNotifier
from src.pipeline.cleanup_pipeline import CleanupPipeline
from src.pipeline.download_pipeline import DownloadPipeline
from src.pipeline.thumbs_pipeline import ThumbsPipeline
from src.pipeline.upload_pipeline import UploadPipeline
from src.repository.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class SingleVideoOrchestrator:
    """1動画単位でパイプライン全体を実行するオーケストレーター."""

    def __init__(
        self,
        repository: StreamRepository,
        download_pipeline: DownloadPipeline,
        thumbs_pipeline: ThumbsPipeline,
        upload_pipeline: UploadPipeline,
        cleanup_pipeline: CleanupPipeline,
        max_retries: int,
        discord_notifier: DiscordNotifier | None = None,
    ) -> None:
        """オーケストレーターを初期化する.

        Args:
            repository: ストリームリポジトリ
            download_pipeline: ダウンロードパイプライン
            thumbs_pipeline: サムネイル抽出パイプライン
            upload_pipeline: アップロードパイプライン
            cleanup_pipeline: クリーンアップパイプライン
            max_retries: 最大リトライ回数
            discord_notifier: Discord通知クライアント（オプション）
        """
        self._repository = repository
        self._download_pipeline = download_pipeline
        self._thumbs_pipeline = thumbs_pipeline
        self._upload_pipeline = upload_pipeline
        self._cleanup_pipeline = cleanup_pipeline
        self._max_retries = max_retries
        self._discord_notifier = discord_notifier

    def process_single_video(self) -> bool:
        """1動画を全ステージで処理する.

        DISCOVERED状態の動画を1件取得し、download → thumbs → upload → cleanup
        の順で処理する。いずれかのステージで失敗した場合は次の動画へ進む。

        Returns:
            処理した動画があればTrue、処理対象がなければFalse
        """
        # DISCOVERED状態の動画を1件取得
        stream = self._repository.get_next_pending(
            StreamStatus.DISCOVERED,
            max_retries=self._max_retries,
        )
        if stream is None:
            return False

        video_id = stream.video_id
        logger.info("Processing video: %s", video_id)

        # Download
        if not self._download_pipeline.download_video(video_id):
            logger.warning("Download failed for %s, skipping to next video", video_id)
            return True  # 処理対象はあった

        # Thumbs
        if not self._thumbs_pipeline.extract_next():
            logger.warning(
                "Thumbnail extraction failed for %s, skipping to next video", video_id
            )
            return True  # 処理対象はあった

        # Upload
        if not self._upload_pipeline.upload_next():
            logger.warning("Upload failed for %s, skipping to next video", video_id)
            return True  # 処理対象はあった

        # Cleanup
        if not self._cleanup_pipeline.cleanup_next():
            logger.warning("Cleanup failed for %s", video_id)
            # クリーンアップ失敗でも処理完了とみなす（次回再試行可能）

        # 全パイプライン完了後にDiscord通知を送信
        if self._discord_notifier:
            updated_stream = self._repository.get(video_id)
            if updated_stream:
                self._discord_notifier.notify_upload_complete(
                    title=updated_stream.title, video_id=video_id
                )

        logger.info("Completed processing video: %s", video_id)
        return True

    def process_all_videos(self) -> int:
        """全動画を1件ずつ処理する.

        処理対象がなくなるまで process_single_video を繰り返す。

        Returns:
            処理した動画数
        """
        count = 0
        while self.process_single_video():
            count += 1
        return count
