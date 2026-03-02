"""外部サービスクライアントのファクトリ."""

from mizu_common import GoogleOAuthClient, YouTubeClient
from mizu_common.google_drive_provider import GoogleDriveProvider

from src.notifications.discord_notifier import DiscordNotifier
from src.settings import Settings
from src.utils.path_manager import PathManager


class ClientFactory:
    """外部サービスクライアントを生成するファクトリ."""

    def __init__(self, settings: Settings, path_manager: PathManager) -> None:
        """ファクトリを初期化する.

        Args:
            settings: アプリケーション設定
            path_manager: パスマネージャ
        """
        self._settings = settings
        self._path_manager = path_manager

    def get_oauth_client(self) -> GoogleOAuthClient:
        """Google OAuth認証クライアントを取得する."""
        return GoogleOAuthClient(
            oauth_client_id=self._settings.google_oauth_client_id,
            oauth_client_secret=self._settings.google_oauth_client_secret or "",
            refresh_token=self._settings.google_refresh_token,
            scopes=self._settings.google_scopes,
        )

    def get_youtube_client(self) -> YouTubeClient:
        """YouTubeクライアントを取得する."""
        return YouTubeClient(oauth_client=self.get_oauth_client())

    def get_gdrive_provider(self, folder_id: str) -> GoogleDriveProvider:
        """Google Driveプロバイダーを取得する.

        Args:
            folder_id: Google Drive フォルダ ID
        """
        return GoogleDriveProvider.from_credentials(
            folder_id=folder_id,
            client_id=self._settings.google_oauth_client_id,
            client_secret=self._settings.google_oauth_client_secret or "",
            refresh_token=self._settings.google_refresh_token,
        )

    def get_discord_notifier(self) -> DiscordNotifier | None:
        """Discord通知クライアントを取得する.

        Webhook URLが設定されていない場合はNoneを返す。

        Returns:
            DiscordNotifierまたはNone
        """
        webhook_url = self._settings.discord_webhook_url
        if not webhook_url:
            return None

        gdrive_folder_url = f"https://drive.google.com/drive/folders/{self._settings.gdrive_root_folder_id}"
        return DiscordNotifier(
            webhook_url=webhook_url,
            gdrive_folder_url=gdrive_folder_url,
        )
