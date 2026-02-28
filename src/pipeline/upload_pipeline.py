"""Google Driveアップロードパイプライン.

mizu-common-pyのGoogleDriveProviderを使用してGoogle Driveへアップロードする。
"""

import logging
import re
from pathlib import Path

from mizu_common.google_drive_provider import GoogleDriveProvider

from src.constants.stream_status import StreamStatus
from src.repository.stream_repository import StreamRepository

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

    @staticmethod
    def _sanitize_filename(name: str) -> str:
        """ファイル名に使えない文字を置換する.

        Args:
            name: 元のファイル名

        Returns:
            サニタイズされたファイル名
        """
        # 禁止文字: \ / : * ? " < > | と制御文字
        sanitized = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", name)
        # 先頭・末尾のドットとスペースを削除
        sanitized = sanitized.strip(". ")
        return sanitized if sanitized else "untitled"

    def _generate_gdrive_folder_name(self, title: str | None, video_id: str) -> str:
        """Google Drive用のフォルダ名を生成する.

        Args:
            title: YouTube動画タイトル
            video_id: YouTube動画ID

        Returns:
            Google Drive用のフォルダ名
        """
        if title is None:
            return video_id
        return self._sanitize_filename(title)

    def _generate_gdrive_filename(self, title: str | None, original_path: Path) -> str:
        """Google Drive用のファイル名を生成する.

        Args:
            title: YouTube動画タイトル
            original_path: 元のファイルパス

        Returns:
            Google Drive用のファイル名
        """
        if title is None:
            return original_path.name
        sanitized = self._sanitize_filename(title)
        return f"{sanitized}{original_path.suffix}"

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

            folder_name = self._generate_gdrive_folder_name(title, video_id)
            gdrive_filename = self._generate_gdrive_filename(title, video_file)

            logger.info("Uploading video: %s", video_id)
            self._gdrive_provider.upload(
                source_path=str(video_file),
                destination_filename=f"{folder_name}/{gdrive_filename}",
            )

            # サムネイルファイルを個別にアップロード
            thumb_dir = self._get_thumbnail_dir(video_id)
            if thumb_dir.exists():
                logger.info("Uploading thumbnails: %s", video_id)
                for thumb_file in sorted(thumb_dir.iterdir()):
                    if thumb_file.is_file():
                        self._gdrive_provider.upload(
                            source_path=str(thumb_file),
                            destination_filename=f"{folder_name}/thumbnails/{thumb_file.name}",
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

        return self.upload_video(
            video_id=stream.video_id,
            local_path=stream.local_path,
            title=stream.title,
        )

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
