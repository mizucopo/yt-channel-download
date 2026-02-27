"""フルパイプライン統合テスト."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from mizu_common import YouTubeClient
from mizu_common import YouTubeVideoInfo as VideoInfo

from src.models.stream_status import StreamStatus
from src.pipeline.cleanup_pipeline import CleanupPipeline
from src.pipeline.discover_pipeline import DiscoverPipeline
from src.pipeline.download_pipeline import DownloadPipeline
from src.pipeline.thumbs_pipeline import ThumbsPipeline
from src.pipeline.upload_pipeline import UploadPipeline
from src.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "streams.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


def test_full_pipeline_processes_video_from_discovery_to_cleanup(
    repository: StreamRepository,
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
    mock_yt_client = Mock(spec=YouTubeClient)
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

    download_dir = tmp_path / "downloads"
    thumbnail_dir = tmp_path / "thumbnails"

    # Act & Assert - Discover
    count = DiscoverPipeline(
        client=mock_yt_client,
        channel_ids=["channel1"],
        repository=repository,
    ).discover_all()
    assert count == 1

    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DISCOVERED

    # Act & Assert - Download
    video_path = download_dir / "video1.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.touch()

    with patch("subprocess.run", return_value=mock_download_result):
        success = DownloadPipeline(
            max_retries=3,
            download_dir=download_dir,
            repository=repository,
        ).download_video("video1")
    assert success is True

    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADED

    # Act & Assert - Thumbnails
    with patch("subprocess.run", return_value=mock_thumb_result):
        success = ThumbsPipeline(
            max_retries=3,
            thumbnail_interval=60,
            thumbnail_dir=thumbnail_dir,
            repository=repository,
        ).extract_thumbnails("video1", str(video_path))
    assert success is True

    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.THUMBS_DONE

    # Act & Assert - Upload
    success = UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_gdrive_provider,
        gdrive_root_folder_id="folder_id",
        thumbnail_dir=thumbnail_dir,
        repository=repository,
    ).upload_video("video1", str(video_path))
    assert success is True

    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.UPLOADED

    # Act & Assert - Cleanup
    success = CleanupPipeline(
        max_retries=3,
        download_dir=download_dir,
        thumbnail_dir=thumbnail_dir,
        repository=repository,
    ).cleanup_video("video1", str(video_path))
    assert success is True

    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.CLEANED
