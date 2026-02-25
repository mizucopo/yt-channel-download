"""CLI エントリポイント.

Clickベースのコマンドラインインターフェースを提供する。
"""

import click

from src import db
from src.pipeline.cleanup import CleanupPipeline
from src.pipeline.discover import DiscoverPipeline
from src.pipeline.download import DownloadPipeline
from src.pipeline.recover import RecoverPipeline
from src.pipeline.thumbs import ThumbsPipeline
from src.pipeline.upload import UploadPipeline
from src.utils.locking import acquire_lock
from src.utils.logging import setup_logging
from src.utils.paths import ensure_directories


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="詳細ログを有効にする")
def cli(verbose: bool) -> None:
    """YouTube Live Archive Downloader.

    YouTubeライブアーカイブを自動的にダウンロードし、
    Google Driveへアップロードする。
    """
    import logging

    level = logging.DEBUG if verbose else logging.INFO
    setup_logging(level)

    # 初期化
    ensure_directories()
    db.init_db()


@cli.command()
def run() -> None:
    """全パイプラインを実行する.

    検出→ダウンロード→サムネイル抽出→アップロード→クリーンアップの
    全ステップを順番に実行する。
    """
    with acquire_lock():
        click.echo("Starting full pipeline...")

        click.echo("Discovering videos...")
        discovered = DiscoverPipeline().discover_videos()
        click.echo(f"  Discovered: {discovered} new videos")

        click.echo("Downloading videos...")
        downloaded = DownloadPipeline().download_all()
        click.echo(f"  Downloaded: {downloaded} videos")

        click.echo("Extracting thumbnails...")
        thumbnailed = ThumbsPipeline().extract_all()
        click.echo(f"  Extracted: {thumbnailed} videos")

        click.echo("Uploading to Google Drive...")
        uploaded = UploadPipeline().upload_all()
        click.echo(f"  Uploaded: {uploaded} videos")

        click.echo("Cleaning up local files...")
        cleaned = CleanupPipeline().cleanup_all()
        click.echo(f"  Cleaned: {cleaned} videos")

        click.echo("Pipeline completed.")


@cli.command()
def discover_cmd() -> None:
    """新しいライブアーカイブを検出する."""
    with acquire_lock():
        count = DiscoverPipeline().discover_videos()
        click.echo(f"Discovered {count} new videos.")


@cli.command()
def download_cmd() -> None:
    """待機中の動画をダウンロードする."""
    with acquire_lock():
        count = DownloadPipeline().download_all()
        click.echo(f"Downloaded {count} videos.")


@cli.command()
def thumbs_cmd() -> None:
    """サムネイルを抽出する."""
    with acquire_lock():
        count = ThumbsPipeline().extract_all()
        click.echo(f"Extracted thumbnails from {count} videos.")


@cli.command()
def upload_cmd() -> None:
    """Google Driveへアップロードする."""
    with acquire_lock():
        count = UploadPipeline().upload_all()
        click.echo(f"Uploaded {count} videos.")


@cli.command()
def cleanup_cmd() -> None:
    """ローカルファイルを削除する."""
    with acquire_lock():
        count = CleanupPipeline().cleanup_all()
        click.echo(f"Cleaned up {count} videos.")


@cli.command()
def recover_cmd() -> None:
    """中断されたストリームを回復する."""
    with acquire_lock():
        count = RecoverPipeline().recover_streams()
        click.echo(f"Recovered {count} streams.")


@cli.command()
@click.argument("video_id")
def download_one(video_id: str) -> None:
    """指定された動画をダウンロードする.

    VIDEO_ID: YouTube動画ID
    """
    with acquire_lock():
        success = DownloadPipeline().download_video(video_id)
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
    stream = db.get_stream(video_id)
    if stream is None or stream.local_path is None:
        click.echo(f"Video {video_id} not found or not downloaded", err=True)
        raise SystemExit(1)

    with acquire_lock():
        success = UploadPipeline().upload_video(video_id, stream.local_path)
        if success:
            click.echo(f"Uploaded {video_id}")
        else:
            click.echo(f"Failed to upload {video_id}", err=True)
            raise SystemExit(1)


@cli.command()
def status() -> None:
    """現在のステータスを表示する."""
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
        streams = db.get_streams_by_status(status_name)
        click.echo(f"  {status_name}: {len(streams)}")


if __name__ == "__main__":
    cli()
