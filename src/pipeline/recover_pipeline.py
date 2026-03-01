"""中断状態回復パイプライン.

処理が中断されたストリームを回復可能な状態に戻す。
"""

import logging
from pathlib import Path

from src.constants.stream_status import StreamStatus
from src.repository.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class RecoverPipeline:
    """中断状態回復パイプライン."""

    def __init__(
        self,
        max_retries: int,
        thumbnail_dir: Path,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            thumbnail_dir: サムネイル保存ディレクトリ
            repository: ストリームリポジトリ
        """
        self._max_retries = max_retries
        self._thumbnail_dir = thumbnail_dir
        self._repository = repository

    def recover_all(self) -> int:
        """中断されたストリームを回復する.

        downloading -> discovered: ダウンロードを再試行
        thumbs_done -> downloaded: サムネイルディレクトリが存在しないまたは空の場合
        uploading -> thumbs_done: アップロードを再試行

        Returns:
            回復されたストリーム数
        """
        count = 0

        # downloading状態をdiscoveredに戻す
        downloading_streams = self._repository.get_by_status(StreamStatus.DOWNLOADING)
        for stream in downloading_streams:
            if stream.retry_count >= self._max_retries:
                continue

            updated = self._repository.update_status(
                stream.video_id,
                StreamStatus.DISCOVERED,
                expected_old_status=StreamStatus.DOWNLOADING,
                increment_retry=True,
            )
            if updated:
                logger.info("Recovered stream from downloading: %s", stream.video_id)
                count += 1

        # uploading状態をthumbs_doneに戻す
        uploading_streams = self._repository.get_by_status(StreamStatus.UPLOADING)
        for stream in uploading_streams:
            if stream.retry_count >= self._max_retries:
                continue

            updated = self._repository.update_status(
                stream.video_id,
                StreamStatus.THUMBS_DONE,
                expected_old_status=StreamStatus.UPLOADING,
                increment_retry=True,
            )
            if updated:
                logger.info("Recovered stream from uploading: %s", stream.video_id)
                count += 1

        # thumbs_done状態でサムネイルディレクトリが存在しない場合、downloadedに戻す
        thumbs_done_streams = self._repository.get_by_status(StreamStatus.THUMBS_DONE)
        for stream in thumbs_done_streams:
            if stream.retry_count >= self._max_retries:
                continue

            thumb_dir = self._thumbnail_dir / stream.video_id
            if thumb_dir.exists() and any(thumb_dir.iterdir()):
                continue

            updated = self._repository.update_status(
                stream.video_id,
                StreamStatus.DOWNLOADED,
                expected_old_status=StreamStatus.THUMBS_DONE,
                increment_retry=True,
            )
            if updated:
                logger.info("Recovered stream from thumbs_done: %s", stream.video_id)
                count += 1

        return count
