"""動画検出パイプライン.

YouTube APIを使用して新しいライブアーカイブを検出し、データベースに登録する。
"""

import logging

from src import db
from src.config import settings
from src.models.stream import Stream
from src.youtube_client import YouTubeClient

logger = logging.getLogger(__name__)


class DiscoverPipeline:
    """動画検出パイプライン."""

    def __init__(self, client: YouTubeClient | None = None) -> None:
        """パイプラインを初期化する.

        Args:
            client: YouTube APIクライアント（Noneの場合は新規作成）
        """
        self._client = client or YouTubeClient(settings.youtube_api_key)

    def discover_videos(self) -> int:
        """新しいライブアーカイブを検出して登録する.

        Returns:
            新規登録された動画数
        """
        count = 0
        for channel_id in settings.youtube_channel_ids:
            logger.info("Discovering videos for channel: %s", channel_id)
            videos = self._client.get_live_archives(channel_id)

            for video in videos:
                existing = db.get_stream(video.video_id)
                if existing is not None:
                    continue

                stream = Stream(
                    video_id=video.video_id,
                    status="discovered",
                    title=video.title,
                    published_at=video.published_at.isoformat(),
                )
                db.insert_stream(stream)
                logger.info(
                    "Discovered new video: %s - %s", video.video_id, video.title
                )
                count += 1

        return count
