"""動画ダウンロードパイプライン.

yt-dlpを使用してYouTubeライブアーカイブをダウンロードする。
"""

import logging
import subprocess
from pathlib import Path

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.base_pipeline import BasePipeline
from src.repository.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class DownloadPipeline(BasePipeline):
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
        super().__init__(max_retries, repository)
        self._download_dir = download_dir

    def _get_pending_status(self) -> StreamStatus:
        """処理待ちステータスを取得する."""
        return StreamStatus.DISCOVERED

    def _process_single(self, video_id: str, _stream: Stream) -> bool:
        """単一のストリームを処理する.

        Args:
            video_id: YouTube動画ID
            _stream: ストリーム情報（未使用）

        Returns:
            処理が成功した場合はTrue
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
                    error_message=self.truncate_error(result.stderr),
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
                error_message=self.truncate_error(str(e)),
                increment_retry=True,
            )
            return False

    def download_video(self, video_id: str) -> bool:
        """指定された動画をダウンロードする.

        Args:
            video_id: YouTube動画ID

        Returns:
            ダウンロードが成功した場合はTrue
        """
        stream = self._repository.get(video_id)
        if stream is None:
            return False
        return self._process_single(video_id, stream)
