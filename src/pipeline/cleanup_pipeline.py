"""ローカルファイルクリーンアップパイプライン.

アップロード完了後、ローカルの動画ファイルとサムネイルを削除する。
"""

import logging
import shutil
from dataclasses import replace
from pathlib import Path

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.base_pipeline import BasePipeline
from src.repository.stream_repository import StreamRepository
from src.utils.path_manager import PathManager

logger = logging.getLogger(__name__)


class CleanupPipeline(BasePipeline):
    """ローカルファイルクリーンアップパイプライン."""

    def __init__(
        self,
        max_retries: int,
        download_dir: Path,
        path_manager: PathManager,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            download_dir: ダウンロードディレクトリ
            path_manager: パスマネージャ
            repository: ストリームリポジトリ
        """
        super().__init__(max_retries, repository)
        self._download_dir = download_dir
        self._path_manager = path_manager

    def _get_pending_status(self) -> StreamStatus:
        """処理待ちステータスを取得する."""
        return StreamStatus.UPLOADED

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

        # CAS更新: uploaded -> cleaned
        updated = self._repository.update_status(
            video_id,
            StreamStatus.CLEANED,
            expected_old_status=StreamStatus.UPLOADED,
        )
        if not updated:
            logger.warning("Failed to acquire lock for cleanup: %s", video_id)
            return False

        try:
            # 動画ファイルを削除
            video_file = Path(stream.local_path)
            if video_file.exists():
                video_file.unlink()
                logger.info("Deleted video file: %s", stream.local_path)

            # サムネイルディレクトリを削除
            thumb_dir = self._path_manager.get_thumbnail_dir(video_id)
            if thumb_dir.exists():
                shutil.rmtree(thumb_dir)
                logger.info("Deleted thumbnail directory: %s", thumb_dir)

            logger.info("Cleanup completed: %s", video_id)
            return True

        except Exception:
            logger.exception("Cleanup error for %s", video_id)
            # クリーンアップエラーはリトライしない（状態はuploadedのまま）
            return False

    def cleanup_video(self, video_id: str, local_path: str) -> bool:
        """動画とサムネイルをローカルから削除する.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス

        Returns:
            クリーンアップが成功した場合はTrue
        """
        stream = self._repository.get(video_id)
        if stream is None:
            return False
        stream_with_path = replace(stream, local_path=local_path)
        return self._process_single(video_id, stream_with_path)

    def cleanup_next(self) -> bool:
        """次の待機中の動画をクリーンアップする.

        Returns:
            クリーンアップ対象があった場合はTrue
        """
        return self.process_next()
