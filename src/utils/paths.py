"""パス管理ユーティリティ.

ダウンロードファイルやサムネイルのパスを生成する。
"""

from pathlib import Path


def get_download_path(video_id: str, download_dir: Path) -> Path:
    """動画のダウンロードパスを取得する.

    Args:
        video_id: YouTube動画ID
        download_dir: ダウンロードディレクトリ

    Returns:
        ダウンロード先のパス
    """
    download_dir.mkdir(parents=True, exist_ok=True)
    return download_dir / f"{video_id}.mp4"


def get_thumbnail_dir(video_id: str, thumbnail_dir: Path) -> Path:
    """サムネイル保存ディレクトリを取得する.

    Args:
        video_id: YouTube動画ID
        thumbnail_dir: サムネイルベースディレクトリ

    Returns:
        サムネイル保存先のディレクトリパス
    """
    thumb_dir = thumbnail_dir / video_id
    thumb_dir.mkdir(parents=True, exist_ok=True)
    return thumb_dir


def get_thumbnail_path(video_id: str, index: int, thumbnail_dir: Path) -> Path:
    """サムネイルファイルのパスを取得する.

    Args:
        video_id: YouTube動画ID
        index: サムネイルのインデックス
        thumbnail_dir: サムネイルベースディレクトリ

    Returns:
        サムネイルファイルのパス
    """
    return get_thumbnail_dir(video_id, thumbnail_dir) / f"thumb_{index:04d}.jpg"


def ensure_directories(
    download_dir: str,
    thumbnail_dir: str,
    database_path: str,
) -> None:
    """必要なディレクトリを作成する."""
    Path(download_dir).mkdir(parents=True, exist_ok=True)
    Path(thumbnail_dir).mkdir(parents=True, exist_ok=True)
    Path(database_path).parent.mkdir(parents=True, exist_ok=True)
