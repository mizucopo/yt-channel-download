"""サムネイル抽出パイプライン.

ffmpegを使用して動画からスクリーンショットを抽出する。
"""

import logging
import subprocess
from pathlib import Path

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.base_pipeline import BasePipeline
from src.repository.stream_repository import StreamRepository
from src.utils.path_manager import PathManager

logger = logging.getLogger(__name__)


class ThumbsPipeline(BasePipeline):
    """サムネイル抽出パイプライン."""

    def __init__(
        self,
        max_retries: int,
        thumbnail_interval: int,
        thumbnail_quality: int,
        path_manager: PathManager,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            thumbnail_interval: サムネイル抽出間隔（秒）
            thumbnail_quality: サムネイル画質（1-31、小さいほど高画質）
            path_manager: パスマネージャ
            repository: ストリームリポジトリ
        """
        super().__init__(max_retries, repository)
        self._thumbnail_interval = thumbnail_interval
        self._thumbnail_quality = thumbnail_quality
        self._path_manager = path_manager

    def _get_pending_status(self) -> StreamStatus:
        """処理待ちステータスを取得する."""
        return StreamStatus.DOWNLOADED

    def _get_completed_status(self) -> StreamStatus:
        """完了ステータスを取得する."""
        return StreamStatus.THUMBS_DONE

    def _execute_process(self, video_id: str, stream: Stream) -> bool:
        """サムネイル抽出処理を実行する.

        Args:
            video_id: YouTube動画ID
            stream: ストリーム情報

        Returns:
            処理が成功した場合はTrue
        """
        if stream.local_path is None:
            return False

        # 動画ファイルの存在確認
        video_file = Path(stream.local_path)
        if not self._validate_file_exists(video_file, video_id):
            return False

        # サムネイルディレクトリを作成
        thumb_dir = self._path_manager.get_thumbnail_dir(video_id)

        logger.info(
            "Extracting thumbnails from %s at %d second intervals",
            video_id,
            self._thumbnail_interval,
        )

        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(video_file),
                "-vf",
                f"fps=1/{self._thumbnail_interval}",
                "-q:v",
                str(self._thumbnail_quality),
                str(thumb_dir / "thumb_%08d.jpg"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        if result.returncode != 0:
            logger.error(
                "Thumbnail extraction failed for %s: %s", video_id, result.stderr
            )
            return False

        logger.info("Thumbnail extraction completed: %s", video_id)
        return True

    def _rollback_on_failure(
        self, video_id: str, error_message: str | None = None
    ) -> None:
        """失敗時はリトライカウントを増やす.

        処理中ステータスがないため、ステータス変更は不要。
        """
        self._repository.update_status(
            video_id,
            self._get_pending_status(),
            expected_old_status=self._get_pending_status(),
            error_message=error_message,
            increment_retry=True,
        )

    def extract_next(self) -> bool:
        """次の待機中の動画からサムネイルを抽出する.

        Returns:
            抽出対象があった場合はTrue
        """
        return self.process_next()
