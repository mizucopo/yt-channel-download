"""Google Driveアップロードパイプラインのテスト."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src import db
from src.pipeline import upload


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト用データベースをセットアップする."""
    test_db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.config.settings.database_path", test_db_path)
    monkeypatch.setattr(
        "src.config.settings.thumbnail_dir", str(tmp_path / "thumbnails")
    )
    monkeypatch.setattr("src.config.settings.max_retries", 3)
    monkeypatch.setattr(
        "src.config.settings.gdrive_credentials_path", "credentials.json"
    )
    monkeypatch.setattr("src.config.settings.gdrive_root_folder_id", "folder_id")
    db.init_db()


def test_upload_video_updates_status_on_success(tmp_path: Path) -> None:
    """upload_videoが成功時にステータスを更新すること.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        動画ファイルを作成する。
        GoogleDriveProviderをモックする。

    Act:
        upload_video()を呼び出す。

    Assert:
        ステータスがuploadedに更新されていること。
    """
    # Arrange
    video_path = tmp_path / "video.mp4"
    video_path.touch()

    db.insert_stream(
        db.Stream(
            video_id="video1",
            status="thumbs_done",
            title="Test Video",
            local_path=str(video_path),
        )
    )

    mock_provider = Mock()
    mock_provider.upload_file.return_value = "gdrive_file_id"

    with patch("src.pipeline.upload.GoogleDriveProvider", return_value=mock_provider):
        # Act
        success = upload.upload_video("video1", str(video_path))

    # Assert
    assert success is True
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "uploaded"
    assert result.gdrive_file_id == "gdrive_file_id"


def test_upload_video_reverts_status_on_failure(tmp_path: Path) -> None:
    """upload_videoが失敗時にステータスを元に戻すこと.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        動画ファイルを作成する。
        GoogleDriveProviderをモックして例外を発生させる。

    Act:
        upload_video()を呼び出す。

    Assert:
        ステータスがthumbs_doneに戻っていること。
    """
    # Arrange
    video_path = tmp_path / "video.mp4"
    video_path.touch()

    db.insert_stream(
        db.Stream(
            video_id="video1",
            status="thumbs_done",
            title="Test Video",
            local_path=str(video_path),
        )
    )

    mock_provider = Mock()
    mock_provider.upload_file.side_effect = Exception("Upload failed")

    with patch("src.pipeline.upload.GoogleDriveProvider", return_value=mock_provider):
        # Act
        success = upload.upload_video("video1", str(video_path))

    # Assert
    assert success is False
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "thumbs_done"
