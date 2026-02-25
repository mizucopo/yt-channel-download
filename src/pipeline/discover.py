"""動画検出パイプライン.

YouTube APIを使用して新しいライブアーカイブを検出し、データベースに登録する。
"""

import logging
from collections.abc import Sequence

from src.models.stream import Stream
from src.youtube_client import YouTubeClient

logger = logging.getLogger(__name__)


class DiscoverPipeline:
    """動画検出パイプライン."""

    def __init__(
        self,
        client: YouTubeClient,
        channel_ids: Sequence[str],
        repository: "StreamRepository",
    ) -> None:
        """パイプラインを初期化する.

        Args:
            client: YouTube APIクライアント
            channel_ids: 検出対象のチャンネルIDリスト
            repository: ストリームリポジトリ
        """
        self._client = client
        self._channel_ids = channel_ids
        self._repository = repository

    def discover_all(self) -> int:
        """新しいライブアーカイブを検出して登録する.

        Returns:
            新規登録された動画数
        """
        count = 0
        for channel_id in self._channel_ids:
            logger.info("Discovering videos for channel: %s", channel_id)
            videos = self._client.get_live_archives(channel_id)

            for video in videos:
                existing = self._repository.get(video.video_id)
                if existing is not None:
                    continue

                stream = Stream(
                    video_id=video.video_id,
                    status="discovered",
                    title=video.title,
                    published_at=video.published_at.isoformat(),
                )
                self._repository.insert(stream)
                logger.info(
                    "Discovered new video: %s - %s", video.video_id, video.title
                )
                count += 1

        return count


from src.repository import StreamRepository  # noqa: E402
