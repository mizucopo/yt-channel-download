"""パス管理ユーティリティ.

ダウンロードファイルやサムネイルのパスを生成する。
"""

from pathlib import Path


class PathManager:
    """パス管理クラス."""

    def __init__(
        self,
        download_dir: Path,
        thumbnail_dir: Path,
        database_path: Path,
    ) -> None:
        """パスマネージャを初期化する.

        Args:
            download_dir: ダウンロードディレクトリ
            thumbnail_dir: サムネイルディレクトリ
            database_path: データベースファイルパス
        """
        self._download_dir = download_dir
        self._thumbnail_dir = thumbnail_dir
        self._database_path = database_path

    @property
    def download_dir(self) -> Path:
        """ダウンロードディレクトリを取得する."""
        return self._download_dir

    @property
    def thumbnail_dir(self) -> Path:
        """サムネイルディレクトリを取得する."""
        return self._thumbnail_dir

    @property
    def database_path(self) -> Path:
        """データベースファイルパスを取得する."""
        return self._database_path

    def get_thumbnail_dir(self, video_id: str) -> Path:
        """サムネイル保存ディレクトリを取得する.

        Args:
            video_id: YouTube動画ID

        Returns:
            サムネイル保存先のディレクトリパス
        """
        thumb_dir = self._thumbnail_dir / video_id
        thumb_dir.mkdir(parents=True, exist_ok=True)
        return thumb_dir

    def ensure_directories(self) -> None:
        """必要なディレクトリを作成する."""
        self._download_dir.mkdir(parents=True, exist_ok=True)
        self._thumbnail_dir.mkdir(parents=True, exist_ok=True)
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
