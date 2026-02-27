"""サムネイル抽出パイプライン.

ffmpegを使用して動画からスクリーンショットを抽出する。
"""

import logging
import subprocess
from pathlib import Path

from src.models.stream_status import StreamStatus
from src.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class ThumbsPipeline:
    """サムネイル抽出パイプライン."""

    def __init__(
        self,
        max_retries: int,
        thumbnail_interval: int,
        thumbnail_dir: Path,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            thumbnail_interval: サムネイル抽出間隔（秒）
            thumbnail_dir: サムネイル保存ディレクトリ
            repository: ストリームリポジトリ
        """
        self._max_retries = max_retries
        self._thumbnail_interval = thumbnail_interval
        self._thumbnail_dir = thumbnail_dir
        self._repository = repository

    def _get_thumbnail_dir(self, video_id: str) -> Path:
        """サムネイル保存ディレクトリを取得する.

        Args:
            video_id: YouTube動画ID

        Returns:
            サムネイル保存先のディレクトリパス
        """
        thumb_dir = self._thumbnail_dir / video_id
        thumb_dir.mkdir(parents=True, exist_ok=True)
        return thumb_dir

    def extract_thumbnails(self, video_id: str, local_path: str) -> bool:
        """動画からサムネイルを抽出する.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス

        Returns:
            抽出が成功した場合はTrue
        """
        # CAS更新: downloaded -> thumbs_done
        updated = self._repository.update_status(
            video_id,
            StreamStatus.THUMBS_DONE,
            expected_old_status=StreamStatus.DOWNLOADED,
        )
        if not updated:
            logger.warning(
                "Failed to acquire lock for thumbnail extraction: %s", video_id
            )
            return False

        try:
            # サムネイルディレクトリを作成
            thumb_dir = self._get_thumbnail_dir(video_id)

            logger.info(
                "Extracting thumbnails from %s at %d second intervals",
                video_id,
                self._thumbnail_interval,
            )

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    local_path,
                    "-vf",
                    f"fps=1/{self._thumbnail_interval}",
                    "-q:v",
                    "2",
                    str(thumb_dir / "thumb_%04d.jpg"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(
                    "Thumbnail extraction failed for %s: %s", video_id, result.stderr
                )
                self._repository.update_status(
                    video_id,
                    StreamStatus.DOWNLOADED,
                    expected_old_status=StreamStatus.THUMBS_DONE,
                    error_message=(
                        result.stderr[:500] if result.stderr else "Unknown error"
                    ),
                    increment_retry=True,
                )
                return False

            logger.info("Thumbnail extraction completed: %s", video_id)
            return True

        except Exception as e:
            logger.exception("Thumbnail extraction error for %s", video_id)
            self._repository.update_status(
                video_id,
                StreamStatus.DOWNLOADED,
                expected_old_status=StreamStatus.THUMBS_DONE,
                error_message=str(e)[:500],
                increment_retry=True,
            )
            return False

    def extract_next(self) -> bool:
        """次の待機中の動画からサムネイルを抽出する.

        Returns:
            抽出対象があった場合はTrue
        """
        stream = self._repository.get_next_pending(
            StreamStatus.DOWNLOADED, self._max_retries
        )
        if stream is None or stream.local_path is None:
            return False

        return self.extract_thumbnails(stream.video_id, stream.local_path)

    def extract_all(self) -> int:
        """すべての待機中の動画からサムネイルを抽出する.

        Returns:
            抽出に成功した動画数
        """
        count = 0
        while True:
            if not self.extract_next():
                break
            count += 1
        return count
