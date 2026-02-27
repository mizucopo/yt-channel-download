"""Google Driveアップロードパイプライン.

mizu-common-pyのGoogleDriveProviderを使用してGoogle Driveへアップロードする。
"""

import logging
from pathlib import Path

from mizu_common.google_drive_provider import GoogleDriveProvider

from src.models.stream_status import StreamStatus
from src.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class UploadPipeline:
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
        self._max_retries = max_retries
        self._gdrive_provider = gdrive_provider
        self._gdrive_root_folder_id = gdrive_root_folder_id
        self._thumbnail_dir = thumbnail_dir
        self._repository = repository

    def _get_thumbnail_dir(self, video_id: str) -> Path:
        """サムネイル保存ディレクトリを取得する.

        Args:
            video_id: YouTube動画ID

        Returns:
            サムネイル保存先のディレクトリパス
        """
        return self._thumbnail_dir / video_id

    def upload_video(self, video_id: str, local_path: str) -> bool:
        """動画とサムネイルをGoogle Driveにアップロードする.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス

        Returns:
            アップロードが成功した場合はTrue
        """
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
            video_file = Path(local_path)
            if not video_file.exists():
                raise FileNotFoundError(f"Video file not found: {local_path}")

            logger.info("Uploading video: %s", video_id)
            video_gdrive_id = self._gdrive_provider.upload_file(
                file_path=str(video_file),
                parent_folder_id=self._gdrive_root_folder_id,
                file_name=video_file.name,
            )

            # サムネイルフォルダをアップロード
            thumb_dir = self._get_thumbnail_dir(video_id)
            if thumb_dir.exists():
                logger.info("Uploading thumbnails: %s", video_id)
                self._gdrive_provider.upload_directory(
                    directory_path=str(thumb_dir),
                    parent_folder_id=self._gdrive_root_folder_id,
                    folder_name=f"{video_id}_thumbnails",
                )

            # CAS更新: uploading -> uploaded
            self._repository.update_status(
                video_id,
                StreamStatus.UPLOADED,
                expected_old_status=StreamStatus.UPLOADING,
                gdrive_file_id=video_gdrive_id,
                gdrive_file_name=video_file.name,
            )
            logger.info("Upload completed: %s", video_id)
            return True

        except Exception as e:
            logger.exception("Upload error for %s", video_id)
            self._repository.update_status(
                video_id,
                StreamStatus.THUMBS_DONE,
                expected_old_status=StreamStatus.UPLOADING,
                error_message=str(e)[:500],
                increment_retry=True,
            )
            return False

    def upload_next(self) -> bool:
        """次の待機中の動画をアップロードする.

        Returns:
            アップロード対象があった場合はTrue
        """
        stream = self._repository.get_next_pending(
            StreamStatus.THUMBS_DONE, self._max_retries
        )
        if stream is None or stream.local_path is None:
            return False

        return self.upload_video(stream.video_id, stream.local_path)

    def upload_all(self) -> int:
        """すべての待機中の動画をアップロードする.

        Returns:
            アップロードに成功した動画数
        """
        count = 0
        while True:
            if not self.upload_next():
                break
            count += 1
        return count
