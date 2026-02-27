"""ローカルファイルクリーンアップパイプライン.

アップロード完了後、ローカルの動画ファイルとサムネイルを削除する。
"""

import logging
import shutil
from pathlib import Path

from src.models.stream_status import StreamStatus
from src.repository.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class CleanupPipeline:
    """ローカルファイルクリーンアップパイプライン."""

    def __init__(
        self,
        max_retries: int,
        download_dir: Path,
        thumbnail_dir: Path,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            download_dir: ダウンロードディレクトリ
            thumbnail_dir: サムネイルディレクトリ
            repository: ストリームリポジトリ
        """
        self._max_retries = max_retries
        self._download_dir = download_dir
        self._thumbnail_dir = thumbnail_dir
        self._repository = repository

    def _get_thumbnail_dir(self, video_id: str) -> Path:
        """サムネイル保存ディレクトリを取得する.

        Args:
            video_id: YouTube動画ID

        Returns:
            サムネイル保存先のディレクトリパス
        """
        return self._thumbnail_dir / video_id

    def cleanup_video(self, video_id: str, local_path: str) -> bool:
        """動画とサムネイルをローカルから削除する.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス

        Returns:
            クリーンアップが成功した場合はTrue
        """
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
            video_file = Path(local_path)
            if video_file.exists():
                video_file.unlink()
                logger.info("Deleted video file: %s", local_path)

            # サムネイルディレクトリを削除
            thumb_dir = self._get_thumbnail_dir(video_id)
            if thumb_dir.exists():
                shutil.rmtree(thumb_dir)
                logger.info("Deleted thumbnail directory: %s", thumb_dir)

            logger.info("Cleanup completed: %s", video_id)
            return True

        except Exception:
            logger.exception("Cleanup error for %s", video_id)
            # クリーンアップエラーはリトライしない（状態はuploadedのまま）
            return False

    def cleanup_next(self) -> bool:
        """次の待機中の動画をクリーンアップする.

        Returns:
            クリーンアップ対象があった場合はTrue
        """
        stream = self._repository.get_next_pending(
            StreamStatus.UPLOADED, self._max_retries
        )
        if stream is None or stream.local_path is None:
            return False

        return self.cleanup_video(stream.video_id, stream.local_path)

    def cleanup_all(self) -> int:
        """すべての待機中の動画をクリーンアップする.

        Returns:
            クリーンアップに成功した動画数
        """
        count = 0
        while True:
            if not self.cleanup_next():
                break
            count += 1
        return count
