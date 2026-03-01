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

logger = logging.getLogger(__name__)


class ThumbsPipeline(BasePipeline):
    """サムネイル抽出パイプライン."""

    def __init__(
        self,
        max_retries: int,
        thumbnail_interval: int,
        thumbnail_quality: int,
        thumbnail_dir: Path,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            thumbnail_interval: サムネイル抽出間隔（秒）
            thumbnail_quality: サムネイル画質（1-31、小さいほど高画質）
            thumbnail_dir: サムネイル保存ディレクトリ
            repository: ストリームリポジトリ
        """
        super().__init__(max_retries, repository)
        self._thumbnail_interval = thumbnail_interval
        self._thumbnail_quality = thumbnail_quality
        self._thumbnail_dir = thumbnail_dir

    def _get_pending_status(self) -> StreamStatus:
        """処理待ちステータスを取得する."""
        return StreamStatus.DOWNLOADED

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

    def _process_single(self, video_id: str, stream: Stream) -> bool:
        """単一のストリームを処理する.

        Args:
            video_id: YouTube動画ID
            stream: ストリーム情報

        Returns:
            処理が成功した場合はTrue
        """
        if stream.local_path is None:
            return False

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
            # 動画ファイルの存在確認
            video_file = Path(stream.local_path)
            if not self._validate_file_exists(video_file, video_id):
                return False

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
                self._repository.update_status(
                    video_id,
                    StreamStatus.DOWNLOADED,
                    expected_old_status=StreamStatus.THUMBS_DONE,
                    error_message=self.truncate_error(result.stderr),
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
                error_message=self.truncate_error(str(e)),
                increment_retry=True,
            )
            return False

    def extract_thumbnails(self, video_id: str, local_path: str) -> bool:
        """動画からサムネイルを抽出する.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス

        Returns:
            抽出が成功した場合はTrue
        """
        stream = self._repository.get(video_id)
        if stream is None:
            return False
        # local_pathを一時的に上書きするため、新しいStreamを作成
        from dataclasses import replace

        stream_with_path = replace(stream, local_path=local_path)
        return self._process_single(video_id, stream_with_path)

    def extract_next(self) -> bool:
        """次の待機中の動画からサムネイルを抽出する.

        Returns:
            抽出対象があった場合はTrue
        """
        return self.process_next()

    def extract_all(self) -> int:
        """すべての待機中の動画からサムネイルを抽出する.

        Returns:
            抽出に成功した動画数
        """
        return self.process_all()
