"""動画検出パイプラインのテスト."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest

from src import db
from src.models.stream import Stream
from src.models.video_info import VideoInfo
from src.pipeline.discover import DiscoverPipeline


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト用データベースをセットアップする."""
    test_db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.config.settings.database_path", test_db_path)
    db.init_db()


def test_discover_videos_registers_new_videos() -> None:
    """discover_videosが新しい動画を登録すること.

    Arrange:
        YouTube APIクライアントのモックを準備する。

    Act:
        discover_videos()を呼び出す。

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
    ).discover_all()

    # Assert
    assert count == 1
    result = db.get_stream("video1")
    assert result is not None
    assert result.title == "Test Video 1"


def test_discover_videos_skips_existing_videos() -> None:
    """discover_videosが既存の動画をスキップすること.

    Arrange:
        既存の動画をデータベースに登録する。
        YouTube APIクライアントのモックを準備する。

    Act:
        discover_videos()を呼び出す。

    Assert:
        新規登録数が0であること。
    """
    # Arrange
    db.insert_stream(
        Stream(video_id="video1", status="downloaded", title="Existing Video")
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
    ).discover_all()

    # Assert
    assert count == 0
