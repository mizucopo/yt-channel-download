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
    mock_repository.is_empty.return_value = False
    mock_youtube_client = MagicMock()
    mock_gdrive_provider = MagicMock()

    with (
        patch.object(app, "acquire_lock"),
        patch.object(app, "get_repository", return_value=mock_repository),
        patch.object(app, "get_youtube_client", return_value=mock_youtube_client),
        patch.object(app, "get_gdrive_provider", return_value=mock_gdrive_provider),
        patch.object(app, "get_discord_notifier", return_value=None),
        patch("src.main.RecoverPipeline") as mock_recover,
        patch("src.main.DiscoverPipeline") as mock_discover,
        patch("src.main.DownloadPipeline") as mock_download,
        patch("src.main.ThumbsPipeline") as mock_thumbs,
        patch("src.main.UploadPipeline") as mock_upload,
        patch("src.main.CleanupPipeline") as mock_cleanup,
        patch("src.main.SingleVideoOrchestrator") as mock_orchestrator,
    ):
        mock_recover.return_value.recover_all.return_value = 1
        mock_discover.return_value.discover_all.return_value = 1
        mock_orchestrator.return_value.process_all_videos.return_value = 1

        # Act
        app.run()

        # Assert
        mock_recover.assert_called_once()
        mock_discover.assert_called_once_with(
            client=mock_youtube_client,
            channel_ids=app.settings.youtube_channel_ids,
            repository=mock_repository,
            is_first_run=False,
        )
        mock_download.assert_called_once()
        mock_thumbs.assert_called_once()
        mock_upload.assert_called_once()
        mock_cleanup.assert_called_once()
        mock_orchestrator.assert_called_once()


def test_run_passes_is_first_run_true_on_empty_database(app: Main) -> None:
    """空のデータベースでis_first_run=Trueが渡されること.

    Arrange:
        リポジトリのis_empty()がTrueを返すようにモックする。
        各パイプラインをモックする。

    Act:
        run()を呼び出す。

    Assert:
        DiscoverPipelineにis_first_run=Trueが渡されること。
    """
    # Arrange
    mock_repository = MagicMock()
    mock_repository.is_empty.return_value = True
    mock_youtube_client = MagicMock()
    mock_gdrive_provider = MagicMock()

    with (
        patch.object(app, "acquire_lock"),
        patch.object(app, "get_repository", return_value=mock_repository),
        patch.object(app, "get_youtube_client", return_value=mock_youtube_client),
        patch.object(app, "get_gdrive_provider", return_value=mock_gdrive_provider),
        patch.object(app, "get_discord_notifier", return_value=None),
        patch("src.main.RecoverPipeline") as mock_recover,
        patch("src.main.DiscoverPipeline") as mock_discover,
        patch("src.main.DownloadPipeline"),
        patch("src.main.ThumbsPipeline"),
        patch("src.main.UploadPipeline"),
        patch("src.main.CleanupPipeline"),
        patch("src.main.SingleVideoOrchestrator") as mock_orchestrator,
    ):
        mock_recover.return_value.recover_all.return_value = 0
        mock_discover.return_value.discover_all.return_value = 5
        mock_orchestrator.return_value.process_all_videos.return_value = 0

        # Act
        app.run()

        # Assert
        mock_discover.assert_called_once_with(
            client=mock_youtube_client,
            channel_ids=app.settings.youtube_channel_ids,
            repository=mock_repository,
            is_first_run=True,
        )


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


@pytest.mark.parametrize(
    "client_id,client_secret,should_mock_auth",
    [
        pytest.param("test_client_id", "", False, id="missing_client_secret"),
        pytest.param("", "test_client_secret", False, id="missing_client_id"),
        pytest.param("test_client_id", "test_client_secret", True, id="auth_failure"),
    ],
)
def test_auth_cmd_fails_on_invalid_credentials(
    app: Main,
    client_id: str,
    client_secret: str,
    should_mock_auth: bool,
) -> None:
    """auth_cmd()が無効な認証情報で失敗すること.

    Arrange:
        認証情報を設定する（CLIENT_ID/CLIENT_SECRET未設定または認証失敗）。

    Act:
        auth_cmd()を呼び出す。

    Assert:
        SystemExit(1)が発生すること。
    """
    # Arrange
    app.settings.google_oauth_client_id = client_id
    app.settings.google_oauth_client_secret = client_secret

    # Act & Assert
    if should_mock_auth:
        with patch("src.main.GoogleOAuthClient.authenticate", return_value=None):
            with pytest.raises(SystemExit) as exc_info:
                app.auth_cmd()
            assert exc_info.value.code == 1
    else:
        with pytest.raises(SystemExit) as exc_info:
            app.auth_cmd()
        assert exc_info.value.code == 1
