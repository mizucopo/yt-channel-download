"""CLI エントリポイントのテスト."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from src.main import Main, cli
from src.models.scan_mode import ScanMode


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


def test_run_delegates_to_pipeline_orchestrator(app: Main) -> None:
    """run()がパイプラインオーケストレーターに処理を委譲すること.

    Arrange:
        パイプラインオーケストレーターをモックする。
        ロック取得をスキップする。

    Act:
        run()をフルスキャンモードで呼び出す。

    Assert:
        パイプラインオーケストレーターのrun()が呼ばれること。
    """
    # Arrange
    mock_repository = MagicMock()
    scan_mode = ScanMode(days=None)

    with (
        patch.object(app, "_lock_context") as mock_lock_context,
        patch.object(app, "get_repository", return_value=mock_repository),
        patch.object(app, "_pipeline_orchestrator") as mock_orchestrator,
    ):
        mock_lock_context.acquire.return_value.__enter__ = MagicMock(return_value=None)
        mock_lock_context.acquire.return_value.__exit__ = MagicMock(return_value=False)

        # Act
        app.run(scan_mode)

        # Assert
        mock_orchestrator.run.assert_called_once_with(mock_repository, scan_mode)


# CLI run コマンドのテスト


@pytest.fixture
def cli_runner() -> CliRunner:
    """Click CLIテストランナーを作成する."""
    return CliRunner()


def test_run_cli_shows_help_when_no_options(
    cli_runner: CliRunner, mock_settings: MagicMock, mock_path_manager: MagicMock
) -> None:
    """オプション未指定時にヘルプが表示されること.

    Arrange:
        テストランナーを準備する。

    Act:
        オプションなしでrunコマンドを実行する。

    Assert:
        ヘルプが表示されること。
        正常終了すること。
    """
    # Arrange & Act
    with (
        patch("src.main.Settings.from_env", return_value=mock_settings),
        patch("src.main.PathManager", return_value=mock_path_manager),
    ):
        result = cli_runner.invoke(cli, ["run"])

    # Assert
    assert result.exit_code == 0
    assert "Usage:" in result.output
    assert "--full" in result.output
    assert "--days" in result.output


def test_run_cli_rejects_full_and_days_together(
    cli_runner: CliRunner, mock_settings: MagicMock, mock_path_manager: MagicMock
) -> None:
    """--fullと--daysの同時指定が拒否されること.

    Arrange:
        テストランナーを準備する。

    Act:
        --fullと--daysを同時に指定してrunコマンドを実行する。

    Assert:
        エラーが表示されること。
    """
    # Arrange & Act
    with (
        patch("src.main.Settings.from_env", return_value=mock_settings),
        patch("src.main.PathManager", return_value=mock_path_manager),
    ):
        result = cli_runner.invoke(cli, ["run", "--full", "--days", "7"])

    # Assert
    assert result.exit_code != 0
    assert "同時に指定できません" in result.output


@pytest.mark.parametrize(
    "days_value",
    [
        pytest.param(0, id="zero_days"),
        pytest.param(-1, id="negative_days"),
    ],
)
def test_run_cli_rejects_invalid_days_value(
    cli_runner: CliRunner,
    mock_settings: MagicMock,
    mock_path_manager: MagicMock,
    days_value: int,
) -> None:
    """--daysに0または負の値を指定した場合エラーになること.

    Arrange:
        テストランナーを準備する。

    Act:
        無効な値で--daysを指定してrunコマンドを実行する。

    Assert:
        エラーが表示されること。
    """
    # Arrange & Act
    with (
        patch("src.main.Settings.from_env", return_value=mock_settings),
        patch("src.main.PathManager", return_value=mock_path_manager),
    ):
        result = cli_runner.invoke(cli, ["run", "--days", str(days_value)])

    # Assert
    assert result.exit_code != 0
    assert "1以上の整数" in result.output


def test_run_cli_rejects_days_option_on_first_run(
    cli_runner: CliRunner, mock_settings: MagicMock, tmp_path: Path
) -> None:
    """初回起動時に -d オプションを指定するとエラーになること.

    Arrange:
        データベースファイルが存在しないパスマネージャを作成する。

    Act:
        --daysオプションでrunコマンドを実行する。

    Assert:
        エラーが表示されること。
        初回起動時は--fullを指定するよう促すメッセージが表示されること。
    """
    # Arrange
    # データベースファイルが存在しないパスマネージャを作成
    mock_path_manager = MagicMock()
    mock_path_manager.download_dir = tmp_path / "downloads"
    mock_path_manager.thumbnail_dir = tmp_path / "thumbnails"
    # データベースパスに存在しないファイルを設定
    nonexistent_db = tmp_path / "nonexistent" / "test.db"
    mock_path_manager.database_path = nonexistent_db

    # Act
    with (
        patch("src.main.Settings.from_env", return_value=mock_settings),
        patch("src.main.PathManager", return_value=mock_path_manager),
    ):
        result = cli_runner.invoke(cli, ["run", "--days", "7"])

    # Assert
    assert result.exit_code != 0
    assert "初回起動時は --full を指定してください" in result.output
