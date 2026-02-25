"""フルパイプライン統合テスト."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src import db
from src.models.video_info import VideoInfo
from src.pipeline.cleanup import CleanupPipeline
from src.pipeline.discover import DiscoverPipeline
from src.pipeline.download import DownloadPipeline
from src.pipeline.thumbs import ThumbsPipeline
from src.pipeline.upload import UploadPipeline


@pytest.fixture(autouse=True)
def setup_test_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト環境をセットアップする."""
    monkeypatch.setattr(
        "src.config.settings.database_path", str(tmp_path / "streams.db")
    )
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


def test_full_pipeline_processes_video_from_discovery_to_cleanup(
    tmp_path: Path,
) -> None:
    """フルパイプラインが動画を検出からクリーンアップまで処理すること.

    Arrange:
        各パイプラインのモックを準備する。
        動画ファイルを作成する。

    Act:
        各パイプラインを順番に実行する。

    Assert:
        最終的にcleanedステータスになること。
    """
    # Arrange
    mock_yt_client = Mock()
    mock_yt_client.get_live_archives.return_value = [
        VideoInfo(
            video_id="video1",
            title="Test Video",
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            duration="PT1H",
        )
    ]

    mock_download_result = Mock()
    mock_download_result.returncode = 0
    mock_download_result.stderr = ""

    mock_thumb_result = Mock()
    mock_thumb_result.returncode = 0
    mock_thumb_result.stderr = ""

    mock_gdrive_provider = Mock()
    mock_gdrive_provider.upload_file.return_value = "gdrive_file_id"

    # Act & Assert - Discover
    with patch("src.pipeline.discover.YouTubeClient", return_value=mock_yt_client):
        count = DiscoverPipeline(client=mock_yt_client).discover_videos()
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
        success = DownloadPipeline().download_video("video1")
    assert success is True

    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "downloaded"

    # Act & Assert - Thumbnails
    with patch("subprocess.run", return_value=mock_thumb_result):
        success = ThumbsPipeline().extract_thumbnails("video1", str(video_path))
    assert success is True

    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "thumbs_done"

    # Act & Assert - Upload
    with patch(
        "src.pipeline.upload.GoogleDriveProvider", return_value=mock_gdrive_provider
    ):
        success = UploadPipeline().upload_video("video1", str(video_path))
    assert success is True

    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "uploaded"

    # Act & Assert - Cleanup
    success = CleanupPipeline().cleanup_video("video1", str(video_path))
    assert success is True

    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "cleaned"
