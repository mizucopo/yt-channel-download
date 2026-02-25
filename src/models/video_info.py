"""動画情報を表すデータモデル."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VideoInfo:
    """動画情報を表すデータクラス."""

    video_id: str
    title: str
    published_at: datetime
    duration: str
