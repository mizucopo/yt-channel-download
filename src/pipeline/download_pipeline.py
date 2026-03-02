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
        self._current_local_path: str | None = None

    def _get_pending_status(self) -> StreamStatus:
        """処理待ちステータスを取得する."""
        return StreamStatus.DISCOVERED

    def _get_processing_status(self) -> StreamStatus:
        """処理中ステータスを取得する."""
        return StreamStatus.DOWNLOADING

    def _get_completed_status(self) -> StreamStatus:
        """完了ステータスを取得する."""
        return StreamStatus.DOWNLOADED

    def _execute_process(self, video_id: str, _stream: Stream) -> bool:
        """ダウンロード処理を実行する.

        Args:
            video_id: YouTube動画ID
            _stream: ストリーム情報（未使用）

        Returns:
            処理が成功した場合はTrue
        """
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
            return False

        # yt-dlpが出力した実際のファイルパスを保存
        self._current_local_path = result.stdout.strip()
        logger.info("Download completed: %s", video_id)
        return True

    def _update_completed_status(
        self, video_id: str, processing_status: StreamStatus
    ) -> None:
        """処理完了時のステータス更新（local_pathも設定）."""
        self._repository.update_status(
            video_id,
            self._get_completed_status(),
            expected_old_status=processing_status,
            local_path=self._current_local_path,
        )

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
