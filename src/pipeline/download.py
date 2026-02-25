"""動画ダウンロードパイプライン.

yt-dlpを使用してYouTubeライブアーカイブをダウンロードする。
"""

import logging
import subprocess
from pathlib import Path

from src import db

logger = logging.getLogger(__name__)


class DownloadPipeline:
    """動画ダウンロードパイプライン."""

    def __init__(
        self,
        max_retries: int,
        download_dir: Path,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            download_dir: ダウンロード保存ディレクトリ
        """
        self._max_retries = max_retries
        self._download_dir = download_dir

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
            output_path = self._download_dir / f"{video_id}.mp4"
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
