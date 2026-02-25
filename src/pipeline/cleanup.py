"""ローカルファイルクリーンアップパイプライン.

アップロード完了後、ローカルの動画ファイルとサムネイルを削除する。
"""

import logging
import shutil
from pathlib import Path

from src import db
from src.config import settings
from src.utils.paths import get_thumbnail_dir

logger = logging.getLogger(__name__)


def cleanup_video(video_id: str, local_path: str) -> bool:
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
        thumb_dir = get_thumbnail_dir(video_id)
        if thumb_dir.exists():
            shutil.rmtree(thumb_dir)
            logger.info("Deleted thumbnail directory: %s", thumb_dir)

        logger.info("Cleanup completed: %s", video_id)
        return True

    except Exception:
        logger.exception("Cleanup error for %s", video_id)
        # クリーンアップエラーはリトライしない（状態はuploadedのまま）
        return False


def cleanup_next() -> bool:
    """次の待機中の動画をクリーンアップする.

    Returns:
        クリーンアップ対象があった場合はTrue
    """
    stream = db.get_next_pending("uploaded", settings.max_retries)
    if stream is None or stream.local_path is None:
        return False

    return cleanup_video(stream.video_id, stream.local_path)


def cleanup_all() -> int:
    """すべての待機中の動画をクリーンアップする.

    Returns:
        クリーンアップに成功した動画数
    """
    count = 0
    while True:
        if not cleanup_next():
            break
        count += 1
    return count
