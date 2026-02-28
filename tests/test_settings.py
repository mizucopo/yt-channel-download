"""設定モジュールのテスト."""

from typing import Any
from unittest.mock import patch

import pytest

from src.settings import Settings


@pytest.mark.parametrize(
    "env_values,expected_error",
    [
        pytest.param(
            {
                "YOUTUBE_CHANNEL_IDS": "",
                "GOOGLE_OAUTH_CLIENT_ID": "",
                "GOOGLE_REFRESH_TOKEN": "",
                "GDRIVE_ROOT_FOLDER_ID": "",
            },
            "YOUTUBE_CHANNEL_IDS",
            id="channel_ids_missing",
        ),
        pytest.param(
            {
                "YOUTUBE_CHANNEL_IDS": "channel1",
                "GOOGLE_OAUTH_CLIENT_ID": "",
                "GOOGLE_REFRESH_TOKEN": "",
                "GDRIVE_ROOT_FOLDER_ID": "",
            },
            "GOOGLE_OAUTH_CLIENT_ID",
            id="oauth_client_id_missing",
        ),
        pytest.param(
            {
                "YOUTUBE_CHANNEL_IDS": "channel1",
                "GOOGLE_OAUTH_CLIENT_ID": "client_id_123",
                "GOOGLE_REFRESH_TOKEN": "",
                "GDRIVE_ROOT_FOLDER_ID": "",
            },
            "GOOGLE_REFRESH_TOKEN",
            id="refresh_token_missing",
        ),
        pytest.param(
            {
                "YOUTUBE_CHANNEL_IDS": "channel1",
                "GOOGLE_OAUTH_CLIENT_ID": "client_id_123",
                "GOOGLE_REFRESH_TOKEN": "refresh_token_123",
                "GDRIVE_ROOT_FOLDER_ID": "",
            },
            "GDRIVE_ROOT_FOLDER_ID",
            id="gdrive_root_folder_id_missing",
        ),
    ],
)
def test_from_env_raises_error_when_required_field_missing(
    env_values: dict[str, str],
    expected_error: str,
) -> None:
    """必須フィールドが未設定の場合、ValueErrorが発生すること.

    Arrange:
        config関数をモックして指定された値を返すようにする。

    Act:
        from_env()を呼び出す。

    Assert:
        期待されるエラーメッセージを含むValueErrorが発生すること。
    """

    # Arrange
    def mock_config(key: str, default: str = "", **kwargs: Any) -> str:  # noqa: ARG001
        return env_values.get(key, default)

    with (
        patch("src.settings.config", side_effect=mock_config),
        pytest.raises(ValueError, match=expected_error),
    ):
        # Act
        Settings.from_env()


def test_from_env_succeeds_when_required_fields_set() -> None:
    """必須フィールドが設定されている場合、正常に作成されること.

    Arrange:
        config関数をモックして必要な値を返すようにする。

    Act:
        from_env()を呼び出す。

    Assert:
        設定オブジェクトが正常に作成されること。
    """
    # Arrange
    env_values = {
        "YOUTUBE_CHANNEL_IDS": "channel1,channel2",
        "GOOGLE_OAUTH_CLIENT_ID": "client_id_123",
        "GOOGLE_REFRESH_TOKEN": "refresh_token_123",
        "GDRIVE_ROOT_FOLDER_ID": "folder123",
    }

    def mock_config(key: str, default: str = "", **kwargs: Any) -> str:  # noqa: ARG001
        return env_values.get(key, default)

    with patch("src.settings.config", side_effect=mock_config):
        # Act
        settings = Settings.from_env()

    # Assert
    assert settings.youtube_channel_ids == ["channel1", "channel2"]
    assert settings.google_oauth_client_id == "client_id_123"
    assert settings.google_refresh_token == "refresh_token_123"
    assert settings.gdrive_root_folder_id == "folder123"
