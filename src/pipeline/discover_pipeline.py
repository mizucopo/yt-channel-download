"""動画検出パイプライン.

YouTube APIを使用して新しい動画を検出し、データベースに登録する。
"""

import logging
from collections.abc import Sequence
from datetime import datetime

from mizu_common import YouTubeClient

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.repository.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class DiscoverPipeline:
    """動画検出パイプライン."""

    def __init__(
        self,
        client: YouTubeClient,
        channel_ids: Sequence[str],
        repository: StreamRepository,
        is_first_run: bool = False,
        published_after: datetime | None = None,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            client: YouTube APIクライアント
            channel_ids: 検出対象のチャンネルIDリスト
            repository: ストリームリポジトリ
            is_first_run: 初回起動かどうか（Trueの場合、動画をCANCELEDで登録）
            published_after: この日時以降に公開された動画のみを検出
        """
        self._client = client
        self._channel_ids = channel_ids
        self._repository = repository
        self._is_first_run = is_first_run
        self._published_after = published_after

    def discover_all(self) -> int:
        """新しい動画を検出して登録する.

        Returns:
            新規登録された動画数
        """
        initial_status = (
            StreamStatus.CANCELED if self._is_first_run else StreamStatus.DISCOVERED
        )
        count = 0
        for channel_id in self._channel_ids:
            logger.info("Discovering videos for channel: %s", channel_id)
            videos = self._client.get_channel_videos(
                channel_id, published_after=self._published_after
            )

            for video in videos:
                existing = self._repository.get(video.video_id)
                if existing is not None:
                    continue

                stream = Stream(
                    video_id=video.video_id,
                    status=initial_status,
                    title=video.title,
                    published_at=video.published_at.isoformat(),
                )
                self._repository.insert(stream)
                logger.info(
                    "Discovered new video: %s - %s", video.video_id, video.title
                )
                count += 1

        return count
