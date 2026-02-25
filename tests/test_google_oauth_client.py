"""Google OAuth認証クライアントのテスト."""

from typing import Any
from unittest.mock import Mock

import pytest

from src.google_oauth_client import GoogleOAuthClient


def test_google_oauth_client_initializes_with_credentials() -> None:
    """GoogleOAuthClientが認証情報で初期化されること.

    Arrange:
        テスト用の認証情報を準備する。

    Act:
        GoogleOAuthClientを作成する。

    Assert:
        認証情報が正しく設定されていること。
    """
    # Arrange
    oauth_client_id = "test_client_id"
    refresh_token = "test_refresh_token"

    # Act
    client = GoogleOAuthClient(oauth_client_id, refresh_token)

    # Assert
    assert client._oauth_client_id == oauth_client_id
    assert client._refresh_token == refresh_token


def test_google_oauth_client_has_required_scopes() -> None:
    """GoogleOAuthClientが必要なスコープを持っていること.

    Arrange:
        GoogleOAuthClientを作成する。

    Act:
        SCOPESを取得する。

    Assert:
        YouTube読み取りとDriveファイルスコープが含まれていること。
    """
    # Arrange & Act
    scopes = GoogleOAuthClient.SCOPES

    # Assert
    assert "https://www.googleapis.com/auth/youtube.readonly" in scopes
    assert "https://www.googleapis.com/auth/drive.file" in scopes


def test_get_access_token_refreshes_token(mocker: Any) -> None:
    """get_access_tokenがトークンをリフレッシュすること.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。

    Act:
        get_access_token()を呼び出す。

    Assert:
        アクセストークンが返されること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "new_access_token"}
    mocker.patch("requests.post", return_value=mock_response)

    client = GoogleOAuthClient("client_id", "refresh_token")

    # Act
    token = client.get_access_token()

    # Assert
    assert token == "new_access_token"


def test_get_access_token_raises_error_on_failure(mocker: Any) -> None:
    """トークン取得失敗時にRuntimeErrorが発生すること.

    Arrange:
        エラーレスポンスをモックする。

    Act:
        get_access_token()を呼び出す。

    Assert:
        RuntimeErrorが発生すること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 400
    mock_response.text = "invalid_grant"
    mocker.patch("requests.post", return_value=mock_response)

    client = GoogleOAuthClient("client_id", "invalid_refresh_token")

    # Act & Assert
    with pytest.raises(RuntimeError, match="アクセストークンの取得に失敗しました"):
        client.get_access_token()


def test_get_headers_returns_authorization_header(mocker: Any) -> None:
    """get_headersがAuthorizationヘッダーを返すこと.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。

    Act:
        get_headers()を呼び出す。

    Assert:
        Authorizationヘッダーが正しく設定されていること。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "test_access_token"}
    mocker.patch("requests.post", return_value=mock_response)

    client = GoogleOAuthClient("client_id", "refresh_token")

    # Act
    headers = client.get_headers()

    # Assert
    assert headers == {"Authorization": "Bearer test_access_token"}


def test_get_access_token_caches_token(mocker: Any) -> None:
    """get_access_tokenがトークンをキャッシュすること.

    Arrange:
        トークンリフレッシュAPIのレスポンスをモックする。

    Act:
        get_access_token()を複数回呼び出す。

    Assert:
        2回目以降はAPIが呼ばれないこと。
    """
    # Arrange
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"access_token": "cached_token"}
    mock_post = mocker.patch("requests.post", return_value=mock_response)

    client = GoogleOAuthClient("client_id", "refresh_token")

    # Act
    token1 = client.get_access_token()
    token2 = client.get_access_token()

    # Assert
    assert token1 == "cached_token"
    assert token2 == "cached_token"
    mock_post.assert_called_once()
