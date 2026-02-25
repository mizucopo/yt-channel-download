"""ファイルロックユーティリティ.

二重起動防止のためのファイルロック機能を提供する。
"""

import fcntl
import os
from collections.abc import Iterator
from contextlib import contextmanager, suppress
from pathlib import Path

from src.settings import Settings


@contextmanager
def acquire_lock() -> Iterator[None]:
    """アプリケーションロックを取得する.

    ロックファイルを作成し、排他ロックを取得する。
    既にロックされている場合はRuntimeErrorを発生させる。

    Yields:
        None

    Raises:
        RuntimeError: 既にロックされている場合
    """
    settings = Settings()
    lock_path = Path(settings.download_dir) / ".app.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    with open(lock_path, "w") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
        except BlockingIOError as e:
            raise RuntimeError("Another instance is already running") from e
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            with suppress(OSError):
                os.unlink(lock_path)
