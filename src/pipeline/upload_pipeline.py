"""Google Driveアップロードパイプライン.

mizu-common-pyのGoogleDriveProviderを使用してGoogle Driveへアップロードする。
"""

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from mizu_common.google_drive_provider import GoogleDriveProvider

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.base_pipeline import BasePipeline
from src.repository.stream_repository import StreamRepository
from src.utils.path_manager import PathManager

logger = logging.getLogger(__name__)


class UploadPipeline(BasePipeline):
    """Google Driveアップロードパイプライン."""

    def __init__(
        self,
        max_retries: int,
        upload_parallel_workers: int,
        gdrive_provider: GoogleDriveProvider,
        gdrive_root_folder_id: str,
        path_manager: PathManager,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            upload_parallel_workers: サムネイル並列アップロード数
            gdrive_provider: Google Driveプロバイダー
            gdrive_root_folder_id: Google DriveルートフォルダID
            path_manager: パスマネージャ
            repository: ストリームリポジトリ
        """
        super().__init__(max_retries, repository)
        self._upload_parallel_workers = upload_parallel_workers
        self._gdrive_provider = gdrive_provider
        self._gdrive_root_folder_id = gdrive_root_folder_id
        self._path_manager = path_manager
        self._current_gdrive_filename: str | None = None

    def _get_pending_status(self) -> StreamStatus:
        """処理待ちステータスを取得する."""
        return StreamStatus.THUMBS_DONE

    def _get_processing_status(self) -> StreamStatus:
        """処理中ステータスを取得する."""
        return StreamStatus.UPLOADING

    def _get_completed_status(self) -> StreamStatus:
        """完了ステータスを取得する."""
        return StreamStatus.UPLOADED

    def _execute_process(self, video_id: str, stream: Stream) -> bool:
        """アップロード処理を実行する.

        Args:
            video_id: YouTube動画ID
            stream: ストリーム情報

        Returns:
            処理が成功した場合はTrue
        """
        if stream.local_path is None:
            return False

        # 動画ファイルの存在確認
        video_file = Path(stream.local_path)
        if not self._validate_file_exists(video_file, video_id):
            return False

        folder_name = GoogleDriveProvider.sanitize_name(stream.title or video_id)
        gdrive_filename = (
            f"{GoogleDriveProvider.sanitize_name(stream.title)}{video_file.suffix}"
            if stream.title
            else video_file.name
        )

        logger.info("Uploading video: %s", video_id)
        self._gdrive_provider.upload(
            source_path=str(video_file),
            destination_filename=gdrive_filename,
        )

        # サムネイルファイルを個別にアップロード
        thumb_dir = self._path_manager.get_thumbnail_dir(video_id)
        if thumb_dir.exists():
            logger.info("Uploading thumbnails: %s", video_id)
            thumb_files = [f for f in sorted(thumb_dir.iterdir()) if f.is_file()]
            self._upload_thumbnails_parallel(thumb_files, folder_name)

        self._current_gdrive_filename = gdrive_filename
        logger.info("Upload completed: %s", video_id)
        return True

    def _update_completed_status(
        self, video_id: str, processing_status: StreamStatus
    ) -> None:
        """処理完了時のステータス更新（gdrive_file_nameも設定）."""
        self._repository.update_status(
            video_id,
            self._get_completed_status(),
            expected_old_status=processing_status,
            gdrive_file_id="",  # 新APIではファイルIDを返さない
            gdrive_file_name=self._current_gdrive_filename,
        )

    def _upload_thumbnails_parallel(
        self, thumb_files: list[Path], folder_name: str
    ) -> None:
        """サムネイルを並列アップロードする.

        Args:
            thumb_files: アップロード対象のサムネイルファイルリスト
            folder_name: Google Drive上のフォルダ名

        Raises:
            Exception: アップロードに失敗した場合
        """
        if not thumb_files:
            return

        executor = ThreadPoolExecutor(max_workers=self._upload_parallel_workers)
        futures = {
            executor.submit(
                self._gdrive_provider.upload,
                str(thumb_file),
                f"{folder_name}/{thumb_file.name}",
            ): thumb_file
            for thumb_file in thumb_files
        }
        try:
            for future in as_completed(futures):
                thumb_file = futures[future]
                try:
                    future.result()
                    logger.debug("Uploaded: %s", thumb_file.name)
                except Exception:
                    logger.exception("Failed to upload: %s", thumb_file.name)
                    # 未開始のタスクをキャンセル
                    for f in futures:
                        f.cancel()
                    raise
        finally:
            # 実行中のタスクは待機せず、未開始のタスクはキャンセル
            executor.shutdown(wait=False, cancel_futures=True)

    def upload_next(self) -> bool:
        """次の待機中の動画をアップロードする.

        Returns:
            アップロード対象があった場合はTrue
        """
        return self.process_next()
