"""DiscordNotifierのテスト."""

from unittest.mock import MagicMock, patch

from mizu_common import DiscordWebhookError

from src.notifications.discord_notifier import DiscordNotifier

MODULE_PATH = "src.notifications.discord_notifier.DiscordClient"


class TestNotifyUploadComplete:
    """notify_upload_completeのテスト."""

    def test_webhook_url未設定時は通知されないこと(self) -> None:
        """Webhook URLがNoneの場合、通知は送信されないこと。"""
        # Arrange
        notifier = DiscordNotifier(
            webhook_url=None,
            gdrive_folder_url="https://example.com",
        )

        # Act
        with patch(MODULE_PATH) as mock_client:
            notifier.notify_upload_complete(title="Test Video", video_id="abc123")

        # Assert
        mock_client.assert_not_called()

    def test正常時はEmbedが送信されること(self) -> None:
        """Webhook URLが設定されている場合、正しいEmbedが送信されること。"""
        # Arrange
        notifier = DiscordNotifier(
            webhook_url="https://discord.com/api/webhooks/xxx/yyy",
            gdrive_folder_url="https://drive.google.com/drive/folders/zzz",
        )

        # Act
        with patch(MODULE_PATH) as mock_client_class:
            mock_client = MagicMock()
            mock_client_class.return_value = mock_client
            notifier.notify_upload_complete(
                title="Test Video Title",
                video_id="abc123",
            )

        # Assert
        mock_client_class.assert_called_once_with(
            webhook_url="https://discord.com/api/webhooks/xxx/yyy"
        )
        mock_client.send_embed.assert_called_once()
        # Embedの内容を検証
        call_args = mock_client.send_embed.call_args
        embed = call_args.kwargs["embed"]
        assert embed.title == "アップロード完了"
        assert "Test Video Title" in embed.description
        assert "https://drive.google.com/drive/folders/zzz" in embed.description
        assert embed.color == 0x57F386

    def test_エラー時はログ出力のみで例外が発生しないこと(self) -> None:
        """Discord送信エラー時はログが出力され、例外が発生しないこと。"""
        # Arrange
        notifier = DiscordNotifier(
            webhook_url="https://discord.com/api/webhooks/xxx/yyy",
            gdrive_folder_url="https://drive.google.com/drive/folders/zzz",
        )

        # Act
        with patch(MODULE_PATH) as mock_client_class:
            mock_client = MagicMock()
            mock_client.send_embed.side_effect = DiscordWebhookError("Connection error")
            mock_client_class.return_value = mock_client

            # 例外が発生しないことを確認
            notifier.notify_upload_complete(title="Test Video", video_id="abc123")

        # Assert - 例外が発生せず正常に終了すること
        # （ログ出力の検証は統合テストで行う）
