"""パス管理ユーティリティ.

ダウンロードファイルやサムネイルのパスを生成する。
"""

from pathlib import Path

from src.config import settings


def get_download_path(video_id: str) -> Path:
    """動画のダウンロードパスを取得する.

    Args:
        video_id: YouTube動画ID

    Returns:
        ダウンロード先のパス
    """
    download_dir = Path(settings.download_dir)
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir / f"{video_id}.mp4"


def get_thumbnail_dir(video_id: str) -> Path:
    """サムネイル保存ディレクトリを取得する.

    Args:
        video_id: YouTube動画ID

    Returns:
        サムネイル保存先のディレクトリパス
    """
    thumb_dir = Path(settings.thumbnail_dir) / video_id
    thumb_dir.mkdir(parents=True, exist_ok=True)
    return thumb_dir


def get_thumbnail_path(video_id: str, index: int) -> Path:
    """サムネイルファイルのパスを取得する.

    Args:
        video_id: YouTube動画ID
        index: サムネイルのインデックス

    Returns:
        サムネイルファイルのパス
    """
    return get_thumbnail_dir(video_id) / f"thumb_{index:04d}.jpg"


def ensure_directories() -> None:
    """必要なディレクトリを作成する."""
    Path(settings.download_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.thumbnail_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.database_path).parent.mkdir(parents=True, exist_ok=True)
