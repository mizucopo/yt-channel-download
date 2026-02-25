"""動画検出パイプラインのテスト."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from src.models.stream import Stream
from src.models.stream_status import StreamStatus
from src.models.video_info import VideoInfo
from src.pipeline.discover import DiscoverPipeline
from src.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


def test_discover_all_registers_new_videos(repository: StreamRepository) -> None:
    """discover_allが新しい動画を登録すること.

    Arrange:
        YouTube APIクライアントのモックを準備する。

    Act:
        discover_all()を呼び出す。

    Assert:
        新しい動画がデータベースに登録されていること。
    """
    # Arrange
    mock_client = Mock()
    mock_client.get_live_archives.return_value = [
        VideoInfo(
            video_id="video1",
            title="Test Video 1",
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            duration="PT1H",
        ),
    ]

    # Act
    count = DiscoverPipeline(
        client=mock_client,
        channel_ids=["channel1"],
        repository=repository,
    ).discover_all()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.title == "Test Video 1"


def test_discover_all_skips_existing_videos(repository: StreamRepository) -> None:
    """discover_allが既存の動画をスキップすること.

    Arrange:
        既存の動画をデータベースに登録する。
        YouTube APIクライアントのモックを準備する。

    Act:
        discover_all()を呼び出す。

    Assert:
        新規登録数が0であること。
    """
    # Arrange
    repository.insert(
        Stream(
            video_id="video1", status=StreamStatus.DOWNLOADED, title="Existing Video"
        )
    )

    mock_client = Mock()
    mock_client.get_live_archives.return_value = [
        VideoInfo(
            video_id="video1",
            title="Test Video 1",
            published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
            duration="PT1H",
        ),
    ]

    # Act
    count = DiscoverPipeline(
        client=mock_client,
        channel_ids=["channel1"],
        repository=repository,
    ).discover_all()

    # Assert
    assert count == 0
