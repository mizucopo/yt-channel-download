"""ClientFactoryのテスト."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.client_factory import ClientFactory
from src.settings import Settings
from src.utils.path_manager import PathManager


@pytest.fixture
def mock_settings() -> Settings:
    """テスト用の設定を返すフィクスチャ."""
    settings = MagicMock(spec=Settings)
    settings.google_oauth_client_id = "test_client_id"
    settings.google_oauth_client_secret = "test_client_secret"
    settings.google_refresh_token = "test_refresh_token"
    settings.google_scopes = ["https://www.googleapis.com/auth/youtube.readonly"]
    settings.gdrive_root_folder_id = "test_folder_id"
    settings.discord_webhook_url = "https://discord.com/api/webhooks/test"
    return settings


@pytest.fixture
def mock_path_manager() -> PathManager:
    """テスト用のパスマネージャを返すフィクスチャ."""
    path_manager = MagicMock(spec=PathManager)
    path_manager.download_dir = Path("/tmp/download")
    path_manager.thumbnail_dir = Path("/tmp/thumbnail")
    path_manager.database_path = Path("/tmp/test.db")
    return path_manager


def test_get_oauth_client_returns_oauth_client_with_settings(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """設定値を使用してGoogleOAuthClientが生成されること.

    Arrange:
        テスト用の設定とパスマネージャを準備。
        GoogleOAuthClientをモック。

    Act:
        get_oauth_client()を呼び出す。

    Assert:
        設定値が正しく渡されてGoogleOAuthClientが生成されること。
    """
    # Arrange
    factory = ClientFactory(mock_settings, mock_path_manager)
    mock_oauth_client = MagicMock()

    with patch(
        "src.client_factory.GoogleOAuthClient", return_value=mock_oauth_client
    ) as mock_class:
        # Act
        result = factory.get_oauth_client()

    # Assert
    assert result is mock_oauth_client
    mock_class.assert_called_once_with(
        oauth_client_id="test_client_id",
        oauth_client_secret="test_client_secret",
        refresh_token="test_refresh_token",
        scopes=["https://www.googleapis.com/auth/youtube.readonly"],
    )


def test_get_oauth_client_handles_none_oauth_client_secret(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """oauth_client_secretがNoneの場合、空文字に変換されること.

    Arrange:
        oauth_client_secretをNoneに設定。

    Act:
        get_oauth_client()を呼び出す。

    Assert:
        空文字が渡されること。
    """
    # Arrange
    mock_settings.google_oauth_client_secret = None  # type: ignore[assignment]
    factory = ClientFactory(mock_settings, mock_path_manager)
    mock_oauth_client = MagicMock()

    with patch(
        "src.client_factory.GoogleOAuthClient", return_value=mock_oauth_client
    ) as mock_class:
        # Act
        factory.get_oauth_client()

    # Assert
    mock_class.assert_called_once()
    call_kwargs = mock_class.call_args.kwargs
    assert call_kwargs["oauth_client_secret"] == ""


def test_get_youtube_client_returns_youtube_client_with_oauth_client(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """GoogleOAuthClientを使用してYouTubeClientが生成されること.

    Arrange:
        YouTubeClientをモック。

    Act:
        get_youtube_client()を呼び出す。

    Assert:
        OAuthクライアントが渡されてYouTubeClientが生成されること。
    """
    # Arrange
    factory = ClientFactory(mock_settings, mock_path_manager)
    mock_oauth_client = MagicMock()
    mock_youtube_client = MagicMock()

    with (
        patch("src.client_factory.GoogleOAuthClient", return_value=mock_oauth_client),
        patch(
            "src.client_factory.YouTubeClient", return_value=mock_youtube_client
        ) as mock_class,
    ):
        # Act
        result = factory.get_youtube_client()

    # Assert
    assert result is mock_youtube_client
    mock_class.assert_called_once_with(oauth_client=mock_oauth_client)


def test_get_gdrive_provider_returns_gdrive_provider_with_settings(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """設定値を使用してGoogleDriveProviderが生成されること.

    Arrange:
        GoogleDriveProviderをモック。

    Act:
        get_gdrive_provider()を呼び出す。

    Assert:
        設定値が正しく渡されること。
    """
    # Arrange
    factory = ClientFactory(mock_settings, mock_path_manager)
    mock_provider = MagicMock()

    with patch("src.client_factory.GoogleDriveProvider") as mock_class:
        mock_class.from_credentials.return_value = mock_provider

        # Act
        result = factory.get_gdrive_provider("custom_folder_id")

    # Assert
    assert result is mock_provider
    mock_class.from_credentials.assert_called_once_with(
        folder_id="custom_folder_id",
        client_id="test_client_id",
        client_secret="test_client_secret",
        refresh_token="test_refresh_token",
    )


def test_get_discord_notifier_returns_discord_notifier_when_webhook_url_set(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """webhook_urlが設定されている場合、DiscordNotifierが生成されること.

    Arrange:
        DiscordNotifierをモック。

    Act:
        get_discord_notifier()を呼び出す。

    Assert:
        正しいURLでDiscordNotifierが生成されること。
    """
    # Arrange
    factory = ClientFactory(mock_settings, mock_path_manager)
    mock_notifier = MagicMock()

    with patch(
        "src.client_factory.DiscordNotifier", return_value=mock_notifier
    ) as mock_class:
        # Act
        result = factory.get_discord_notifier()

    # Assert
    assert result is mock_notifier
    mock_class.assert_called_once_with(
        webhook_url="https://discord.com/api/webhooks/test",
        gdrive_folder_url="https://drive.google.com/drive/folders/test_folder_id",
    )


def test_get_discord_notifier_returns_none_when_webhook_url_not_set(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """webhook_urlが未設定の場合、Noneが返されること.

    Arrange:
        discord_webhook_urlを空文字に設定。

    Act:
        get_discord_notifier()を呼び出す。

    Assert:
        Noneが返されること。
    """
    # Arrange
    mock_settings.discord_webhook_url = ""
    factory = ClientFactory(mock_settings, mock_path_manager)

    # Act
    result = factory.get_discord_notifier()

    # Assert
    assert result is None


def test_get_discord_notifier_returns_none_when_webhook_url_is_none(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """webhook_urlがNoneの場合、Noneが返されること.

    Arrange:
        discord_webhook_urlをNoneに設定。

    Act:
        get_discord_notifier()を呼び出す。

    Assert:
        Noneが返されること。
    """
    # Arrange
    mock_settings.discord_webhook_url = None
    factory = ClientFactory(mock_settings, mock_path_manager)

    # Act
    result = factory.get_discord_notifier()

    # Assert
    assert result is None
