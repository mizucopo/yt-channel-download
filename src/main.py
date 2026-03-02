"""CLI エントリポイント.

Clickベースのコマンドラインインターフェースを提供する。
"""

import logging
from pathlib import Path

import click
from mizu_common import LoggingConfigurator

from src.client_factory import ClientFactory
from src.commands.auth_command import AuthCommand
from src.commands.redownload_command import RedownloadCommand
from src.commands.status_command import StatusCommand
from src.lock_context import LockContext
from src.models.scan_mode import ScanMode
from src.pipeline.pipeline_orchestrator import PipelineOrchestrator
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

        # コンポジション
        self._client_factory = ClientFactory(self._settings, self._path_manager)
        self._lock_context = LockContext(self._settings, self._path_manager)
        self._pipeline_orchestrator = PipelineOrchestrator(
            self._settings, self._path_manager, self._client_factory
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

    def initialize(self) -> None:
        """アプリケーションを初期化する."""
        level = logging.DEBUG if self._verbose else logging.INFO
        LoggingConfigurator(level=level)

        self._path_manager.ensure_directories()

        repository = self.get_repository()
        repository.init_db()

    def run(self, scan_mode: ScanMode) -> None:
        """全パイプラインを実行する.

        復旧→検出→ダウンロード→サムネイル抽出→アップロード→クリーンアップの
        全ステップを順番に実行する。

        Args:
            scan_mode: スキャンモード（フルスキャンまたは期間指定）
        """
        with self._lock_context.acquire():
            click.echo("Starting full pipeline...")
            repository = self.get_repository()
            self._pipeline_orchestrator.run(repository, scan_mode)

    def status(self) -> None:
        """現在のステータスを表示する."""
        command = StatusCommand(self.get_repository())
        command.execute()

    def unlock(self) -> None:
        """ロックファイルを削除する."""
        self._lock_context.release()

    def auth_cmd(self) -> None:
        """Google OAuth認証を実行し、リフレッシュトークンを取得する."""
        command = AuthCommand(self._settings)
        command.execute()

    def redownload(self, video_id: str) -> None:
        """指定された動画を再ダウンロード対象にする."""
        command = RedownloadCommand(self.get_repository())
        command.execute(video_id)


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
@click.option("-f", "--full", is_flag=True, help="フルスキャン（全期間）")
@click.option("-d", "--days", type=int, help="過去N日分をスキャン")
@click.pass_context
def run(ctx: click.Context, full: bool, days: int | None) -> None:
    """全パイプラインを実行する.

    -f/--full または -d/--days のいずれかを指定する必要がある。
    """
    # オプション未指定時はヘルプを表示
    if not full and days is None:
        click.echo(ctx.get_help())
        ctx.exit()
        return

    # 相互排他・妥当性チェック
    if full and days is not None:
        raise click.UsageError("--full と --days は同時に指定できません。")
    if days is not None and days <= 0:
        raise click.UsageError("--days には1以上の整数を指定してください。")

    # 初回起動時の -d オプションチェック（initialize() より前に実行）
    app: Main = ctx.obj
    if days is not None and not app.path_manager.database_path.exists():
        raise click.UsageError(
            "初回起動時は --full を指定してください。"
            "-d オプションは2回目以降に使用できます。"
        )

    app.initialize()
    scan_mode = ScanMode(days=None if full else days)
    app.run(scan_mode)


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
