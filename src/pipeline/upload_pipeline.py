"""Google Driveアップロードパイプライン.

mizu-common-pyのGoogleDriveProviderを使用してGoogle Driveへアップロードする。
"""

import logging
from pathlib import Path

from mizu_common.google_drive_provider import GoogleDriveProvider

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.base_pipeline import BasePipeline
from src.repository.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class UploadPipeline(BasePipeline):
    """Google Driveアップロードパイプライン."""

    def __init__(
        self,
        max_retries: int,
        gdrive_provider: GoogleDriveProvider,
        gdrive_root_folder_id: str,
        thumbnail_dir: Path,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            gdrive_provider: Google Driveプロバイダー
            gdrive_root_folder_id: Google DriveルートフォルダID
            thumbnail_dir: サムネイルディレクトリ
            repository: ストリームリポジトリ
        """
        super().__init__(max_retries, repository)
        self._gdrive_provider = gdrive_provider
        self._gdrive_root_folder_id = gdrive_root_folder_id
        self._thumbnail_dir = thumbnail_dir

    def _get_pending_status(self) -> StreamStatus:
        """処理待ちステータスを取得する."""
        return StreamStatus.THUMBS_DONE

    def _get_thumbnail_dir(self, video_id: str) -> Path:
        """サムネイル保存ディレクトリを取得する.

        Args:
            video_id: YouTube動画ID

        Returns:
            サムネイル保存先のディレクトリパス
        """
        return self._thumbnail_dir / video_id

    def _process_single(self, video_id: str, stream: Stream) -> bool:
        """単一のストリームを処理する.

        Args:
            video_id: YouTube動画ID
            stream: ストリーム情報

        Returns:
            処理が成功した場合はTrue
        """
        if stream.local_path is None:
            return False

        # CAS更新: thumbs_done -> uploading
        updated = self._repository.update_status(
            video_id,
            StreamStatus.UPLOADING,
            expected_old_status=StreamStatus.THUMBS_DONE,
        )
        if not updated:
            logger.warning("Failed to acquire lock for upload: %s", video_id)
            return False

        try:
            # 動画ファイルをアップロード
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
            thumb_dir = self._get_thumbnail_dir(video_id)
            if thumb_dir.exists():
                logger.info("Uploading thumbnails: %s", video_id)
                for thumb_file in sorted(thumb_dir.iterdir()):
                    if thumb_file.is_file():
                        self._gdrive_provider.upload(
                            source_path=str(thumb_file),
                            destination_filename=f"{folder_name}/{thumb_file.name}",
                        )

            # CAS更新: uploading -> uploaded
            self._repository.update_status(
                video_id,
                StreamStatus.UPLOADED,
                expected_old_status=StreamStatus.UPLOADING,
                gdrive_file_id="",  # 新APIではファイルIDを返さない
                gdrive_file_name=gdrive_filename,
            )
            logger.info("Upload completed: %s", video_id)

            return True

        except Exception as e:
            logger.exception("Upload error for %s", video_id)
            self._repository.update_status(
                video_id,
                StreamStatus.THUMBS_DONE,
                expected_old_status=StreamStatus.UPLOADING,
                error_message=self.truncate_error(str(e)),
                increment_retry=True,
            )
            return False

    def upload_video(
        self, video_id: str, local_path: str, title: str | None = None
    ) -> bool:
        """動画とサムネイルをGoogle Driveにアップロードする.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス
            title: YouTube動画タイトル（ファイル名に使用）

        Returns:
            アップロードが成功した場合はTrue
        """
        stream = self._repository.get(video_id)
        if stream is None:
            return False
        # local_pathとtitleを一時的に上書きするため、新しいStreamを作成
        from dataclasses import replace

        stream_with_overrides = replace(stream, local_path=local_path, title=title)
        return self._process_single(video_id, stream_with_overrides)

    def upload_next(self) -> bool:
        """次の待機中の動画をアップロードする.

        Returns:
            アップロード対象があった場合はTrue
        """
        return self.process_next()

    def upload_all(self) -> int:
        """すべての待機中の動画をアップロードする.

        Returns:
            アップロードに成功した動画数
        """
        return self.process_all()
