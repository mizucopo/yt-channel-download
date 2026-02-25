"""フルパイプライン統合テスト."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src import db


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト環境をセットアップする."""
    monkeypatch.setattr("src.config.settings.database_path", str(tmp_path / "test.db"))
    monkeypatch.setattr("src.config.settings.download_dir", str(tmp_path / "downloads"))
    monkeypatch.setattr(
        "src.config.settings.thumbnail_dir", str(tmp_path / "thumbnails")
    )
    monkeypatch.setattr("src.config.settings.max_retries", 3)
    monkeypatch.setattr("src.config.settings.thumbnail_interval", 60)
    monkeypatch.setattr(
        "src.config.settings.gdrive_credentials_path", "credentials.json"
    )
    monkeypatch.setattr("src.config.settings.gdrive_root_folder_id", "folder_id")
    monkeypatch.setattr("src.config.settings.youtube_channel_ids", ["channel1"])
    db.init_db()


def test_full_pipeline_flow(tmp_path: Path) -> None:
    """フルパイプラインが正しく動作すること.

    Arrange:
        各ステージのモックを準備する。
        動画ファイルを作成する。

    Act:
        各パイプラインステージを順番に実行する。

    Assert:
        最終的にcleanedステータスになること。
    """
    # Arrange
    from datetime import datetime, timezone

    from src.pipeline import cleanup, discover, download, thumbs, upload
    from src.yt_api import VideoInfo

    # Mock YouTube client
    mock_yt_client = Mock()
    mock_yt_client.get_live_archives.return_value = [
        VideoInfo(
            video_id="video1",
            title="Test Video",
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            duration="PT1H",
        )
    ]

    # Mock subprocess for download
    mock_download_result = Mock()
    mock_download_result.returncode = 0
    mock_download_result.stderr = ""

    # Mock subprocess for thumbnail
    mock_thumb_result = Mock()
    mock_thumb_result.returncode = 0
    mock_thumb_result.stderr = ""

    # Mock Google Drive provider
    mock_gdrive_provider = Mock()
    mock_gdrive_provider.upload_file.return_value = "gdrive_file_id"

    # Act & Assert - Discover
    with patch("src.pipeline.discover.YouTubeClient", return_value=mock_yt_client):
        count = discover.discover_videos(client=mock_yt_client)
    assert count == 1

    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "discovered"

    # Act & Assert - Download
    video_path = tmp_path / "downloads" / "video1.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.touch()

    with (
        patch("subprocess.run", return_value=mock_download_result),
        patch("src.pipeline.download.get_download_path", return_value=video_path),
    ):
        success = download.download_video("video1")
    assert success is True

    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "downloaded"

    # Act & Assert - Thumbnails
    with patch("subprocess.run", return_value=mock_thumb_result):
        success = thumbs.extract_thumbnails("video1", str(video_path))
    assert success is True

    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "thumbs_done"

    # Act & Assert - Upload
    with patch(
        "src.pipeline.upload.GoogleDriveProvider", return_value=mock_gdrive_provider
    ):
        success = upload.upload_video("video1", str(video_path))
    assert success is True

    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "uploaded"

    # Act & Assert - Cleanup
    success = cleanup.cleanup_video("video1", str(video_path))
    assert success is True

    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "cleaned"
