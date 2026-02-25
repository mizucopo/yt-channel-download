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
from src.utils.lock_manager import LockManager
from src.utils.logging_config import LoggingConfig
from src.utils.path_manager import PathManager
from src.youtube_client import YouTubeClient


def _get_settings() -> Settings:
    """設定を取得する."""
    return Settings()


def _get_path_manager() -> PathManager:
    """パスマネージャを取得する."""
    settings = _get_settings()
    return PathManager(
        download_dir=Path(settings.download_dir),
        thumbnail_dir=Path(settings.thumbnail_dir),
        database_path=Path(settings.database_path),
    )


def _get_repository() -> StreamRepository:
    """ストリームリポジトリを取得する."""
    path_manager = _get_path_manager()
    return StreamRepository(path_manager.database_path)


@contextmanager
def _acquire_lock() -> Iterator[None]:
    """ロックを取得するコンテキストマネージャ."""
    settings = _get_settings()
    path_manager = _get_path_manager()
    lock_manager = LockManager(
        lock_dir=path_manager.download_dir,
        stale_hours=settings.lock_stale_hours,
    )
    with lock_manager.acquire():
        yield


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="詳細ログを有効にする")
def cli(verbose: bool) -> None:
    """YouTube Live Archive Downloader.

    YouTubeライブアーカイブを自動的にダウンロードし、
    Google Driveへアップロードする。
    """
    level = logging.DEBUG if verbose else logging.INFO
    LoggingConfig(level=level)

    # 初期化
    path_manager = _get_path_manager()
    path_manager.ensure_directories()

    repository = StreamRepository(path_manager.database_path)
    repository.init_db()


@cli.command()
def run() -> None:
    """全パイプラインを実行する.

    検出→ダウンロード→サムネイル抽出→アップロード→クリーンアップの
    全ステップを順番に実行する。
    """
    settings = _get_settings()
    path_manager = _get_path_manager()

    with _acquire_lock():
        click.echo("Starting full pipeline...")

        # 共通設定
        repository = _get_repository()
        youtube_client = YouTubeClient(settings.youtube_api_key)
        gdrive_provider = GoogleDriveProvider(
            credentials_path=settings.gdrive_credentials_path
        )

        click.echo("Discovering videos...")
        discovered = DiscoverPipeline(
            client=youtube_client,
            channel_ids=settings.youtube_channel_ids,
            repository=repository,
        ).discover_all()
        click.echo(f"  Discovered: {discovered} new videos")

        click.echo("Downloading videos...")
        downloaded = DownloadPipeline(
            max_retries=settings.max_retries,
            download_dir=path_manager.download_dir,
            repository=repository,
        ).download_all()
        click.echo(f"  Downloaded: {downloaded} videos")

        click.echo("Extracting thumbnails...")
        thumbnailed = ThumbsPipeline(
            max_retries=settings.max_retries,
            thumbnail_interval=settings.thumbnail_interval,
            thumbnail_dir=path_manager.thumbnail_dir,
            repository=repository,
        ).extract_all()
        click.echo(f"  Extracted: {thumbnailed} videos")

        click.echo("Uploading to Google Drive...")
        uploaded = UploadPipeline(
            max_retries=settings.max_retries,
            gdrive_provider=gdrive_provider,
            gdrive_root_folder_id=settings.gdrive_root_folder_id,
            thumbnail_dir=path_manager.thumbnail_dir,
            repository=repository,
        ).upload_all()
        click.echo(f"  Uploaded: {uploaded} videos")

        click.echo("Cleaning up local files...")
        cleaned = CleanupPipeline(
            max_retries=settings.max_retries,
            download_dir=path_manager.download_dir,
            thumbnail_dir=path_manager.thumbnail_dir,
            repository=repository,
        ).cleanup_all()
        click.echo(f"  Cleaned: {cleaned} videos")

        click.echo("Pipeline completed.")


@cli.command()
def discover_cmd() -> None:
    """新しいライブアーカイブを検出する."""
    settings = _get_settings()

    with _acquire_lock():
        repository = _get_repository()
        youtube_client = YouTubeClient(settings.youtube_api_key)
        count = DiscoverPipeline(
            client=youtube_client,
            channel_ids=settings.youtube_channel_ids,
            repository=repository,
        ).discover_all()
        click.echo(f"Discovered {count} new videos.")


@cli.command()
def download_cmd() -> None:
    """待機中の動画をダウンロードする."""
    settings = _get_settings()
    path_manager = _get_path_manager()

    with _acquire_lock():
        repository = _get_repository()
        count = DownloadPipeline(
            max_retries=settings.max_retries,
            download_dir=path_manager.download_dir,
            repository=repository,
        ).download_all()
        click.echo(f"Downloaded {count} videos.")


@cli.command()
def thumbs_cmd() -> None:
    """サムネイルを抽出する."""
    settings = _get_settings()
    path_manager = _get_path_manager()

    with _acquire_lock():
        repository = _get_repository()
        count = ThumbsPipeline(
            max_retries=settings.max_retries,
            thumbnail_interval=settings.thumbnail_interval,
            thumbnail_dir=path_manager.thumbnail_dir,
            repository=repository,
        ).extract_all()
        click.echo(f"Extracted thumbnails from {count} videos.")


@cli.command()
def upload_cmd() -> None:
    """Google Driveへアップロードする."""
    settings = _get_settings()
    path_manager = _get_path_manager()

    with _acquire_lock():
        repository = _get_repository()
        gdrive_provider = GoogleDriveProvider(
            credentials_path=settings.gdrive_credentials_path
        )
        count = UploadPipeline(
            max_retries=settings.max_retries,
            gdrive_provider=gdrive_provider,
            gdrive_root_folder_id=settings.gdrive_root_folder_id,
            thumbnail_dir=path_manager.thumbnail_dir,
            repository=repository,
        ).upload_all()
        click.echo(f"Uploaded {count} videos.")


@cli.command()
def cleanup_cmd() -> None:
    """ローカルファイルを削除する."""
    settings = _get_settings()
    path_manager = _get_path_manager()

    with _acquire_lock():
        repository = _get_repository()
        count = CleanupPipeline(
            max_retries=settings.max_retries,
            download_dir=path_manager.download_dir,
            thumbnail_dir=path_manager.thumbnail_dir,
            repository=repository,
        ).cleanup_all()
        click.echo(f"Cleaned up {count} videos.")


@cli.command()
def recover_cmd() -> None:
    """中断されたストリームを回復する."""
    settings = _get_settings()

    with _acquire_lock():
        repository = _get_repository()
        count = RecoverPipeline(
            max_retries=settings.max_retries,
            repository=repository,
        ).recover_all()
        click.echo(f"Recovered {count} streams.")


@cli.command()
@click.argument("video_id")
def download_one(video_id: str) -> None:
    """指定された動画をダウンロードする.

    VIDEO_ID: YouTube動画ID
    """
    settings = _get_settings()
    path_manager = _get_path_manager()

    with _acquire_lock():
        repository = _get_repository()
        success = DownloadPipeline(
            max_retries=settings.max_retries,
            download_dir=path_manager.download_dir,
            repository=repository,
        ).download_video(video_id)
        if success:
            click.echo(f"Downloaded {video_id}")
        else:
            click.echo(f"Failed to download {video_id}", err=True)
            raise SystemExit(1)


@cli.command()
@click.argument("video_id")
def upload_one(video_id: str) -> None:
    """指定された動画をアップロードする.

    VIDEO_ID: YouTube動画ID
    """
    settings = _get_settings()
    path_manager = _get_path_manager()
    repository = _get_repository()
    stream = repository.get(video_id)
    if stream is None or stream.local_path is None:
        click.echo(f"Video {video_id} not found or not downloaded", err=True)
        raise SystemExit(1)

    with _acquire_lock():
        gdrive_provider = GoogleDriveProvider(
            credentials_path=settings.gdrive_credentials_path
        )
        success = UploadPipeline(
            max_retries=settings.max_retries,
            gdrive_provider=gdrive_provider,
            gdrive_root_folder_id=settings.gdrive_root_folder_id,
            thumbnail_dir=path_manager.thumbnail_dir,
            repository=repository,
        ).upload_video(video_id, stream.local_path)
        if success:
            click.echo(f"Uploaded {video_id}")
        else:
            click.echo(f"Failed to upload {video_id}", err=True)
            raise SystemExit(1)


@cli.command()
def status() -> None:
    """現在のステータスを表示する."""
    repository = _get_repository()

    click.echo("Current status:")
    for status in StreamStatus:
        streams = repository.get_by_status(status)
        click.echo(f"  {status.value}: {len(streams)}")


@cli.command()
def unlock() -> None:
    """ロックファイルを削除する."""
    path_manager = _get_path_manager()
    lock_manager = LockManager(lock_dir=path_manager.download_dir)

    if not lock_manager.is_locked():
        click.echo("Lock file does not exist.")
        return

    lock_manager.release()
    click.echo(f"Removed lock file: {lock_manager.lock_path}")


if __name__ == "__main__":
    cli()
