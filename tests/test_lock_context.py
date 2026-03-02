"""LockContextのテスト."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from mizu_common import AlreadyRunningError

from src.lock_context import LockContext
from src.settings import Settings
from src.utils.path_manager import PathManager


@pytest.fixture
def mock_settings() -> Settings:
    """テスト用の設定を返すフィクスチャ."""
    settings = MagicMock(spec=Settings)
    settings.lock_stale_hours = 24
    return settings


@pytest.fixture
def mock_path_manager() -> PathManager:
    """テスト用のパスマネージャを返すフィクスチャ."""
    path_manager = MagicMock(spec=PathManager)
    path_manager.download_dir = Path("/tmp/download")
    return path_manager


def test_acquire_acquires_lock_successfully(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """ロック取得に成功した場合、コンテキストが実行されること.

    Arrange:
        LockManagerをモックして正常にロック取得できるようにする。

    Act:
        acquire()コンテキストマネージャ内のコードを実行。

    Assert:
        コンテキスト内のコードが実行されること。
    """
    # Arrange
    lock_context = LockContext(mock_settings, mock_path_manager)
    mock_lock_manager = MagicMock()
    mock_lock_manager.acquire.return_value.__enter__ = MagicMock(return_value=None)
    mock_lock_manager.acquire.return_value.__exit__ = MagicMock(return_value=False)
    executed = False

    with patch(
        "src.lock_context.LockManager", return_value=mock_lock_manager
    ) as mock_class:
        mock_class.return_value = mock_lock_manager

        # Act
        with lock_context.acquire():
            executed = True

    # Assert
    assert executed is True
    mock_class.assert_called_once_with(
        lock_dir=mock_path_manager.download_dir,
        stale_hours=mock_settings.lock_stale_hours,
    )


def test_acquire_exits_when_already_running(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """他のインスタンスが実行中の場合、SystemExitが発生すること.

    Arrange:
        LockManagerをモックしてAlreadyRunningErrorを発生させる。

    Act:
        acquire()コンテキストマネージャを実行。

    Assert:
        SystemExit(0)が発生すること。
    """
    # Arrange
    lock_context = LockContext(mock_settings, mock_path_manager)
    mock_lock_manager = MagicMock()
    mock_lock_manager.acquire.side_effect = AlreadyRunningError("Already running")

    with (
        patch("src.lock_context.LockManager", return_value=mock_lock_manager),
        patch("click.echo") as mock_echo,
        pytest.raises(SystemExit) as exc_info,
        lock_context.acquire(),
    ):
        pass

    # Assert
    assert exc_info.value.code == 0
    expected_msg = "Another instance is already running. Exiting."
    mock_echo.assert_called_once_with(expected_msg)


def test_release_releases_lock_when_locked(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """ロックされている場合、ロックが解除されること.

    Arrange:
        LockManagerをモックしてis_locked()がTrueを返すようにする。

    Act:
        release()を呼び出す。

    Assert:
        release()が呼ばれ、メッセージが表示されること。
    """
    # Arrange
    lock_context = LockContext(mock_settings, mock_path_manager)
    mock_lock_manager = MagicMock()
    mock_lock_manager.is_locked.return_value = True
    mock_lock_manager.lock_path = Path("/tmp/download/.lock")

    with (
        patch("src.lock_context.LockManager", return_value=mock_lock_manager),
        patch("click.echo") as mock_echo,
    ):
        # Act
        lock_context.release()

    # Assert
    mock_lock_manager.release.assert_called_once()
    mock_echo.assert_called_once_with("Removed lock file: /tmp/download/.lock")


def test_release_shows_message_when_not_locked(
    mock_settings: Settings, mock_path_manager: PathManager
) -> None:
    """ロックされていない場合、メッセージが表示されること.

    Arrange:
        LockManagerをモックしてis_locked()がFalseを返すようにする。

    Act:
        release()を呼び出す。

    Assert:
        release()が呼ばれず、メッセージが表示されること。
    """
    # Arrange
    lock_context = LockContext(mock_settings, mock_path_manager)
    mock_lock_manager = MagicMock()
    mock_lock_manager.is_locked.return_value = False

    with (
        patch("src.lock_context.LockManager", return_value=mock_lock_manager),
        patch("click.echo") as mock_echo,
    ):
        # Act
        lock_context.release()

    # Assert
    mock_lock_manager.release.assert_not_called()
    mock_echo.assert_called_once_with("Lock file does not exist.")
