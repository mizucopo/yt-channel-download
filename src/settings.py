"""アプリケーション設定モジュール.

環境変数から設定を読み込み、アプリケーション全体で使用する設定値を提供する。
"""

from typing import Any

from decouple import config
from pydantic import BaseModel, ConfigDict, field_validator


class Settings(BaseModel):
    """アプリケーション設定.

    環境変数から読み込まれた設定値を保持する。
    """

    model_config = ConfigDict(frozen=False)

    # YouTube API設定
    youtube_api_key: str = config("YOUTUBE_API_KEY", default="")
    youtube_channel_ids: list[str] = []

    # パス設定
    database_path: str = config("DATABASE_PATH", default="data/streams.db")
    download_dir: str = config("DOWNLOAD_DIR", default="data/downloads")
    thumbnail_dir: str = config("THUMBNAIL_DIR", default="data/thumbnails")

    # Google Drive設定
    gdrive_credentials_path: str = config(
        "GDRIVE_CREDENTIALS_PATH", default="credentials.json"
    )
    gdrive_root_folder_id: str = config("GDRIVE_ROOT_FOLDER_ID", default="")

    # ダウンロード設定
    thumbnail_interval: int = config("THUMBNAIL_INTERVAL", default=60, cast=int)
    max_retries: int = config("MAX_RETRIES", default=3, cast=int)

    # ロック設定
    lock_stale_hours: int = config("LOCK_STALE_HOURS", default=3, cast=int)

    @field_validator("youtube_channel_ids", mode="before")
    @classmethod
    def _parse_channel_ids(cls, _value: Any) -> list[str]:
        """チャンネルID文字列をパースする.

        Args:
            _value: 使用しない（環境変数から直接読み込むため）

        Returns:
            チャンネルIDのリスト
        """
        raw = config("YOUTUBE_CHANNEL_IDS", default="")
        if not raw:
            return []
        return [v.strip() for v in raw.split(",") if v.strip()]
