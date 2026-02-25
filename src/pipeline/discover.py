"""動画検出パイプライン.

YouTube APIを使用して新しいライブアーカイブを検出し、データベースに登録する。
"""

import logging

from src import db
from src.config import settings
from src.yt_api import YouTubeClient

logger = logging.getLogger(__name__)


def discover_videos(client: YouTubeClient | None = None) -> int:
    """新しいライブアーカイブを検出して登録する.

    Args:
        client: YouTube APIクライアント（Noneの場合は新規作成）

    Returns:
        新規登録された動画数
    """
    if client is None:
        client = YouTubeClient(settings.youtube_api_key)

    count = 0
    for channel_id in settings.youtube_channel_ids:
        logger.info("Discovering videos for channel: %s", channel_id)
        videos = client.get_live_archives(channel_id)

        for video in videos:
            existing = db.get_stream(video.video_id)
            if existing is not None:
                continue

            stream = db.Stream(
                video_id=video.video_id,
                status="discovered",
                title=video.title,
                published_at=video.published_at.isoformat(),
            )
            db.insert_stream(stream)
            logger.info("Discovered new video: %s - %s", video.video_id, video.title)
            count += 1

    return count
