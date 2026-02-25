"""ファイルロックユーティリティのテスト."""

from pathlib import Path

import pytest

from src.utils.lock_manager import LockManager


def test_acquire_lock_prevents_concurrent_access(tmp_path: Path) -> None:
    """acquireが二重起動を防止すること.

    Arrange:
        ロックを取得する。

    Act:
        同じロックを再度取得しようとする。

    Assert:
        RuntimeErrorが発生すること。
    """
    # Arrange
    lock_manager = LockManager(lock_dir=tmp_path)
    cm = lock_manager.acquire()
    cm.__enter__()

    try:
        # Act & Assert
        with pytest.raises(RuntimeError, match="Another instance"):
            lock_manager.acquire().__enter__()
    finally:
        cm.__exit__(None, None, None)


def test_acquire_lock_releases_on_exit(tmp_path: Path) -> None:
    """acquireが終了時にロックを解放すること.

    Arrange:
        ロックを取得して解放する。

    Act:
        再度ロックを取得する。

    Assert:
        ロックが正常に取得できること。
    """
    # Arrange
    lock_manager = LockManager(lock_dir=tmp_path)

    # Act
    with lock_manager.acquire():
        pass

    # Assert - should not raise
    with lock_manager.acquire():
        pass
