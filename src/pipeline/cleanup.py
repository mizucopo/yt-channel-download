"""ローカルファイルクリーンアップパイプライン.

アップロード完了後、ローカルの動画ファイルとサムネイルを削除する。
"""

import logging
import shutil
from pathlib import Path

from src import db
from src.utils.paths import get_thumbnail_dir

logger = logging.getLogger(__name__)


class CleanupPipeline:
    """ローカルファイルクリーンアップパイプライン."""

    def __init__(
        self,
        max_retries: int,
        download_dir: Path,
        thumbnail_dir: Path,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            download_dir: ダウンロードディレクトリ
            thumbnail_dir: サムネイルディレクトリ
        """
        self._max_retries = max_retries
        self._download_dir = download_dir
        self._thumbnail_dir = thumbnail_dir

    def cleanup_video(self, video_id: str, local_path: str) -> bool:
        """動画とサムネイルをローカルから削除する.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス

        Returns:
            クリーンアップが成功した場合はTrue
        """
        # CAS更新: uploaded -> cleaned
        updated = db.update_status(
            video_id,
            "cleaned",
            expected_old_status="uploaded",
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
            thumb_dir = get_thumbnail_dir(video_id, self._thumbnail_dir)
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
        stream = db.get_next_pending("uploaded", self._max_retries)
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
