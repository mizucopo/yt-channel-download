"""動画検出パイプラインのテスト."""

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock

import pytest
from mizu_common import YouTubeVideoInfo as VideoInfo

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.discover_pipeline import DiscoverPipeline
from src.repository.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


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
    mock_client.get_channel_videos.return_value = [
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


@pytest.mark.parametrize(
    "is_first_run,expected_status",
    [
        pytest.param(True, StreamStatus.CANCELED, id="first_run"),
        pytest.param(False, StreamStatus.DISCOVERED, id="normal_run"),
    ],
)
def test_discover_all_registers_with_correct_initial_status(
    repository: StreamRepository,
    is_first_run: bool,
    expected_status: StreamStatus,
) -> None:
    """discover_allがis_first_runに応じて正しい初期ステータスで登録すること.

    Arrange:
        YouTube APIクライアントのモックを準備する。

    Act:
        is_first_runを指定してdiscover_all()を呼び出す。

    Assert:
        初回実行時はCANCELED、通常実行時はDISCOVEREDで登録されること。
    """
    # Arrange
    mock_client = Mock()
    mock_client.get_channel_videos.return_value = [
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
        is_first_run=is_first_run,
    ).discover_all()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == expected_status


@pytest.mark.parametrize(
    "published_after",
    [
        pytest.param(datetime(2024, 1, 1, tzinfo=timezone.utc), id="with_date"),
        pytest.param(None, id="without_date"),
    ],
)
def test_discover_all_passes_published_after_to_client(
    repository: StreamRepository,
    published_after: datetime | None,
) -> None:
    """discover_allがpublished_afterをクライアントに正しく渡すこと.

    Arrange:
        YouTube APIクライアントのモックを準備する。

    Act:
        published_afterを指定してdiscover_all()を呼び出す。

    Assert:
        クライアントのget_channel_videosがpublished_after付きで呼ばれること。
    """
    # Arrange
    mock_client = Mock()
    mock_client.get_channel_videos.return_value = []

    # Act
    DiscoverPipeline(
        client=mock_client,
        channel_ids=["channel1"],
        repository=repository,
        is_first_run=False,
        published_after=published_after,
    ).discover_all()

    # Assert
    mock_client.get_channel_videos.assert_called_once_with(
        "channel1", published_after=published_after
    )
