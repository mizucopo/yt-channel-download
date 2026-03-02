"""Google OAuth認証コマンド."""

import click
from mizu_common import GoogleOAuthClient, GoogleScope

from src.settings import Settings


class AuthCommand:
    """Google OAuth認証コマンド."""

    def __init__(self, settings: Settings) -> None:
        """コマンドを初期化する.

        Args:
            settings: アプリケーション設定
        """
        self._settings = settings

    def execute(self) -> None:
        """Google OAuth認証を実行し、リフレッシュトークンを取得する."""
        if not self._settings.google_oauth_client_secret:
            click.echo("Error: GOOGLE_OAUTH_CLIENT_SECRET is not set.", err=True)
            raise SystemExit(1)

        if not self._settings.google_oauth_client_id:
            click.echo("Error: GOOGLE_OAUTH_CLIENT_ID is not set.", err=True)
            raise SystemExit(1)

        refresh_token = GoogleOAuthClient.authenticate(
            self._settings.google_oauth_client_id,
            self._settings.google_oauth_client_secret,
            [GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE],
        )

        if refresh_token:
            click.echo("\nAuthentication successful!")
            click.echo("Please add the following to your .env file:")
            click.echo(f"GOOGLE_REFRESH_TOKEN={refresh_token}")
        else:
            click.echo("\nAuthentication failed.", err=True)
            raise SystemExit(1)
