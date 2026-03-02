"""パイプライン構築・実行オーケストレーター."""

import click

from src.client_factory import ClientFactory
from src.models.scan_mode import ScanMode
from src.pipeline.cleanup_pipeline import CleanupPipeline
from src.pipeline.discover_pipeline import DiscoverPipeline
from src.pipeline.download_pipeline import DownloadPipeline
from src.pipeline.recover_pipeline import RecoverPipeline
from src.pipeline.single_video_orchestrator import SingleVideoOrchestrator
from src.pipeline.thumbs_pipeline import ThumbsPipeline
from src.pipeline.upload_pipeline import UploadPipeline
from src.repository.stream_repository import StreamRepository
from src.settings import Settings
from src.utils.path_manager import PathManager


class PipelineOrchestrator:
    """パイプラインの構築と実行を管理するオーケストレーター."""

    def __init__(
        self,
        settings: Settings,
        path_manager: PathManager,
        client_factory: ClientFactory,
    ) -> None:
        """オーケストレーターを初期化する.

        Args:
            settings: アプリケーション設定
            path_manager: パスマネージャ
            client_factory: クライアントファクトリ
        """
        self._settings = settings
        self._path_manager = path_manager
        self._client_factory = client_factory

    def run(self, repository: StreamRepository, scan_mode: ScanMode) -> None:
        """全パイプラインを実行する.

        復旧→検出→ダウンロード→サムネイル抽出→アップロード→クリーンアップの
        全ステップを順番に実行する。

        Args:
            repository: ストリームリポジトリ
            scan_mode: スキャンモード（フルスキャンまたは期間指定）
        """
        repository.reset_all_retry_counts()
        is_first_run = repository.is_empty()
        youtube_client = self._client_factory.get_youtube_client()
        gdrive_provider = self._client_factory.get_gdrive_provider(
            folder_id=self._settings.gdrive_root_folder_id
        )

        click.echo("Recovering streams...")
        recovered = RecoverPipeline(
            max_retries=self._settings.max_retries,
            thumbnail_dir=self._path_manager.thumbnail_dir,
            repository=repository,
        ).run()
        click.echo(f"  Recovered: {recovered} streams")

        click.echo("Discovering videos...")
        discovered = DiscoverPipeline(
            client=youtube_client,
            channel_ids=self._settings.youtube_channel_ids,
            repository=repository,
            is_first_run=is_first_run,
            published_after=scan_mode.get_published_after(),
        ).discover_all()
        if is_first_run and discovered > 0:
            click.echo(
                f"  First run: {discovered} existing videos registered as canceled"
            )
        else:
            click.echo(f"  Discovered: {discovered} new videos")

        # パイプラインを初期化
        download_pipeline = DownloadPipeline(
            max_retries=self._settings.max_retries,
            download_dir=self._path_manager.download_dir,
            repository=repository,
        )
        thumbs_pipeline = ThumbsPipeline(
            max_retries=self._settings.max_retries,
            thumbnail_interval=self._settings.thumbnail_interval,
            thumbnail_quality=self._settings.thumbnail_quality,
            path_manager=self._path_manager,
            repository=repository,
        )
        upload_pipeline = UploadPipeline(
            max_retries=self._settings.max_retries,
            gdrive_provider=gdrive_provider,
            gdrive_root_folder_id=self._settings.gdrive_root_folder_id,
            path_manager=self._path_manager,
            repository=repository,
        )
        cleanup_pipeline = CleanupPipeline(
            max_retries=self._settings.max_retries,
            download_dir=self._path_manager.download_dir,
            path_manager=self._path_manager,
            repository=repository,
        )

        # 1動画単位でパイプライン全体を実行
        click.echo("Processing videos...")
        orchestrator = SingleVideoOrchestrator(
            repository=repository,
            download_pipeline=download_pipeline,
            thumbs_pipeline=thumbs_pipeline,
            upload_pipeline=upload_pipeline,
            cleanup_pipeline=cleanup_pipeline,
            max_retries=self._settings.max_retries,
            discord_notifier=self._client_factory.get_discord_notifier(),
        )
        processed = orchestrator.process_all_videos()
        click.echo(f"  Processed: {processed} videos")

        click.echo("Pipeline completed.")
