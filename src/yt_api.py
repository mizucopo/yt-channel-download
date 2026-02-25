"""YouTube Data API v3クライアントモジュール.

YouTubeライブアーカイブの検出と詳細取得を提供する。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, cast

import requests


@dataclass(frozen=True)
class VideoInfo:
    """動画情報を表すデータクラス."""

    video_id: str
    title: str
    published_at: datetime
    duration: str


class YouTubeClient:
    """YouTube Data API v3クライアント.

    YouTube APIを使用してライブアーカイブ情報を取得する。
    """

    BASE_URL = "https://www.googleapis.com/youtube/v3"

    def __init__(self, api_key: str) -> None:
        """クライアントを初期化する.

        Args:
            api_key: YouTube Data API キー
        """
        self.api_key = api_key

    def _make_request(
        self, endpoint: str, params: dict[str, str]
    ) -> dict[str, Any] | None:
        """APIリクエストを実行する.

        Args:
            endpoint: APIエンドポイント
            params: リクエストパラメータ

        Returns:
            レスポンスJSON（エラー時はNone）
        """
        params["key"] = self.api_key
        response = requests.get(
            f"{self.BASE_URL}/{endpoint}", params=params, timeout=30
        )

        if response.status_code != 200:
            return None

        return cast("dict[str, Any]", response.json())

    def get_live_archives(self, channel_id: str) -> list[VideoInfo]:
        """チャンネルのライブアーカイブ一覧を取得する.

        Args:
            channel_id: YouTubeチャンネルID

        Returns:
            ライブアーカイブのリスト
        """
        videos: list[VideoInfo] = []
        next_page_token: str | None = None

        while True:
            params: dict[str, str] = {
                "channelId": channel_id,
                "part": "id",
                "maxResults": "50",
                "type": "video",
                "eventType": "completed",
            }

            if next_page_token:
                params["pageToken"] = next_page_token

            data = self._make_request("search", params)
            if data is None:
                break

            video_ids = [item["id"]["videoId"] for item in data.get("items", [])]
            if video_ids:
                video_details = self._get_video_details_batch(video_ids)
                videos.extend(video_details)

            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        return videos

    def _get_video_details_batch(self, video_ids: list[str]) -> list[VideoInfo]:
        """複数の動画詳細を一括取得する.

        Args:
            video_ids: 動画IDのリスト

        Returns:
            動画情報のリスト
        """
        if not video_ids:
            return []

        params = {
            "part": "snippet,contentDetails",
            "id": ",".join(video_ids),
        }

        data = self._make_request("videos", params)
        if data is None:
            return []

        videos: list[VideoInfo] = []
        for item in data.get("items", []):
            video_id = item["id"]
            title = item["snippet"]["title"]
            published_at_str = item["snippet"]["publishedAt"]
            duration = item["contentDetails"]["duration"]

            # ISO 8601形式の日時をパース
            published_at = datetime.fromisoformat(
                published_at_str.replace("Z", "+00:00")
            )

            videos.append(
                VideoInfo(
                    video_id=video_id,
                    title=title,
                    published_at=published_at,
                    duration=duration,
                )
            )

        return videos

    def get_video_details(self, video_id: str) -> VideoInfo | None:
        """単一の動画詳細を取得する.

        Args:
            video_id: YouTube動画ID

        Returns:
            動画情報（存在しない場合はNone）
        """
        videos = self._get_video_details_batch([video_id])
        return videos[0] if videos else None
