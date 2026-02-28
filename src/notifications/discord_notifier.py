"""Discord通知モジュール.

mizu-common-pyのDiscordClientを使用してDiscordへ通知を送信する。
"""

import logging

from mizu_common import DiscordClient, DiscordEmbed, DiscordWebhookError

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord通知クライアント."""

    def __init__(self, webhook_url: str | None, gdrive_folder_url: str) -> None:
        """クライアントを初期化する.

        Args:
            webhook_url: Discord Webhook URL（Noneの場合は通知をスキップ）
            gdrive_folder_url: Google DriveフォルダのURL
        """
        self._webhook_url = webhook_url
        self._gdrive_folder_url = gdrive_folder_url

    def notify_upload_complete(self, title: str | None, video_id: str) -> None:
        """アップロード完了通知を送信する.

        通知失敗時はログ出力のみで、例外は発生させない。

        Args:
            title: YouTube動画タイトル
            video_id: YouTube動画ID
        """
        if not self._webhook_url:
            return

        display_title = title or video_id
        embed = DiscordEmbed(
            title="アップロード完了",
            description=f"**{display_title}**\n\n[Google Driveで開く]"
            f"({self._gdrive_folder_url})",
            color=0x57F386,  # 緑色
        )

        try:
            client = DiscordClient(webhook_url=self._webhook_url)
            client.send_embed(embed=embed)
            logger.info("Discord notification sent: %s", video_id)
        except DiscordWebhookError as e:
            logger.warning("Discord notification failed for %s: %s", video_id, e)
