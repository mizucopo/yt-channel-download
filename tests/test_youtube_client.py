"""YouTube APIクライアントのテスト."""

from datetime import datetime, timezone
from typing import Any
from unittest.mock import Mock

import pytest

from src.models.video_info import VideoInfo
from src.youtube_client import YouTubeClient


@pytest.fixture
def mock_requests() -> None:
    """requests.getをモックする."""
    pass


def test_video_info_is_dataclass() -> None:
    """VideoInfoがデータクラスとして正しく作成されること.

    Arrange:
        テスト用の動画情報を準備する。

    Act:
        VideoInfoデータクラスを作成する。

    Assert:
        各フィールドが正しく設定されていること。
    """
    # Arrange & Act
    info = VideoInfo(
        video_id="test_id",
        title="Test Video",
        published_at=datetime(2024, 1, 1, tzinfo=timezone.utc),
        duration="PT1H2M3S",
    )

    # Assert
    assert info.video_id == "test_id"
    assert info.title == "Test Video"
    assert info.duration == "PT1H2M3S"


def test_youtube_client_initializes_with_api_key() -> None:
    """YouTubeClientがAPIキーで初期化されること.

    Arrange:
        テスト用のAPIキーを準備する。

    Act:
        YouTubeClientを作成する。

    Assert:
        APIキーが正しく設定されていること。
    """
    # Arrange
    api_key = "test_api_key"

    # Act
    client = YouTubeClient(api_key)

    # Assert
    assert client.api_key == api_key


def test_get_video_details_returns_video_info(mocker: Any) -> None:
    """get_video_detailsが動画情報を返すこと.

    Arrange:
        APIレスポンスをモックする。

    Act:
        get_video_details()を呼び出す。

    Assert:
        VideoInfoが正しく返されること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {
                "id": "test_video_id",
                "snippet": {
                    "title": "Test Video Title",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT10M"},
            }
        ]
    }
    mocker.patch("requests.get", return_value=mock_response)

    client = YouTubeClient("test_key")

    # Act
    result = client.get_video_details("test_video_id")

    # Assert
    assert result is not None
    assert result.video_id == "test_video_id"
    assert result.title == "Test Video Title"
    assert result.duration == "PT10M"


def test_get_video_details_returns_none_on_error(mocker: Any) -> None:
    """APIエラー時にget_video_detailsがNoneを返すこと.

    Arrange:
        エラーレスポンスをモックする。

    Act:
        get_video_details()を呼び出す。

    Assert:
        Noneが返されること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 404
    mocker.patch("requests.get", return_value=mock_response)

    client = YouTubeClient("test_key")

    # Act
    result = client.get_video_details("nonexistent_id")

    # Assert
    assert result is None


def test_get_live_archives_returns_videos(mocker: Any) -> None:
    """get_live_archivesがライブアーカイブ一覧を返すこと.

    Arrange:
        検索APIと動画詳細APIのレスポンスをモックする。

    Act:
        get_live_archives()を呼び出す。

    Assert:
        VideoInfoのリストが返されること。
    """
    # Arrange
    search_response = Mock()
    search_response.status_code = 200
    search_response.json.return_value = {
        "items": [{"id": {"videoId": "video1"}}],
        "nextPageToken": None,
    }

    videos_response = Mock()
    videos_response.status_code = 200
    videos_response.json.return_value = {
        "items": [
            {
                "id": "video1",
                "snippet": {
                    "title": "Live Archive 1",
                    "publishedAt": "2024-01-01T00:00:00Z",
                },
                "contentDetails": {"duration": "PT1H"},
            }
        ]
    }

    mock_get = mocker.patch("requests.get")
    mock_get.side_effect = [search_response, videos_response]

    client = YouTubeClient("test_key")

    # Act
    result = client.get_live_archives("test_channel_id")

    # Assert
    assert len(result) == 1
    assert result[0].video_id == "video1"
    assert result[0].title == "Live Archive 1"
