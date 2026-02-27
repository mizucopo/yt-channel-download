"""サムネイル抽出パイプラインのテスト."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.models.stream import Stream
from src.models.stream_status import StreamStatus
from src.pipeline.thumbs_pipeline import ThumbsPipeline
from src.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


def test_extract_thumbnails_updates_status_on_success(
    repository: StreamRepository, tmp_path: Path
) -> None:
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
    repository.insert(
        Stream(
            video_id="video1",
            status=StreamStatus.DOWNLOADED,
            title="Test Video",
            local_path="/path/to/video.mp4",
        )
    )

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    thumbnail_dir = tmp_path / "thumbnails"

    with patch("subprocess.run", return_value=mock_result):
        # Act
        success = ThumbsPipeline(
            max_retries=3,
            thumbnail_interval=60,
            thumbnail_dir=thumbnail_dir,
            repository=repository,
        ).extract_thumbnails("video1", "/path/to/video.mp4")

    # Assert
    assert success is True
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.THUMBS_DONE


def test_extract_thumbnails_reverts_status_on_failure(
    repository: StreamRepository, tmp_path: Path
) -> None:
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
    repository.insert(
        Stream(
            video_id="video1",
            status=StreamStatus.DOWNLOADED,
            title="Test Video",
            local_path="/path/to/video.mp4",
        )
    )

    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "FFmpeg error"

    thumbnail_dir = tmp_path / "thumbnails"

    with patch("subprocess.run", return_value=mock_result):
        # Act
        success = ThumbsPipeline(
            max_retries=3,
            thumbnail_interval=60,
            thumbnail_dir=thumbnail_dir,
            repository=repository,
        ).extract_thumbnails("video1", "/path/to/video.mp4")

    # Assert
    assert success is False
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADED
