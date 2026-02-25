"""サムネイル抽出パイプライン.

ffmpegを使用して動画からスクリーンショットを抽出する。
"""

import logging
import subprocess

from src import db
from src.config import settings
from src.utils.paths import get_thumbnail_dir, get_thumbnail_path

logger = logging.getLogger(__name__)


class ThumbsPipeline:
    """サムネイル抽出パイプライン."""

    def __init__(self, max_retries: int | None = None) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数（Noneの場合は設定値を使用）
        """
        self._max_retries = (
            max_retries if max_retries is not None else settings.max_retries
        )

    def extract_thumbnails(self, video_id: str, local_path: str) -> bool:
        """動画からサムネイルを抽出する.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス

        Returns:
            抽出が成功した場合はTrue
        """
        # CAS更新: downloaded -> thumbs_done
        updated = db.update_status(
            video_id,
            "thumbs_done",
            expected_old_status="downloaded",
        )
        if not updated:
            logger.warning(
                "Failed to acquire lock for thumbnail extraction: %s", video_id
            )
            return False

        try:
            # サムネイルディレクトリを作成
            get_thumbnail_dir(video_id)
            interval = settings.thumbnail_interval

            logger.info(
                "Extracting thumbnails from %s at %d second intervals",
                video_id,
                interval,
            )

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    local_path,
                    "-vf",
                    f"fps=1/{interval}",
                    "-q:v",
                    "2",
                    str(get_thumbnail_path(video_id, 0).parent / "thumb_%04d.jpg"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(
                    "Thumbnail extraction failed for %s: %s", video_id, result.stderr
                )
                db.update_status(
                    video_id,
                    "downloaded",
                    expected_old_status="thumbs_done",
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
            db.update_status(
                video_id,
                "downloaded",
                expected_old_status="thumbs_done",
                error_message=str(e)[:500],
                increment_retry=True,
            )
            return False

    def extract_next(self) -> bool:
        """次の待機中の動画からサムネイルを抽出する.

        Returns:
            抽出対象があった場合はTrue
        """
        stream = db.get_next_pending("downloaded", self._max_retries)
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
