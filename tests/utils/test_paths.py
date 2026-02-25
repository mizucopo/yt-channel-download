"""パス管理ユーティリティのテスト."""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def setup_test_paths(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト用パスをセットアップする."""
    monkeypatch.setattr("src.config.settings.download_dir", str(tmp_path / "downloads"))
    monkeypatch.setattr(
        "src.config.settings.thumbnail_dir", str(tmp_path / "thumbnails")
    )


def test_get_download_path_returns_correct_path() -> None:
    """get_download_pathが正しいパスを返すこと.

    Arrange:
        テスト用のvideo_idを準備する。

    Act:
        get_download_path()を呼び出す。

    Assert:
        正しいパスが返されること。
    """
    # Arrange
    from src.utils.paths import get_download_path

    video_id = "test_video_id"

    # Act
    result = get_download_path(video_id)

    # Assert
    assert result.name == "test_video_id.mp4"
    assert "downloads" in str(result)


def test_get_thumbnail_dir_creates_directory() -> None:
    """get_thumbnail_dirがディレクトリを作成すること.

    Arrange:
        テスト用のvideo_idを準備する。

    Act:
        get_thumbnail_dir()を呼び出す。

    Assert:
        ディレクトリが作成され、正しいパスが返されること。
    """
    # Arrange
    from src.utils.paths import get_thumbnail_dir

    video_id = "test_video_id"

    # Act
    result = get_thumbnail_dir(video_id)

    # Assert
    assert result.name == video_id
    assert result.exists()
    assert result.is_dir()


def test_get_thumbnail_path_returns_correct_path() -> None:
    """get_thumbnail_pathが正しいパスを返すこと.

    Arrange:
        テスト用のvideo_idとindexを準備する。

    Act:
        get_thumbnail_path()を呼び出す。

    Assert:
        正しいパスが返されること。
    """
    # Arrange
    from src.utils.paths import get_thumbnail_path

    video_id = "test_video_id"
    index = 5

    # Act
    result = get_thumbnail_path(video_id, index)

    # Assert
    assert result.name == "thumb_0005.jpg"
    assert video_id in str(result)
