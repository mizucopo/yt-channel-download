"""パス管理ユーティリティのテスト."""

from pathlib import Path

from src.utils.path_manager import PathManager


def test_get_thumbnail_dir_creates_directory(tmp_path: Path) -> None:
    """get_thumbnail_dirがディレクトリを作成すること.

    Arrange:
        PathManagerを初期化する。

    Act:
        get_thumbnail_dir()を呼び出す。

    Assert:
        ディレクトリが作成され、正しいパスが返されること。
    """
    # Arrange
    path_manager = PathManager(
        download_dir=tmp_path / "downloads",
        thumbnail_dir=tmp_path / "thumbnails",
        database_path=tmp_path / "streams.db",
    )
    video_id = "test_video_id"

    # Act
    result = path_manager.get_thumbnail_dir(video_id)

    # Assert
    assert result.name == video_id
    assert result.exists()
    assert result.is_dir()
