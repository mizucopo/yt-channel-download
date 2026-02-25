"""CLI エントリポイント.

Clickベースのコマンドラインインターフェースを提供する。
"""

import logging
from pathlib import Path

import click
from mizu_common.google_drive_provider import GoogleDriveProvider

from src.config import settings
from src.pipeline.cleanup import CleanupPipeline
from src.pipeline.discover import DiscoverPipeline
from src.pipeline.download import DownloadPipeline
from src.pipeline.recover import RecoverPipeline
from src.pipeline.thumbs import ThumbsPipeline
from src.pipeline.upload import UploadPipeline
from src.repository import StreamRepository
from src.utils.locking import acquire_lock
from src.utils.logging import setup_logging
from src.utils.paths import ensure_directories
from src.youtube_client import YouTubeClient


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="詳細ログを有効にする")
def cli(verbose: bool) -> None:
    """YouTube Live Archive Downloader.

    YouTubeライブアーカイブを自動的にダウンロードし、
    Google Driveへアップロードする。
    """
    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level)

    # 初期化
    ensure_directories(
        settings.download_dir,
        settings.thumbnail_dir,
        settings.database_path,
    )

    repository = StreamRepository(Path(settings.database_path))
    repository.init_db()


def _get_repository() -> StreamRepository:
    """ストリームリポジトリを取得する."""
    return StreamRepository(Path(settings.database_path))


@cli.command()
def run() -> None:
    """全パイプラインを実行する.

    検出→ダウンロード→サムネイル抽出→アップロード→クリーンアップの
    全ステップを順番に実行する。
    """
    with acquire_lock():
        click.echo("Starting full pipeline...")

        # 共通設定
        repository = _get_repository()
        download_dir = Path(settings.download_dir)
        thumbnail_dir = Path(settings.thumbnail_dir)
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
            download_dir=download_dir,
            repository=repository,
        ).download_all()
        click.echo(f"  Downloaded: {downloaded} videos")

        click.echo("Extracting thumbnails...")
        thumbnailed = ThumbsPipeline(
            max_retries=settings.max_retries,
            thumbnail_interval=settings.thumbnail_interval,
            thumbnail_dir=thumbnail_dir,
            repository=repository,
        ).extract_all()
        click.echo(f"  Extracted: {thumbnailed} videos")

        click.echo("Uploading to Google Drive...")
        uploaded = UploadPipeline(
            max_retries=settings.max_retries,
            gdrive_provider=gdrive_provider,
            gdrive_root_folder_id=settings.gdrive_root_folder_id,
            thumbnail_dir=thumbnail_dir,
            repository=repository,
        ).upload_all()
        click.echo(f"  Uploaded: {uploaded} videos")

        click.echo("Cleaning up local files...")
        cleaned = CleanupPipeline(
            max_retries=settings.max_retries,
            download_dir=download_dir,
            thumbnail_dir=thumbnail_dir,
            repository=repository,
        ).cleanup_all()
        click.echo(f"  Cleaned: {cleaned} videos")

        click.echo("Pipeline completed.")


@cli.command()
def discover_cmd() -> None:
    """新しいライブアーカイブを検出する."""
    with acquire_lock():
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
    with acquire_lock():
        repository = _get_repository()
        count = DownloadPipeline(
            max_retries=settings.max_retries,
            download_dir=Path(settings.download_dir),
            repository=repository,
        ).download_all()
        click.echo(f"Downloaded {count} videos.")


@cli.command()
def thumbs_cmd() -> None:
    """サムネイルを抽出する."""
    with acquire_lock():
        repository = _get_repository()
        count = ThumbsPipeline(
            max_retries=settings.max_retries,
            thumbnail_interval=settings.thumbnail_interval,
            thumbnail_dir=Path(settings.thumbnail_dir),
            repository=repository,
        ).extract_all()
        click.echo(f"Extracted thumbnails from {count} videos.")


@cli.command()
def upload_cmd() -> None:
    """Google Driveへアップロードする."""
    with acquire_lock():
        repository = _get_repository()
        gdrive_provider = GoogleDriveProvider(
            credentials_path=settings.gdrive_credentials_path
        )
        count = UploadPipeline(
            max_retries=settings.max_retries,
            gdrive_provider=gdrive_provider,
            gdrive_root_folder_id=settings.gdrive_root_folder_id,
            thumbnail_dir=Path(settings.thumbnail_dir),
            repository=repository,
        ).upload_all()
        click.echo(f"Uploaded {count} videos.")


@cli.command()
def cleanup_cmd() -> None:
    """ローカルファイルを削除する."""
    with acquire_lock():
        repository = _get_repository()
        count = CleanupPipeline(
            max_retries=settings.max_retries,
            download_dir=Path(settings.download_dir),
            thumbnail_dir=Path(settings.thumbnail_dir),
            repository=repository,
        ).cleanup_all()
        click.echo(f"Cleaned up {count} videos.")


@cli.command()
def recover_cmd() -> None:
    """中断されたストリームを回復する."""
    with acquire_lock():
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
    with acquire_lock():
        repository = _get_repository()
        success = DownloadPipeline(
            max_retries=settings.max_retries,
            download_dir=Path(settings.download_dir),
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
    repository = _get_repository()
    stream = repository.get(video_id)
    if stream is None or stream.local_path is None:
        click.echo(f"Video {video_id} not found or not downloaded", err=True)
        raise SystemExit(1)

    with acquire_lock():
        gdrive_provider = GoogleDriveProvider(
            credentials_path=settings.gdrive_credentials_path
        )
        success = UploadPipeline(
            max_retries=settings.max_retries,
            gdrive_provider=gdrive_provider,
            gdrive_root_folder_id=settings.gdrive_root_folder_id,
            thumbnail_dir=Path(settings.thumbnail_dir),
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
    statuses = [
        "discovered",
        "downloading",
        "downloaded",
        "thumbs_done",
        "uploading",
        "uploaded",
        "cleaned",
    ]

    click.echo("Current status:")
    for status_name in statuses:
        streams = repository.get_by_status(status_name)
        click.echo(f"  {status_name}: {len(streams)}")


if __name__ == "__main__":
    cli()
