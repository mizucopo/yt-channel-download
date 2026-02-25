"""ストリーム情報を表すデータモデル."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Stream:
    """ストリーム情報を表すデータクラス."""

    video_id: str
    status: str
    title: str | None = None
    published_at: str | None = None
    local_path: str | None = None
    gdrive_file_id: str | None = None
    gdrive_file_name: str | None = None
    error_message: str | None = None
    retry_count: int = 0
    created_at: str | None = None
    updated_at: str | None = None
