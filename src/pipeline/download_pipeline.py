"""動画ダウンロードパイプライン.

yt-dlpを使用してYouTubeライブアーカイブをダウンロードする。
"""

import logging
import subprocess
from pathlib import Path

from src.models.stream_status import StreamStatus
from src.repository.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class DownloadPipeline:
    """動画ダウンロードパイプライン."""

    DEFAULT_VIDEO_FORMAT = "bv[height=1080][ext=webm]+ba[ext=webm]"

    def __init__(
        self,
        max_retries: int,
        download_dir: Path,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            download_dir: ダウンロード保存ディレクトリ
            repository: ストリームリポジトリ
        """
        self._max_retries = max_retries
        self._download_dir = download_dir
        self._repository = repository

    def download_video(self, video_id: str) -> bool:
        """指定された動画をダウンロードする.

        Args:
            video_id: YouTube動画ID

        Returns:
            ダウンロードが成功した場合はTrue
        """
        # CAS更新: discovered -> downloading
        updated = self._repository.update_status(
            video_id,
            StreamStatus.DOWNLOADING,
            expected_old_status=StreamStatus.DISCOVERED,
        )
        if not updated:
            logger.warning("Failed to acquire lock for video: %s", video_id)
            return False

        try:
            output_template = self._download_dir / f"{video_id}.%(ext)s"
            url = f"https://www.youtube.com/watch?v={video_id}"

            logger.info("Downloading video: %s", video_id)
            result = subprocess.run(
                [
                    "yt-dlp",
                    "-f",
                    self.DEFAULT_VIDEO_FORMAT,
                    "-o",
                    str(output_template),
                    "--print",
                    "after_move:filepath",
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
                self._repository.update_status(
                    video_id,
                    StreamStatus.DISCOVERED,
                    expected_old_status=StreamStatus.DOWNLOADING,
                    error_message=(
                        result.stderr[:500] if result.stderr else "Unknown error"
                    ),
                    increment_retry=True,
                )
                return False

            # yt-dlpが出力した実際のファイルパスを取得
            actual_path = result.stdout.strip()

            # CAS更新: downloading -> downloaded
            self._repository.update_status(
                video_id,
                StreamStatus.DOWNLOADED,
                expected_old_status=StreamStatus.DOWNLOADING,
                local_path=actual_path,
            )
            logger.info("Download completed: %s", video_id)
            return True

        except Exception as e:
            logger.exception("Download error for %s", video_id)
            self._repository.update_status(
                video_id,
                StreamStatus.DISCOVERED,
                expected_old_status=StreamStatus.DOWNLOADING,
                error_message=str(e)[:500],
                increment_retry=True,
            )
            return False

    def download_next(self) -> bool:
        """次の待機中の動画をダウンロードする.

        Returns:
            ダウンロード対象があった場合はTrue
        """
        stream = self._repository.get_next_pending(
            StreamStatus.DISCOVERED, self._max_retries
        )
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
