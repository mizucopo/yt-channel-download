"""CLI エントリポイントのテスト."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

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
        patch("src.main.DiscoverPipeline") as mock_discover,
        patch("src.main.DownloadPipeline") as mock_download,
        patch("src.main.ThumbsPipeline") as mock_thumbs,
        patch("src.main.UploadPipeline") as mock_upload,
        patch("src.main.CleanupPipeline") as mock_cleanup,
    ):
        mock_discover.return_value.discover_all.return_value = 1
        mock_download.return_value.download_all.return_value = 1
        mock_thumbs.return_value.extract_all.return_value = 1
        mock_upload.return_value.upload_all.return_value = 1
        mock_cleanup.return_value.cleanup_all.return_value = 1

        # Act
        app.run()

        # Assert
        mock_discover.assert_called_once_with(
            client=mock_youtube_client,
            channel_ids=app.settings.youtube_channel_ids,
            repository=mock_repository,
        )
        mock_download.assert_called_once()
        mock_thumbs.assert_called_once()
        mock_upload.assert_called_once()
        mock_cleanup.assert_called_once()


def test_discover_cmd_executes_discover_pipeline(app: Main) -> None:
    """discover_cmd()がDiscoverPipelineを実行すること.

    Arrange:
        DiscoverPipelineとリポジトリをモックする。

    Act:
        discover_cmd()を呼び出す。

    Assert:
        DiscoverPipeline.discover_all()が呼ばれること。
    """
    # Arrange
    mock_repository = MagicMock()
    mock_youtube_client = MagicMock()

    with (
        patch.object(app, "acquire_lock"),
        patch.object(app, "get_repository", return_value=mock_repository),
        patch.object(app, "get_youtube_client", return_value=mock_youtube_client),
        patch("src.main.DiscoverPipeline") as mock_discover,
    ):
        mock_discover.return_value.discover_all.return_value = 5

        # Act
        app.discover_cmd()

        # Assert
        mock_discover.return_value.discover_all.assert_called_once()


def test_download_cmd_executes_download_pipeline(app: Main) -> None:
    """download_cmd()がDownloadPipelineを実行すること.

    Arrange:
        DownloadPipelineとリポジトリをモックする。

    Act:
        download_cmd()を呼び出す。

    Assert:
        DownloadPipeline.download_all()が呼ばれること。
    """
    # Arrange
    mock_repository = MagicMock()

    with (
        patch.object(app, "acquire_lock"),
        patch.object(app, "get_repository", return_value=mock_repository),
        patch("src.main.DownloadPipeline") as mock_download,
    ):
        mock_download.return_value.download_all.return_value = 3

        # Act
        app.download_cmd()

        # Assert
        mock_download.return_value.download_all.assert_called_once()


def test_thumbs_cmd_executes_thumbs_pipeline(app: Main) -> None:
    """thumbs_cmd()がThumbsPipelineを実行すること."""
    # Arrange
    mock_repository = MagicMock()

    with (
        patch.object(app, "acquire_lock"),
        patch.object(app, "get_repository", return_value=mock_repository),
        patch("src.main.ThumbsPipeline") as mock_thumbs,
    ):
        mock_thumbs.return_value.extract_all.return_value = 2

        # Act
        app.thumbs_cmd()

        # Assert
        mock_thumbs.return_value.extract_all.assert_called_once()


def test_upload_cmd_executes_upload_pipeline(app: Main) -> None:
    """upload_cmd()がUploadPipelineを実行すること."""
    # Arrange
    mock_repository = MagicMock()
    mock_gdrive_provider = MagicMock()

    with (
        patch.object(app, "acquire_lock"),
        patch.object(app, "get_repository", return_value=mock_repository),
        patch.object(app, "get_gdrive_provider", return_value=mock_gdrive_provider),
        patch("src.main.UploadPipeline") as mock_upload,
    ):
        mock_upload.return_value.upload_all.return_value = 1

        # Act
        app.upload_cmd()

        # Assert
        mock_upload.return_value.upload_all.assert_called_once()


def test_cleanup_cmd_executes_cleanup_pipeline(app: Main) -> None:
    """cleanup_cmd()がCleanupPipelineを実行すること."""
    # Arrange
    mock_repository = MagicMock()

    with (
        patch.object(app, "acquire_lock"),
        patch.object(app, "get_repository", return_value=mock_repository),
        patch("src.main.CleanupPipeline") as mock_cleanup,
    ):
        mock_cleanup.return_value.cleanup_all.return_value = 1

        # Act
        app.cleanup_cmd()

        # Assert
        mock_cleanup.return_value.cleanup_all.assert_called_once()


def test_recover_cmd_executes_recover_pipeline(app: Main) -> None:
    """recover_cmd()がRecoverPipelineを実行すること."""
    # Arrange
    mock_repository = MagicMock()

    with (
        patch.object(app, "acquire_lock"),
        patch.object(app, "get_repository", return_value=mock_repository),
        patch("src.main.RecoverPipeline") as mock_recover,
    ):
        mock_recover.return_value.recover_all.return_value = 2

        # Act
        app.recover_cmd()

        # Assert
        mock_recover.return_value.recover_all.assert_called_once()
