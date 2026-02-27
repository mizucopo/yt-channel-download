"""アプリケーション設定モジュール.

環境変数から設定を読み込み、アプリケーション全体で使用する設定値を提供する。
"""

from decouple import config
from mizu_common import GoogleScope
from pydantic import BaseModel, ConfigDict


class Settings(BaseModel):
    """アプリケーション設定.

    環境変数から読み込まれた設定値を保持する。
    """

    model_config = ConfigDict(frozen=False)

    # YouTube API設定
    youtube_channel_ids: list[str]

    # パス設定
    database_path: str
    download_dir: str
    thumbnail_dir: str

    # Google OAuth設定（YouTube API, Google Drive API共通）
    google_oauth_client_id: str
    google_refresh_token: str
    google_scopes: list[str]
    gdrive_root_folder_id: str

    # ダウンロード設定
    thumbnail_interval: int
    max_retries: int

    # ロック設定
    lock_stale_hours: int

    @staticmethod
    def _parse_channel_ids(value: str) -> list[str]:
        """チャンネルID文字列をパースする.

        Args:
            value: カンマ区切りのチャンネルID文字列

        Returns:
            チャンネルIDのリスト
        """
        if not value:
            return []
        return [v.strip() for v in value.split(",") if v.strip()]

    @classmethod
    def from_env(cls) -> "Settings":
        """環境変数から設定を読み込む.

        Returns:
            設定オブジェクト

        Raises:
            ValidationError: 必須設定が不足している場合
        """
        instance = cls(
            youtube_channel_ids=cls._parse_channel_ids(
                config("YOUTUBE_CHANNEL_IDS", default="")
            ),
            database_path=config("DATABASE_PATH", default="data/streams.db"),
            download_dir=config("DOWNLOAD_DIR", default="data/downloads"),
            thumbnail_dir=config("THUMBNAIL_DIR", default="data/thumbnails"),
            google_oauth_client_id=config("GOOGLE_OAUTH_CLIENT_ID", default=""),
            google_refresh_token=config("GOOGLE_REFRESH_TOKEN", default=""),
            google_scopes=[
                GoogleScope.YOUTUBE_READONLY,
                GoogleScope.DRIVE_FILE,
            ],
            gdrive_root_folder_id=config("GDRIVE_ROOT_FOLDER_ID", default=""),
            thumbnail_interval=config("THUMBNAIL_INTERVAL", default=60, cast=int),
            max_retries=config("MAX_RETRIES", default=3, cast=int),
            lock_stale_hours=config("LOCK_STALE_HOURS", default=3, cast=int),
        )

        # 必須設定の検証
        missing: list[str] = []
        if not instance.youtube_channel_ids:
            missing.append("YOUTUBE_CHANNEL_IDS")
        if not instance.google_oauth_client_id:
            missing.append("GOOGLE_OAUTH_CLIENT_ID")
        if not instance.google_refresh_token:
            missing.append("GOOGLE_REFRESH_TOKEN")
        if not instance.gdrive_root_folder_id:
            missing.append("GDRIVE_ROOT_FOLDER_ID")

        if missing:
            missing_str = ", ".join(missing)
            raise ValueError(f"必須の環境変数が設定されていません: {missing_str}")

        return instance
