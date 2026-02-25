"""サムネイル抽出パイプラインのテスト."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src import db
from src.pipeline import thumbs


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト用データベースをセットアップする."""
    test_db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.config.settings.database_path", test_db_path)
    monkeypatch.setattr(
        "src.config.settings.thumbnail_dir", str(tmp_path / "thumbnails")
    )
    monkeypatch.setattr("src.config.settings.thumbnail_interval", 60)
    monkeypatch.setattr("src.config.settings.max_retries", 3)
    db.init_db()


def test_extract_thumbnails_updates_status_on_success() -> None:
    """extract_thumbnailsが成功時にステータスを更新すること.

    Arrange:
        downloadedステータスのストリームを登録する。
        subprocess.runをモックして成功を返す。

    Act:
        extract_thumbnails()を呼び出す。

    Assert:
        ステータスがthumbs_doneに更新されていること。
    """
    # Arrange
    db.insert_stream(
        db.Stream(
            video_id="video1",
            status="downloaded",
            title="Test Video",
            local_path="/path/to/video.mp4",
        )
    )

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result):
        # Act
        success = thumbs.extract_thumbnails("video1", "/path/to/video.mp4")

    # Assert
    assert success is True
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "thumbs_done"


def test_extract_thumbnails_reverts_status_on_failure() -> None:
    """extract_thumbnailsが失敗時にステータスを元に戻すこと.

    Arrange:
        downloadedステータスのストリームを登録する。
        subprocess.runをモックして失敗を返す。

    Act:
        extract_thumbnails()を呼び出す。

    Assert:
        ステータスがdownloadedに戻っていること。
    """
    # Arrange
    db.insert_stream(
        db.Stream(
            video_id="video1",
            status="downloaded",
            title="Test Video",
            local_path="/path/to/video.mp4",
        )
    )

    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "FFmpeg error"

    with patch("subprocess.run", return_value=mock_result):
        # Act
        success = thumbs.extract_thumbnails("video1", "/path/to/video.mp4")

    # Assert
    assert success is False
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "downloaded"
