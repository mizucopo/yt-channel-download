"""CLI エントリポイントのテスト."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mizu_common import GoogleScope

from src.main import Main


@pytest.fixture
def mock_settings() -> MagicMock:
    """モック設定を作成する."""
    settings = MagicMock()
    settings.youtube_channel_ids = ["channel1"]
    settings.max_retries = 3
    settings.thumbnail_interval = 60
    settings.gdrive_root_folder_id = "folder_id"
    settings.lock_stale_hours = 24
    settings.download_dir = "/tmp/downloads"
    settings.thumbnail_dir = "/tmp/thumbnails"
    settings.database_path = "/tmp/test.db"
    return settings


@pytest.fixture
def mock_path_manager(tmp_path: Path) -> MagicMock:
    """モックパスマネージャを作成する."""
    manager = MagicMock()
    manager.download_dir = tmp_path / "downloads"
    manager.thumbnail_dir = tmp_path / "thumbnails"
    manager.database_path = tmp_path / "test.db"
    return manager


@pytest.fixture
def app(mock_settings: MagicMock, mock_path_manager: MagicMock) -> Main:
    """テスト用アプリケーションを作成する."""
    with (
        patch("src.main.Settings.from_env", return_value=mock_settings),
        patch("src.main.PathManager", return_value=mock_path_manager),
    ):
        return Main()


def test_run_executes_all_pipelines_in_order(app: Main) -> None:
    """run()が全パイプラインを正しい順序で実行すること.

    Arrange:
        各パイプラインとリポジトリをモックする。
        ロック取得をスキップする。

    Act:
        run()を呼び出す。

    Assert:
        各パイプラインが順番に実行されること。
    """
    # Arrange
    mock_repository = MagicMock()
    mock_youtube_client = MagicMock()
    mock_gdrive_provider = MagicMock()

    with (
        patch.object(app, "acquire_lock"),
        patch.object(app, "get_repository", return_value=mock_repository),
        patch.object(app, "get_youtube_client", return_value=mock_youtube_client),
        patch.object(app, "get_gdrive_provider", return_value=mock_gdrive_provider),
        patch("src.main.RecoverPipeline") as mock_recover,
        patch("src.main.DiscoverPipeline") as mock_discover,
        patch("src.main.DownloadPipeline") as mock_download,
        patch("src.main.ThumbsPipeline") as mock_thumbs,
        patch("src.main.UploadPipeline") as mock_upload,
        patch("src.main.CleanupPipeline") as mock_cleanup,
    ):
        mock_recover.return_value.recover_all.return_value = 1
        mock_discover.return_value.discover_all.return_value = 1
        mock_download.return_value.download_all.return_value = 1
        mock_thumbs.return_value.extract_all.return_value = 1
        mock_upload.return_value.upload_all.return_value = 1
        mock_cleanup.return_value.cleanup_all.return_value = 1

        # Act
        app.run()

        # Assert
        mock_recover.assert_called_once()
        mock_discover.assert_called_once_with(
            client=mock_youtube_client,
            channel_ids=app.settings.youtube_channel_ids,
            repository=mock_repository,
        )
        mock_download.assert_called_once()
        mock_thumbs.assert_called_once()
        mock_upload.assert_called_once()
        mock_cleanup.assert_called_once()


def test_auth_cmd_succeeds_with_valid_credentials(app: Main) -> None:
    """auth_cmd()が有効な認証情報で成功すること.

    Arrange:
        設定にCLIENT_IDとCLIENT_SECRETを設定する。
        GoogleOAuthClient.authenticateをモックする。

    Act:
        auth_cmd()を呼び出す。

    Assert:
        authenticateが正しい引数で呼ばれること。
        リフレッシュトークンが出力されること。
    """
    # Arrange
    app.settings.google_oauth_client_id = "test_client_id"
    app.settings.google_oauth_client_secret = "test_client_secret"

    with (
        patch(
            "src.main.GoogleOAuthClient.authenticate",
            return_value="test_refresh_token",
        ) as mock_auth,
        patch("src.main.click.echo") as mock_echo,
    ):
        # Act
        app.auth_cmd()

        # Assert
        mock_auth.assert_called_once_with(
            "test_client_id",
            "test_client_secret",
            [GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE],
        )
        # リフレッシュトークンを含むメッセージが出力されること
        calls = mock_echo.call_args_list
        assert any("test_refresh_token" in str(call) for call in calls)


def test_auth_cmd_fails_without_client_secret(app: Main) -> None:
    """auth_cmd()がCLIENT_SECRET未設定時に失敗すること.

    Arrange:
        設定のCLIENT_SECRETを空にする。

    Act:
        auth_cmd()を呼び出す。

    Assert:
        SystemExit(1)が発生すること。
    """
    # Arrange
    app.settings.google_oauth_client_id = "test_client_id"
    app.settings.google_oauth_client_secret = ""

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        app.auth_cmd()
    assert exc_info.value.code == 1


def test_auth_cmd_fails_without_client_id(app: Main) -> None:
    """auth_cmd()がCLIENT_ID未設定時に失敗すること.

    Arrange:
        設定のCLIENT_IDを空にする。

    Act:
        auth_cmd()を呼び出す。

    Assert:
        SystemExit(1)が発生すること。
    """
    # Arrange
    app.settings.google_oauth_client_id = ""
    app.settings.google_oauth_client_secret = "test_client_secret"

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        app.auth_cmd()
    assert exc_info.value.code == 1


def test_auth_cmd_fails_when_authentication_fails(app: Main) -> None:
    """auth_cmd()が認証失敗時に失敗すること.

    Arrange:
        設定にCLIENT_IDとCLIENT_SECRETを設定する。
        GoogleOAuthClient.authenticateがNoneを返すようにモックする。

    Act:
        auth_cmd()を呼び出す。

    Assert:
        SystemExit(1)が発生すること。
    """
    # Arrange
    app.settings.google_oauth_client_id = "test_client_id"
    app.settings.google_oauth_client_secret = "test_client_secret"

    with patch("src.main.GoogleOAuthClient.authenticate", return_value=None):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            app.auth_cmd()
        assert exc_info.value.code == 1
