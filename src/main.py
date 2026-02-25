"""CLI エントリポイント.

Clickベースのコマンドラインインターフェースを提供する。
"""

import logging
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

import click
from mizu_common.google_drive_provider import GoogleDriveProvider

from src.models.stream_status import StreamStatus
from src.pipeline.cleanup import CleanupPipeline
from src.pipeline.discover import DiscoverPipeline
from src.pipeline.download import DownloadPipeline
from src.pipeline.recover import RecoverPipeline
from src.pipeline.thumbs import ThumbsPipeline
from src.pipeline.upload import UploadPipeline
from src.settings import Settings
from src.stream_repository import StreamRepository
from src.utils.already_running_error import AlreadyRunningError
from src.utils.lock_manager import LockManager
from src.utils.logging_config import LoggingConfig
from src.utils.path_manager import PathManager
from src.youtube_client import YouTubeClient


class Main:
    """CLIアプリケーションクラス."""

    def __init__(self) -> None:
        """アプリケーションを初期化する."""
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

    def get_youtube_client(self) -> YouTubeClient:
        """YouTubeクライアントを取得する."""
        return YouTubeClient(self._settings.youtube_api_key)

    def get_gdrive_provider(self) -> GoogleDriveProvider:
        """Google Driveプロバイダーを取得する."""
        return GoogleDriveProvider(
            credentials_path=self._settings.gdrive_credentials_path
        )

    def initialize(self, verbose: bool) -> None:
        """アプリケーションを初期化する.

        Args:
            verbose: 詳細ログを有効にするかどうか
        """
        level = logging.DEBUG if verbose else logging.INFO
        LoggingConfig(level=level)

        self._path_manager.ensure_directories()

        repository = self.get_repository()
        repository.init_db()

    def run(self) -> None:
        """全パイプラインを実行する.

        検出→ダウンロード→サムネイル抽出→アップロード→クリーンアップの
        全ステップを順番に実行する。
        """
        with self.acquire_lock():
            click.echo("Starting full pipeline...")

            repository = self.get_repository()
            youtube_client = self.get_youtube_client()
            gdrive_provider = self.get_gdrive_provider()

            click.echo("Discovering videos...")
            discovered = DiscoverPipeline(
                client=youtube_client,
                channel_ids=self._settings.youtube_channel_ids,
                repository=repository,
            ).discover_all()
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

    def discover_cmd(self) -> None:
        """新しいライブアーカイブを検出する."""
        with self.acquire_lock():
            repository = self.get_repository()
            youtube_client = self.get_youtube_client()
            count = DiscoverPipeline(
                client=youtube_client,
                channel_ids=self._settings.youtube_channel_ids,
                repository=repository,
            ).discover_all()
            click.echo(f"Discovered {count} new videos.")

    def download_cmd(self) -> None:
        """待機中の動画をダウンロードする."""
        with self.acquire_lock():
            repository = self.get_repository()
            count = DownloadPipeline(
                max_retries=self._settings.max_retries,
                download_dir=self._path_manager.download_dir,
                repository=repository,
            ).download_all()
            click.echo(f"Downloaded {count} videos.")

    def thumbs_cmd(self) -> None:
        """サムネイルを抽出する."""
        with self.acquire_lock():
            repository = self.get_repository()
            count = ThumbsPipeline(
                max_retries=self._settings.max_retries,
                thumbnail_interval=self._settings.thumbnail_interval,
                thumbnail_dir=self._path_manager.thumbnail_dir,
                repository=repository,
            ).extract_all()
            click.echo(f"Extracted thumbnails from {count} videos.")

    def upload_cmd(self) -> None:
        """Google Driveへアップロードする."""
        with self.acquire_lock():
            repository = self.get_repository()
            gdrive_provider = self.get_gdrive_provider()
            count = UploadPipeline(
                max_retries=self._settings.max_retries,
                gdrive_provider=gdrive_provider,
                gdrive_root_folder_id=self._settings.gdrive_root_folder_id,
                thumbnail_dir=self._path_manager.thumbnail_dir,
                repository=repository,
            ).upload_all()
            click.echo(f"Uploaded {count} videos.")

    def cleanup_cmd(self) -> None:
        """ローカルファイルを削除する."""
        with self.acquire_lock():
            repository = self.get_repository()
            count = CleanupPipeline(
                max_retries=self._settings.max_retries,
                download_dir=self._path_manager.download_dir,
                thumbnail_dir=self._path_manager.thumbnail_dir,
                repository=repository,
            ).cleanup_all()
            click.echo(f"Cleaned up {count} videos.")

    def recover_cmd(self) -> None:
        """中断されたストリームを回復する."""
        with self.acquire_lock():
            repository = self.get_repository()
            count = RecoverPipeline(
                max_retries=self._settings.max_retries,
                repository=repository,
            ).recover_all()
            click.echo(f"Recovered {count} streams.")

    def download_one(self, video_id: str) -> None:
        """指定された動画をダウンロードする.

        Args:
            video_id: YouTube動画ID
        """
        with self.acquire_lock():
            repository = self.get_repository()
            success = DownloadPipeline(
                max_retries=self._settings.max_retries,
                download_dir=self._path_manager.download_dir,
                repository=repository,
            ).download_video(video_id)
            if success:
                click.echo(f"Downloaded {video_id}")
            else:
                click.echo(f"Failed to download {video_id}", err=True)
                raise SystemExit(1)

    def upload_one(self, video_id: str) -> None:
        """指定された動画をアップロードする.

        Args:
            video_id: YouTube動画ID
        """
        repository = self.get_repository()
        stream = repository.get(video_id)
        if stream is None or stream.local_path is None:
            click.echo(f"Video {video_id} not found or not downloaded", err=True)
            raise SystemExit(1)

        with self.acquire_lock():
            gdrive_provider = self.get_gdrive_provider()
            success = UploadPipeline(
                max_retries=self._settings.max_retries,
                gdrive_provider=gdrive_provider,
                gdrive_root_folder_id=self._settings.gdrive_root_folder_id,
                thumbnail_dir=self._path_manager.thumbnail_dir,
                repository=repository,
            ).upload_video(video_id, stream.local_path)
            if success:
                click.echo(f"Uploaded {video_id}")
            else:
                click.echo(f"Failed to upload {video_id}", err=True)
                raise SystemExit(1)

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

    @staticmethod
    @click.group()
    @click.option("-v", "--verbose", is_flag=True, help="詳細ログを有効にする")
    @click.pass_context
    def cli(ctx: click.Context, verbose: bool) -> None:
        """YouTube Live Archive Downloader.

        YouTubeライブアーカイブを自動的にダウンロードし、
        Google Driveへアップロードする。
        """
        app = Main()
        app.initialize(verbose)
        ctx.obj = app

    @classmethod
    def register_commands(cls) -> None:
        """CLIコマンドを登録する."""
        cls.cli.command()(cls._run)
        cls.cli.command("discover-cmd")(cls._discover_cmd)
        cls.cli.command("download-cmd")(cls._download_cmd)
        cls.cli.command("thumbs-cmd")(cls._thumbs_cmd)
        cls.cli.command("upload-cmd")(cls._upload_cmd)
        cls.cli.command("cleanup-cmd")(cls._cleanup_cmd)
        cls.cli.command("recover-cmd")(cls._recover_cmd)
        cls.cli.command("download-one")(cls._download_one)
        cls.cli.command("upload-one")(cls._upload_one)
        cls.cli.command("status")(cls._status)
        cls.cli.command("unlock")(cls._unlock)

    @staticmethod
    @click.pass_obj
    def _run(app: "Main") -> None:
        app.run()

    @staticmethod
    @click.pass_obj
    def _discover_cmd(app: "Main") -> None:
        app.discover_cmd()

    @staticmethod
    @click.pass_obj
    def _download_cmd(app: "Main") -> None:
        app.download_cmd()

    @staticmethod
    @click.pass_obj
    def _thumbs_cmd(app: "Main") -> None:
        app.thumbs_cmd()

    @staticmethod
    @click.pass_obj
    def _upload_cmd(app: "Main") -> None:
        app.upload_cmd()

    @staticmethod
    @click.pass_obj
    def _cleanup_cmd(app: "Main") -> None:
        app.cleanup_cmd()

    @staticmethod
    @click.pass_obj
    def _recover_cmd(app: "Main") -> None:
        app.recover_cmd()

    @staticmethod
    @click.argument("video_id")
    @click.pass_obj
    def _download_one(app: "Main", video_id: str) -> None:
        app.download_one(video_id)

    @staticmethod
    @click.argument("video_id")
    @click.pass_obj
    def _upload_one(app: "Main", video_id: str) -> None:
        app.upload_one(video_id)

    @staticmethod
    @click.pass_obj
    def _status(app: "Main") -> None:
        app.status()

    @staticmethod
    @click.pass_obj
    def _unlock(app: "Main") -> None:
        app.unlock()


Main.register_commands()


if __name__ == "__main__":
    Main.cli()
