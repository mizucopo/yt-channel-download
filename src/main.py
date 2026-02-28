"""CLI エントリポイント.

Clickベースのコマンドラインインターフェースを提供する。
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import click
from mizu_common import (
    AlreadyRunningError,
    GoogleOAuthClient,
    GoogleScope,
    LockManager,
    LoggingConfigurator,
    YouTubeClient,
)
from mizu_common.google_drive_provider import GoogleDriveProvider

from src.constants.stream_status import StreamStatus
from src.pipeline.cleanup_pipeline import CleanupPipeline
from src.pipeline.discover_pipeline import DiscoverPipeline
from src.pipeline.download_pipeline import DownloadPipeline
from src.pipeline.recover_pipeline import RecoverPipeline
from src.pipeline.thumbs_pipeline import ThumbsPipeline
from src.pipeline.upload_pipeline import UploadPipeline
from src.repository.stream_repository import StreamRepository
from src.settings import Settings
from src.utils.path_manager import PathManager


class Main:
    """CLIアプリケーションクラス."""

    def __init__(self, verbose: bool = False) -> None:
        """アプリケーションを初期化する.

        Args:
            verbose: 詳細ログを有効にするかどうか
        """
        self._verbose = verbose
        self._settings = Settings.from_env()
        self._path_manager = PathManager(
            download_dir=Path(self._settings.download_dir),
            thumbnail_dir=Path(self._settings.thumbnail_dir),
            database_path=Path(self._settings.database_path),
        )

    @property
    def settings(self) -> Settings:
        """設定を取得する."""
        return self._settings

    @property
    def path_manager(self) -> PathManager:
        """パスマネージャを取得する."""
        return self._path_manager

    def get_repository(self) -> StreamRepository:
        """ストリームリポジトリを取得する."""
        return StreamRepository(self._path_manager.database_path)

    @contextmanager
    def acquire_lock(self) -> Iterator[None]:
        """ロックを取得するコンテキストマネージャ."""
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

    def get_oauth_client(self) -> GoogleOAuthClient:
        """Google OAuth認証クライアントを取得する."""
        return GoogleOAuthClient(
            oauth_client_id=self._settings.google_oauth_client_id,
            oauth_client_secret=self._settings.google_oauth_client_secret,
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

    def initialize(self) -> None:
        """アプリケーションを初期化する."""
        level = logging.DEBUG if self._verbose else logging.INFO
        LoggingConfigurator(level=level)

        self._path_manager.ensure_directories()

        repository = self.get_repository()
        repository.init_db()

    def run(self) -> None:
        """全パイプラインを実行する.

        復旧→検出→ダウンロード→サムネイル抽出→アップロード→クリーンアップの
        全ステップを順番に実行する。
        """
        with self.acquire_lock():
            click.echo("Starting full pipeline...")

            repository = self.get_repository()
            is_first_run = repository.is_empty()
            youtube_client = self.get_youtube_client()
            gdrive_provider = self.get_gdrive_provider(
                folder_id=self._settings.gdrive_root_folder_id
            )

            click.echo("Recovering streams...")
            recovered = RecoverPipeline(
                max_retries=self._settings.max_retries,
                thumbnail_dir=self._path_manager.thumbnail_dir,
                repository=repository,
            ).recover_all()
            click.echo(f"  Recovered: {recovered} streams")

            click.echo("Discovering videos...")
            discovered = DiscoverPipeline(
                client=youtube_client,
                channel_ids=self._settings.youtube_channel_ids,
                repository=repository,
                is_first_run=is_first_run,
            ).discover_all()
            if is_first_run and discovered > 0:
                click.echo(
                    f"  First run: {discovered} existing videos registered as canceled"
                )
            else:
                click.echo(f"  Discovered: {discovered} new videos")

            click.echo("Downloading videos...")
            downloaded = DownloadPipeline(
                max_retries=self._settings.max_retries,
                download_dir=self._path_manager.download_dir,
                repository=repository,
            ).download_all()
            click.echo(f"  Downloaded: {downloaded} videos")

            click.echo("Extracting thumbnails...")
            thumbnailed = ThumbsPipeline(
                max_retries=self._settings.max_retries,
                thumbnail_interval=self._settings.thumbnail_interval,
                thumbnail_quality=self._settings.thumbnail_quality,
                thumbnail_dir=self._path_manager.thumbnail_dir,
                repository=repository,
            ).extract_all()
            click.echo(f"  Extracted: {thumbnailed} videos")

            click.echo("Uploading to Google Drive...")
            uploaded = UploadPipeline(
                max_retries=self._settings.max_retries,
                gdrive_provider=gdrive_provider,
                gdrive_root_folder_id=self._settings.gdrive_root_folder_id,
                thumbnail_dir=self._path_manager.thumbnail_dir,
                repository=repository,
            ).upload_all()
            click.echo(f"  Uploaded: {uploaded} videos")

            click.echo("Cleaning up local files...")
            cleaned = CleanupPipeline(
                max_retries=self._settings.max_retries,
                download_dir=self._path_manager.download_dir,
                thumbnail_dir=self._path_manager.thumbnail_dir,
                repository=repository,
            ).cleanup_all()
            click.echo(f"  Cleaned: {cleaned} videos")

            click.echo("Pipeline completed.")

    def status(self) -> None:
        """現在のステータスを表示する."""
        repository = self.get_repository()

        click.echo("Current status:")
        for status in StreamStatus:
            streams = repository.get_by_status(status)
            click.echo(f"  {status.value}: {len(streams)}")

    def unlock(self) -> None:
        """ロックファイルを削除する."""
        lock_manager = self.get_lock_manager()

        if not lock_manager.is_locked():
            click.echo("Lock file does not exist.")
            return

        lock_manager.release()
        click.echo(f"Removed lock file: {lock_manager.lock_path}")

    def auth_cmd(self) -> None:
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

    def redownload(self, video_id: str) -> None:
        """指定された動画を再ダウンロード対象にする."""
        repository = self.get_repository()

        stream = repository.get(video_id)
        if stream is None:
            click.echo(f"Error: Video {video_id} not found in database.", err=True)
            raise SystemExit(1)

        if repository.reset_for_redownload(video_id):
            click.echo(f"Video {video_id} has been reset for redownload.")
        else:
            click.echo(f"Error: Failed to reset video {video_id}.", err=True)
            raise SystemExit(1)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="詳細ログを有効にする")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """YouTube Live Archive Downloader.

    YouTubeライブアーカイブを自動的にダウンロードし、
    Google Driveへアップロードする。
    """
    app = Main(verbose=verbose)
    ctx.obj = app


@cli.command()
@click.pass_obj
def run(app: Main) -> None:
    """全パイプラインを実行する."""
    app.initialize()
    app.run()


@cli.command()
@click.pass_obj
def status(app: Main) -> None:
    """現在のステータスを表示する."""
    app.initialize()
    app.status()


@cli.command()
@click.pass_obj
def unlock(app: Main) -> None:
    """ロックファイルを削除する."""
    app.initialize()
    app.unlock()


@cli.command()
@click.pass_obj
def auth(app: Main) -> None:
    """Google OAuth認証を実行する."""
    app.auth_cmd()


@cli.command()
@click.argument("video_id")
@click.pass_obj
def redownload(app: Main, video_id: str) -> None:
    """指定された動画を再ダウンロード対象にする."""
    app.initialize()
    app.redownload(video_id)


if __name__ == "__main__":
    cli()
