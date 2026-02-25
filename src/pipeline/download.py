"""動画ダウンロードパイプライン.

yt-dlpを使用してYouTubeライブアーカイブをダウンロードする。
"""

import logging
import subprocess

from src import db
from src.config import settings
from src.utils.paths import get_download_path

logger = logging.getLogger(__name__)


class DownloadPipeline:
    """動画ダウンロードパイプライン."""

    def __init__(self, max_retries: int | None = None) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数（Noneの場合は設定値を使用）
        """
        self._max_retries = (
            max_retries if max_retries is not None else settings.max_retries
        )

    def download_video(self, video_id: str) -> bool:
        """指定された動画をダウンロードする.

        Args:
            video_id: YouTube動画ID

        Returns:
            ダウンロードが成功した場合はTrue
        """
        # CAS更新: discovered -> downloading
        updated = db.update_status(
            video_id,
            "downloading",
            expected_old_status="discovered",
        )
        if not updated:
            logger.warning("Failed to acquire lock for video: %s", video_id)
            return False

        try:
            output_path = get_download_path(video_id)
            url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info("Downloading video: %s", video_id)
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-f",
                    "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
                    "-o",
                    str(output_path),
                    "--no-playlist",
                    "--no-warnings",
                    url,
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error("Download failed for %s: %s", video_id, result.stderr)
                db.update_status(
                    video_id,
                    "discovered",
                    expected_old_status="downloading",
                    error_message=(
                        result.stderr[:500] if result.stderr else "Unknown error"
                    ),
                    increment_retry=True,
                )
                return False

            # CAS更新: downloading -> downloaded
            db.update_status(
                video_id,
                "downloaded",
                expected_old_status="downloading",
                local_path=str(output_path),
            )
            logger.info("Download completed: %s", video_id)
            return True

        except Exception as e:
            logger.exception("Download error for %s", video_id)
            db.update_status(
                video_id,
                "discovered",
                expected_old_status="downloading",
                error_message=str(e)[:500],
                increment_retry=True,
            )
            return False

    def download_next(self) -> bool:
        """次の待機中の動画をダウンロードする.

        Returns:
            ダウンロード対象があった場合はTrue
        """
        stream = db.get_next_pending("discovered", self._max_retries)
        if stream is None:
            return False

        return self.download_video(stream.video_id)

    def download_all(self) -> int:
        """すべての待機中の動画をダウンロードする.

        Returns:
            ダウンロードに成功した動画数
        """
        count = 0
        while True:
            if not self.download_next():
                break
            count += 1
        return count
