"""mizu-common stubs."""

from datetime import datetime
from pathlib import Path

# Lock Manager
class AlreadyRunningError(Exception):
    """他のインスタンスが実行中の場合の例外."""

    ...

class StaleLockError(Exception):
    """古いロックファイルが検出された場合の例外."""

    ...

class LockManager:
    """ロックマネージャ."""

    def __init__(self, lock_dir: Path, stale_hours: int = 3) -> None: ...
    def acquire(self) -> "LockManager": ...
    def __enter__(self) -> None: ...
    def __exit__(self, *args: object) -> None: ...
    def is_locked(self) -> bool: ...
    def release(self) -> None: ...
    @property
    def lock_path(self) -> Path: ...

# Logging
class LoggingConfigurator:
    """ログ設定."""

    def __init__(self, level: int = 20) -> None: ...

# Google OAuth
class GoogleScope:
    """Google API スコープ."""

    YOUTUBE_READONLY: str = "https://www.googleapis.com/auth/youtube.readonly"
    DRIVE_FILE: str = "https://www.googleapis.com/auth/drive.file"

class GoogleOAuthClient:
    """Google OAuth認証クライアント."""

    def __init__(
        self,
        oauth_client_id: str,
        refresh_token: str,
        scopes: list[str],
    ) -> None: ...
    def get_access_token(self) -> str: ...
    @staticmethod
    def authenticate(
        client_id: str,
        client_secret: str,
        scopes: list[str],
    ) -> str | None: ...

# YouTube
class YouTubeVideoInfo:
    """YouTube動画情報."""

    video_id: str
    title: str
    published_at: datetime
    duration: str

    def __init__(
        self,
        video_id: str,
        title: str,
        published_at: datetime,
        duration: str,
    ) -> None: ...

class YouTubeClient:
    """YouTube APIクライアント."""

    def __init__(self, oauth_client: GoogleOAuthClient) -> None: ...
    def get_live_archives(self, channel_id: str) -> list[YouTubeVideoInfo]: ...

__all__ = [
    "AlreadyRunningError",
    "StaleLockError",
    "LockManager",
    "LoggingConfigurator",
    "GoogleScope",
    "GoogleOAuthClient",
    "YouTubeVideoInfo",
    "YouTubeClient",
]
