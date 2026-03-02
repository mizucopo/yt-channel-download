"""ロック管理モジュール."""

from collections.abc import Iterator
from contextlib import contextmanager

import click
from mizu_common import AlreadyRunningError, LockManager

from src.settings import Settings
from src.utils.path_manager import PathManager


class LockContext:
    """ロック管理コンテキスト."""

    def __init__(self, settings: Settings, path_manager: PathManager) -> None:
        """ロックコンテキストを初期化する.

        Args:
            settings: アプリケーション設定
            path_manager: パスマネージャ
        """
        self._settings = settings
        self._path_manager = path_manager

    @contextmanager
    def acquire(self) -> Iterator[None]:
        """ロックを取得するコンテキストマネージャ.

        他のインスタンスが実行中の場合は終了する。

        Yields:
            ロック取得中のコンテキスト
        """
        lock_manager = LockManager(
            lock_dir=self._path_manager.download_dir,
            stale_hours=self._settings.lock_stale_hours,
        )
        try:
            with lock_manager.acquire():
                yield
        except AlreadyRunningError:
            click.echo("Another instance is already running. Exiting.")
            raise SystemExit(0) from None

    def get_lock_manager(self) -> LockManager:
        """ロックマネージャを取得する."""
        return LockManager(lock_dir=self._path_manager.download_dir)

    def release(self) -> None:
        """ロックファイルを削除する."""
        lock_manager = LockManager(lock_dir=self._path_manager.download_dir)

        if not lock_manager.is_locked():
            click.echo("Lock file does not exist.")
            return

        lock_manager.release()
        click.echo(f"Removed lock file: {lock_manager.lock_path}")
