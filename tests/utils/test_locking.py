"""ファイルロックユーティリティのテスト."""

from pathlib import Path

import pytest

from src.utils.locking import acquire_lock


def test_acquire_lock_prevents_concurrent_access(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """acquire_lockが二重起動を防止すること.

    Arrange:
        ロックを取得する。

    Act:
        同じロックを再度取得しようとする。

    Assert:
        RuntimeErrorが発生すること。
    """
    # Arrange
    monkeypatch.setattr("src.config.settings.download_dir", str(tmp_path))

    # Act & Assert
    with acquire_lock(), pytest.raises(RuntimeError, match="Another instance"):  # noqa: SIM117
        with acquire_lock():
            pass


def test_acquire_lock_releases_on_exit(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """acquire_lockが終了時にロックを解放すること.

    Arrange:
        ロックを取得して解放する。

    Act:
        再度ロックを取得する。

    Assert:
        ロックが正常に取得できること。
    """
    # Arrange
    monkeypatch.setattr("src.config.settings.download_dir", str(tmp_path))

    # Act
    with acquire_lock():
        pass

    # Assert - should not raise
    with acquire_lock():
        pass
