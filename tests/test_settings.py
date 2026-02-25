"""設定モジュールのテスト."""

import os

import pytest

from src.settings import Settings


def test_from_env_raises_error_when_api_key_missing() -> None:
    """YOUTUBE_API_KEYが未設定の場合、ValueErrorが発生すること.

    Arrange:
        YOUTUBE_API_KEYを未設定にする。

    Act:
        from_env()を呼び出す。

    Assert:
        ValueErrorが発生すること。
    """
    # Arrange
    os.environ.pop("YOUTUBE_API_KEY", None)

    # Act & Assert
    with pytest.raises(ValueError, match="YOUTUBE_API_KEY"):
        Settings.from_env()


def test_from_env_raises_error_when_channel_ids_missing() -> None:
    """YOUTUBE_CHANNEL_IDSが未設定の場合、ValueErrorが発生すること.

    Arrange:
        YOUTUBE_CHANNEL_IDSを未設定にする。

    Act:
        from_env()を呼び出す。

    Assert:
        ValueErrorが発生すること。
    """
    # Arrange
    os.environ["YOUTUBE_API_KEY"] = "test_api_key"
    os.environ.pop("YOUTUBE_CHANNEL_IDS", None)

    try:
        # Act & Assert
        with pytest.raises(ValueError, match="YOUTUBE_CHANNEL_IDS"):
            Settings.from_env()
    finally:
        os.environ.pop("YOUTUBE_API_KEY", None)


def test_from_env_raises_error_when_gdrive_oauth_client_id_missing() -> None:
    """GDRIVE_OAUTH_CLIENT_IDが未設定の場合、ValueErrorが発生すること.

    Arrange:
        GDRIVE_OAUTH_CLIENT_IDを未設定にする。

    Act:
        from_env()を呼び出す。

    Assert:
        ValueErrorが発生すること。
    """
    # Arrange
    os.environ["YOUTUBE_API_KEY"] = "test_api_key"
    os.environ["YOUTUBE_CHANNEL_IDS"] = "channel1"
    os.environ.pop("GDRIVE_OAUTH_CLIENT_ID", None)

    try:
        # Act & Assert
        with pytest.raises(ValueError, match="GDRIVE_OAUTH_CLIENT_ID"):
            Settings.from_env()
    finally:
        os.environ.pop("YOUTUBE_API_KEY", None)
        os.environ.pop("YOUTUBE_CHANNEL_IDS", None)


def test_from_env_raises_error_when_gdrive_refresh_token_missing() -> None:
    """GDRIVE_REFRESH_TOKENが未設定の場合、ValueErrorが発生すること.

    Arrange:
        GDRIVE_REFRESH_TOKENを未設定にする。

    Act:
        from_env()を呼び出す。

    Assert:
        ValueErrorが発生すること。
    """
    # Arrange
    os.environ["YOUTUBE_API_KEY"] = "test_api_key"
    os.environ["YOUTUBE_CHANNEL_IDS"] = "channel1"
    os.environ["GDRIVE_OAUTH_CLIENT_ID"] = "client_id_123"
    os.environ.pop("GDRIVE_REFRESH_TOKEN", None)

    try:
        # Act & Assert
        with pytest.raises(ValueError, match="GDRIVE_REFRESH_TOKEN"):
            Settings.from_env()
    finally:
        os.environ.pop("YOUTUBE_API_KEY", None)
        os.environ.pop("YOUTUBE_CHANNEL_IDS", None)
        os.environ.pop("GDRIVE_OAUTH_CLIENT_ID", None)


def test_from_env_raises_error_when_gdrive_root_folder_id_missing() -> None:
    """GDRIVE_ROOT_FOLDER_IDが未設定の場合、ValueErrorが発生すること.

    Arrange:
        GDRIVE_ROOT_FOLDER_IDを未設定にする。

    Act:
        from_env()を呼び出す。

    Assert:
        ValueErrorが発生すること。
    """
    # Arrange
    os.environ["YOUTUBE_API_KEY"] = "test_api_key"
    os.environ["YOUTUBE_CHANNEL_IDS"] = "channel1"
    os.environ["GDRIVE_OAUTH_CLIENT_ID"] = "client_id_123"
    os.environ["GDRIVE_REFRESH_TOKEN"] = "refresh_token_123"
    os.environ.pop("GDRIVE_ROOT_FOLDER_ID", None)

    try:
        # Act & Assert
        with pytest.raises(ValueError, match="GDRIVE_ROOT_FOLDER_ID"):
            Settings.from_env()
    finally:
        os.environ.pop("YOUTUBE_API_KEY", None)
        os.environ.pop("YOUTUBE_CHANNEL_IDS", None)
        os.environ.pop("GDRIVE_OAUTH_CLIENT_ID", None)
        os.environ.pop("GDRIVE_REFRESH_TOKEN", None)


def test_from_env_succeeds_when_required_fields_set() -> None:
    """必須フィールドが設定されている場合、正常に作成されること.

    Arrange:
        必須フィールドを設定する。

    Act:
        from_env()を呼び出す。

    Assert:
        設定オブジェクトが正常に作成されること。
    """
    # Arrange
    os.environ["YOUTUBE_API_KEY"] = "test_api_key"
    os.environ["YOUTUBE_CHANNEL_IDS"] = "channel1,channel2"
    os.environ["GDRIVE_OAUTH_CLIENT_ID"] = "client_id_123"
    os.environ["GDRIVE_REFRESH_TOKEN"] = "refresh_token_123"
    os.environ["GDRIVE_ROOT_FOLDER_ID"] = "folder123"

    try:
        # Act
        settings = Settings.from_env()

        # Assert
        assert settings.youtube_api_key == "test_api_key"
        assert settings.youtube_channel_ids == ["channel1", "channel2"]
        assert settings.gdrive_oauth_client_id == "client_id_123"
        assert settings.gdrive_refresh_token == "refresh_token_123"
        assert settings.gdrive_root_folder_id == "folder123"
    finally:
        os.environ.pop("YOUTUBE_API_KEY", None)
        os.environ.pop("YOUTUBE_CHANNEL_IDS", None)
        os.environ.pop("GDRIVE_OAUTH_CLIENT_ID", None)
        os.environ.pop("GDRIVE_REFRESH_TOKEN", None)
        os.environ.pop("GDRIVE_ROOT_FOLDER_ID", None)
