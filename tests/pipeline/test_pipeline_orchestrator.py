"""PipelineOrchestratorのテスト."""

from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.models.scan_mode import ScanMode
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator
from src.settings import Settings
from src.utils.path_manager import PathManager


@pytest.fixture
def mock_settings() -> Settings:
    """テスト用の設定を返すフィクスチャ."""
    settings = MagicMock(spec=Settings)
    settings.max_retries = 3
    settings.thumbnail_interval = 5
    settings.thumbnail_quality = 85
    settings.gdrive_root_folder_id = "test_folder_id"
    settings.youtube_channel_ids = ["channel1", "channel2"]
    return settings


@pytest.fixture
def mock_path_manager() -> PathManager:
    """テスト用のパスマネージャを返すフィクスチャ."""
    path_manager = MagicMock(spec=PathManager)
    path_manager.download_dir = Path("/tmp/download")
    path_manager.thumbnail_dir = Path("/tmp/thumbnail")
    path_manager.database_path = Path("/tmp/test.db")
    return path_manager


@pytest.fixture
def mock_client_factory() -> MagicMock:
    """テスト用のクライアントファクトリを返すフィクスチャ."""
    factory = MagicMock()
    factory.get_youtube_client.return_value = MagicMock()
    factory.get_gdrive_provider.return_value = MagicMock()
    factory.get_discord_notifier.return_value = None
    return factory


@pytest.fixture
def mock_repository() -> MagicMock:
    """テスト用のリポジトリを返すフィクスチャ."""
    repository = MagicMock()
    repository.is_empty.return_value = False
    return repository


def test_run_runs_full_pipeline(
    mock_settings: Settings,
    mock_path_manager: PathManager,
    mock_client_factory: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """全パイプラインが実行されること.

    Arrange:
        各パイプラインとScanModeをモック。

    Act:
        run()を呼び出す。

    Assert:
        各パイプラインが正しいパラメータで実行されること。
    """
    # Arrange
    orchestrator = PipelineOrchestrator(
        mock_settings, mock_path_manager, mock_client_factory
    )
    scan_mode = MagicMock(spec=ScanMode)
    scan_mode.get_published_after.return_value = datetime(2026, 1, 1)

    with (
        patch(
            "src.pipeline.pipeline_orchestrator.RecoverPipeline"
        ) as mock_recover_class,
        patch(
            "src.pipeline.pipeline_orchestrator.DiscoverPipeline"
        ) as mock_discover_class,
        patch(
            "src.pipeline.pipeline_orchestrator.DownloadPipeline"
        ) as mock_download_class,
        patch("src.pipeline.pipeline_orchestrator.ThumbsPipeline") as mock_thumbs_class,
        patch("src.pipeline.pipeline_orchestrator.UploadPipeline") as mock_upload_class,
        patch(
            "src.pipeline.pipeline_orchestrator.CleanupPipeline"
        ) as mock_cleanup_class,
        patch(
            "src.pipeline.pipeline_orchestrator.SingleVideoOrchestrator"
        ) as mock_single_class,
        patch("click.echo"),
    ):
        mock_recover = MagicMock()
        mock_recover.run.return_value = 5
        mock_recover_class.return_value = mock_recover

        mock_discover = MagicMock()
        mock_discover.discover_all.return_value = 10
        mock_discover_class.return_value = mock_discover

        mock_single = MagicMock()
        mock_single.process_all_videos.return_value = 3
        mock_single_class.return_value = mock_single

        # Act
        orchestrator.run(mock_repository, scan_mode)

    # Assert
    mock_repository.reset_all_retry_counts.assert_called_once()
    mock_client_factory.get_youtube_client.assert_called_once()
    mock_client_factory.get_gdrive_provider.assert_called_once_with(
        folder_id="test_folder_id"
    )
    mock_client_factory.get_discord_notifier.assert_called_once()

    # RecoverPipeline
    mock_recover_class.assert_called_once_with(
        max_retries=3,
        thumbnail_dir=Path("/tmp/thumbnail"),
        repository=mock_repository,
    )
    mock_recover.run.assert_called_once()

    # DiscoverPipeline
    mock_discover_class.assert_called_once_with(
        client=mock_client_factory.get_youtube_client.return_value,
        channel_ids=["channel1", "channel2"],
        repository=mock_repository,
        is_first_run=False,
        published_after=datetime(2026, 1, 1),
    )
    mock_discover.discover_all.assert_called_once()

    # DownloadPipeline
    mock_download_class.assert_called_once_with(
        max_retries=3,
        download_dir=Path("/tmp/download"),
        repository=mock_repository,
    )

    # ThumbsPipeline
    mock_thumbs_class.assert_called_once_with(
        max_retries=3,
        thumbnail_interval=5,
        thumbnail_quality=85,
        path_manager=mock_path_manager,
        repository=mock_repository,
    )

    # UploadPipeline
    mock_upload_class.assert_called_once_with(
        max_retries=3,
        gdrive_provider=mock_client_factory.get_gdrive_provider.return_value,
        gdrive_root_folder_id="test_folder_id",
        path_manager=mock_path_manager,
        repository=mock_repository,
    )

    # CleanupPipeline
    mock_cleanup_class.assert_called_once_with(
        max_retries=3,
        download_dir=Path("/tmp/download"),
        path_manager=mock_path_manager,
        repository=mock_repository,
    )

    # SingleVideoOrchestrator
    mock_single_class.assert_called_once()
    mock_single.process_all_videos.assert_called_once()


def test_run_shows_first_run_message_when_discovered_on_first_run(
    mock_settings: Settings,
    mock_path_manager: PathManager,
    mock_client_factory: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """初回実行時に動画が検出された場合、専用メッセージが表示されること.

    Arrange:
        is_empty()がTrueを返すようにモック。

    Act:
        run()を呼び出す。

    Assert:
        初回実行メッセージが表示されること。
    """
    # Arrange
    mock_repository.is_empty.return_value = True
    orchestrator = PipelineOrchestrator(
        mock_settings, mock_path_manager, mock_client_factory
    )
    scan_mode = MagicMock(spec=ScanMode)
    scan_mode.get_published_after.return_value = None

    with (
        patch("src.pipeline.pipeline_orchestrator.RecoverPipeline") as mock_recover,
        patch(
            "src.pipeline.pipeline_orchestrator.DiscoverPipeline"
        ) as mock_discover_class,
        patch("src.pipeline.pipeline_orchestrator.DownloadPipeline"),
        patch("src.pipeline.pipeline_orchestrator.ThumbsPipeline"),
        patch("src.pipeline.pipeline_orchestrator.UploadPipeline"),
        patch("src.pipeline.pipeline_orchestrator.CleanupPipeline"),
        patch(
            "src.pipeline.pipeline_orchestrator.SingleVideoOrchestrator"
        ) as mock_single,
        patch("click.echo") as mock_echo,
    ):
        mock_recover.return_value.run.return_value = 0
        mock_discover = MagicMock()
        mock_discover.discover_all.return_value = 5
        mock_discover_class.return_value = mock_discover
        mock_single.return_value.process_all_videos.return_value = 0

        # Act
        orchestrator.run(mock_repository, scan_mode)

    # Assert
    echo_calls = [str(call) for call in mock_echo.call_args_list]
    assert any("First run" in call for call in echo_calls)


def test_run_shows_discovered_message_when_not_first_run(
    mock_settings: Settings,
    mock_path_manager: PathManager,
    mock_client_factory: MagicMock,
    mock_repository: MagicMock,
) -> None:
    """2回目以降に動画が検出された場合、通常メッセージが表示されること.

    Arrange:
        is_empty()がFalseを返すようにモック。

    Act:
        run()を呼び出す。

    Assert:
        通常の検出メッセージが表示されること。
    """
    # Arrange
    mock_repository.is_empty.return_value = False
    orchestrator = PipelineOrchestrator(
        mock_settings, mock_path_manager, mock_client_factory
    )
    scan_mode = MagicMock(spec=ScanMode)
    scan_mode.get_published_after.return_value = None

    with (
        patch("src.pipeline.pipeline_orchestrator.RecoverPipeline") as mock_recover,
        patch(
            "src.pipeline.pipeline_orchestrator.DiscoverPipeline"
        ) as mock_discover_class,
        patch("src.pipeline.pipeline_orchestrator.DownloadPipeline"),
        patch("src.pipeline.pipeline_orchestrator.ThumbsPipeline"),
        patch("src.pipeline.pipeline_orchestrator.UploadPipeline"),
        patch("src.pipeline.pipeline_orchestrator.CleanupPipeline"),
        patch(
            "src.pipeline.pipeline_orchestrator.SingleVideoOrchestrator"
        ) as mock_single,
        patch("click.echo") as mock_echo,
    ):
        mock_recover.return_value.run.return_value = 0
        mock_discover = MagicMock()
        mock_discover.discover_all.return_value = 5
        mock_discover_class.return_value = mock_discover
        mock_single.return_value.process_all_videos.return_value = 0

        # Act
        orchestrator.run(mock_repository, scan_mode)

    # Assert
    echo_calls = [str(call) for call in mock_echo.call_args_list]
    assert any("Discovered" in call for call in echo_calls)
