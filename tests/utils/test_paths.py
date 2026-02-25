"""パス管理ユーティリティのテスト."""

from pathlib import Path

from src.utils.paths import PathManager


def test_get_download_path_returns_correct_path(tmp_path: Path) -> None:
    """get_download_pathが正しいパスを返すこと.

    Arrange:
        PathManagerを初期化する。

    Act:
        get_download_path()を呼び出す。

    Assert:
        正しいパスが返されること。
    """
    # Arrange
    path_manager = PathManager(
        download_dir=tmp_path / "downloads",
        thumbnail_dir=tmp_path / "thumbnails",
        database_path=tmp_path / "streams.db",
    )
    video_id = "test_video_id"

    # Act
    result = path_manager.get_download_path(video_id)

    # Assert
    assert result.name == "test_video_id.mp4"
    assert "downloads" in str(result)


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


def test_get_thumbnail_path_returns_correct_path(tmp_path: Path) -> None:
    """get_thumbnail_pathが正しいパスを返すこと.

    Arrange:
        PathManagerを初期化する。

    Act:
        get_thumbnail_path()を呼び出す。

    Assert:
        正しいパスが返されること。
    """
    # Arrange
    path_manager = PathManager(
        download_dir=tmp_path / "downloads",
        thumbnail_dir=tmp_path / "thumbnails",
        database_path=tmp_path / "streams.db",
    )
    video_id = "test_video_id"
    index = 5

    # Act
    result = path_manager.get_thumbnail_path(video_id, index)

    # Assert
    assert result.name == "thumb_0005.jpg"
    assert video_id in str(result)
