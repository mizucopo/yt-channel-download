"""動画ダウンロードパイプラインのテスト."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src import db
from src.models.stream import Stream
from src.pipeline.download import DownloadPipeline


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト用データベースをセットアップする."""
    test_db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.config.settings.database_path", test_db_path)
    monkeypatch.setattr("src.config.settings.download_dir", str(tmp_path / "downloads"))
    monkeypatch.setattr("src.config.settings.max_retries", 3)
    db.init_db()


def test_download_video_updates_status_on_success() -> None:
    """download_videoが成功時にステータスを更新すること.

    Arrange:
        discoveredステータスのストリームを登録する。
        subprocess.runをモックして成功を返す。

    Act:
        download_video()を呼び出す。

    Assert:
        ステータスがdownloadedに更新されていること。
    """
    # Arrange
    db.insert_stream(Stream(video_id="video1", status="discovered", title="Test Video"))

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result):
        # Act
        success = DownloadPipeline().download_video("video1")

    # Assert
    assert success is True
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "downloaded"


def test_download_video_reverts_status_on_failure() -> None:
    """download_videoが失敗時にステータスを元に戻すこと.

    Arrange:
        discoveredステータスのストリームを登録する。
        subprocess.runをモックして失敗を返す。

    Act:
        download_video()を呼び出す。

    Assert:
        ステータスがdiscoveredに戻っていること。
    """
    # Arrange
    db.insert_stream(Stream(video_id="video1", status="discovered", title="Test Video"))

    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "Download failed"

    with patch("subprocess.run", return_value=mock_result):
        # Act
        success = DownloadPipeline().download_video("video1")

    # Assert
    assert success is False
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "discovered"
    assert result.retry_count == 1


def test_download_video_fails_on_cas_mismatch() -> None:
    """CAS更新が失敗した場合、download_videoがFalseを返すこと.

    Arrange:
        downloadedステータスのストリームを登録する
        （CAS更新が失敗するように）。

    Act:
        download_video()を呼び出す。

    Assert:
        Falseが返されること。
    """
    # Arrange
    db.insert_stream(Stream(video_id="video1", status="downloaded", title="Test Video"))

    # Act
    success = DownloadPipeline().download_video("video1")

    # Assert
    assert success is False
