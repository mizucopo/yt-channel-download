"""ストリームステータスの定義."""

from enum import Enum


class StreamStatus(str, Enum):
    """ストリームのステータス."""

    DISCOVERED = "discovered"
    DOWNLOADING = "downloading"
    DOWNLOADED = "downloaded"
    THUMBS_DONE = "thumbs_done"
    UPLOADING = "uploading"
    UPLOADED = "uploaded"
    CLEANED = "cleaned"
    CANCELED = "canceled"
