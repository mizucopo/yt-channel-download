"""Google Driveアップロードパイプライン.

mizu-common-pyのGoogleDriveProviderを使用してGoogle Driveへアップロードする。
"""

import logging
from pathlib import Path

from mizu_common.google_drive_provider import GoogleDriveProvider

from src import db
from src.config import settings
from src.utils.paths import get_thumbnail_dir

logger = logging.getLogger(__name__)


class UploadPipeline:
    """Google Driveアップロードパイプライン."""

    def __init__(self, max_retries: int | None = None) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数（Noneの場合は設定値を使用）
        """
        self._max_retries = (
            max_retries if max_retries is not None else settings.max_retries
        )

    def upload_video(self, video_id: str, local_path: str) -> bool:
        """動画とサムネイルをGoogle Driveにアップロードする.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス

        Returns:
            アップロードが成功した場合はTrue
        """
        # CAS更新: thumbs_done -> uploading
        updated = db.update_status(
            video_id,
            "uploading",
            expected_old_status="thumbs_done",
        )
        if not updated:
            logger.warning("Failed to acquire lock for upload: %s", video_id)
            return False

        try:
            provider = GoogleDriveProvider(
                credentials_path=settings.gdrive_credentials_path
            )

            # 動画ファイルをアップロード
            video_file = Path(local_path)
            if not video_file.exists():
                raise FileNotFoundError(f"Video file not found: {local_path}")

            logger.info("Uploading video: %s", video_id)
            video_gdrive_id = provider.upload_file(
                file_path=str(video_file),
                parent_folder_id=settings.gdrive_root_folder_id,
                file_name=video_file.name,
            )

            # サムネイルフォルダをアップロード
            thumb_dir = get_thumbnail_dir(video_id)
            if thumb_dir.exists():
                logger.info("Uploading thumbnails: %s", video_id)
                provider.upload_directory(
                    directory_path=str(thumb_dir),
                    parent_folder_id=settings.gdrive_root_folder_id,
                    folder_name=f"{video_id}_thumbnails",
                )

            # CAS更新: uploading -> uploaded
            db.update_status(
                video_id,
                "uploaded",
                expected_old_status="uploading",
                gdrive_file_id=video_gdrive_id,
                gdrive_file_name=video_file.name,
            )
            logger.info("Upload completed: %s", video_id)
            return True

        except Exception as e:
            logger.exception("Upload error for %s", video_id)
            db.update_status(
                video_id,
                "thumbs_done",
                expected_old_status="uploading",
                error_message=str(e)[:500],
                increment_retry=True,
            )
            return False

    def upload_next(self) -> bool:
        """次の待機中の動画をアップロードする.

        Returns:
            アップロード対象があった場合はTrue
        """
        stream = db.get_next_pending("thumbs_done", self._max_retries)
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
