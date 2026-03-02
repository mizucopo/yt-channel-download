"""Google OAuth認証コマンドのテスト."""

from unittest.mock import MagicMock, patch

import pytest
from mizu_common import GoogleScope

from src.commands.auth_command import AuthCommand


@pytest.fixture
def mock_settings() -> MagicMock:
    """モック設定を作成する."""
    settings = MagicMock()
    settings.google_oauth_client_id = "test_client_id"
    settings.google_oauth_client_secret = "test_client_secret"
    return settings


def test_execute_succeeds_with_valid_credentials(mock_settings: MagicMock) -> None:
    """有効な認証情報で認証が成功すること.

    Arrange:
        設定にCLIENT_IDとCLIENT_SECRETを設定する。
        GoogleOAuthClient.authenticateをモックする。

    Act:
        execute()を呼び出す。

    Assert:
        authenticateが正しい引数で呼ばれること。
        リフレッシュトークンが出力されること。
    """
    # Arrange
    command = AuthCommand(mock_settings)

    with (
        patch(
            "src.commands.auth_command.GoogleOAuthClient.authenticate",
            return_value="test_refresh_token",
        ) as mock_auth,
        patch("src.commands.auth_command.click.echo") as mock_echo,
    ):
        # Act
        command.execute()

        # Assert
        mock_auth.assert_called_once_with(
            "test_client_id",
            "test_client_secret",
            [GoogleScope.YOUTUBE_READONLY, GoogleScope.DRIVE_FILE],
        )
        # リフレッシュトークンを含むメッセージが出力されること
        calls = mock_echo.call_args_list
        assert any("test_refresh_token" in str(call) for call in calls)


@pytest.mark.parametrize(
    "missing_field",
    [
        pytest.param("client_id", id="client_id_missing"),
        pytest.param("client_secret", id="client_secret_missing"),
    ],
)
def test_execute_fails_when_required_field_missing(
    mock_settings: MagicMock, missing_field: str
) -> None:
    """必須フィールドが未設定の場合に失敗すること.

    Arrange:
        指定されたフィールドを空にする。

    Act:
        execute()を呼び出す。

    Assert:
        SystemExit(1)が発生すること。
    """
    # Arrange
    if missing_field == "client_id":
        mock_settings.google_oauth_client_id = ""
    else:
        mock_settings.google_oauth_client_secret = ""
    command = AuthCommand(mock_settings)

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        command.execute()
    assert exc_info.value.code == 1


def test_execute_fails_when_authentication_fails(mock_settings: MagicMock) -> None:
    """認証が失敗した場合にSystemExitが発生すること.

    Arrange:
        GoogleOAuthClient.authenticateがNoneを返すようにモックする。

    Act:
        execute()を呼び出す。

    Assert:
        SystemExit(1)が発生すること。
    """
    # Arrange
    command = AuthCommand(mock_settings)

    with patch(
        "src.commands.auth_command.GoogleOAuthClient.authenticate",
        return_value=None,
    ):
        # Act & Assert
        with pytest.raises(SystemExit) as exc_info:
            command.execute()
        assert exc_info.value.code == 1
