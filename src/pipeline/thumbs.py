"""サムネイル抽出パイプライン.

ffmpegを使用して動画からスクリーンショットを抽出する。
"""

import logging
import subprocess
from pathlib import Path

from src.utils.paths import get_thumbnail_dir

logger = logging.getLogger(__name__)


class ThumbsPipeline:
    """サムネイル抽出パイプライン."""

    def __init__(
        self,
        max_retries: int,
        thumbnail_interval: int,
        thumbnail_dir: Path,
        repository: "StreamRepository",
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            thumbnail_interval: サムネイル抽出間隔（秒）
            thumbnail_dir: サムネイル保存ディレクトリ
            repository: ストリームリポジトリ
        """
        self._max_retries = max_retries
        self._thumbnail_interval = thumbnail_interval
        self._thumbnail_dir = thumbnail_dir
        self._repository = repository

    def extract_thumbnails(self, video_id: str, local_path: str) -> bool:
        """動画からサムネイルを抽出する.

        Args:
            video_id: YouTube動画ID
            local_path: 動画ファイルのパス

        Returns:
            抽出が成功した場合はTrue
        """
        # CAS更新: downloaded -> thumbs_done
        updated = self._repository.update_status(
            video_id,
            "thumbs_done",
            expected_old_status="downloaded",
        )
        if not updated:
            logger.warning(
                "Failed to acquire lock for thumbnail extraction: %s", video_id
            )
            return False

        try:
            # サムネイルディレクトリを作成
            thumb_dir = get_thumbnail_dir(video_id, self._thumbnail_dir)
            thumb_dir.mkdir(parents=True, exist_ok=True)

            logger.info(
                "Extracting thumbnails from %s at %d second intervals",
                video_id,
                self._thumbnail_interval,
            )

            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    local_path,
                    "-vf",
                    f"fps=1/{self._thumbnail_interval}",
                    "-q:v",
                    "2",
                    str(thumb_dir / "thumb_%04d.jpg"),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                logger.error(
                    "Thumbnail extraction failed for %s: %s", video_id, result.stderr
                )
                self._repository.update_status(
                    video_id,
                    "downloaded",
                    expected_old_status="thumbs_done",
                    error_message=(
                        result.stderr[:500] if result.stderr else "Unknown error"
                    ),
                    increment_retry=True,
                )
                return False

            logger.info("Thumbnail extraction completed: %s", video_id)
            return True

        except Exception as e:
            logger.exception("Thumbnail extraction error for %s", video_id)
            self._repository.update_status(
                video_id,
                "downloaded",
                expected_old_status="thumbs_done",
                error_message=str(e)[:500],
                increment_retry=True,
            )
            return False

    def extract_next(self) -> bool:
        """次の待機中の動画からサムネイルを抽出する.

        Returns:
            抽出対象があった場合はTrue
        """
        stream = self._repository.get_next_pending("downloaded", self._max_retries)
        if stream is None or stream.local_path is None:
            return False

        return self.extract_thumbnails(stream.video_id, stream.local_path)

    def extract_all(self) -> int:
        """すべての待機中の動画からサムネイルを抽出する.

        Returns:
            抽出に成功した動画数
        """
        count = 0
        while True:
            if not self.extract_next():
                break
            count += 1
        return count


from src.repository import StreamRepository  # noqa: E402
