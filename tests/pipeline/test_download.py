"""動画ダウンロードパイプラインのテスト."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.models.stream import Stream
from src.pipeline.download import DownloadPipeline
from src.repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


def test_download_video_updates_status_on_success(
    repository: StreamRepository, tmp_path: Path
) -> None:
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
    repository.insert(
        Stream(video_id="video1", status="discovered", title="Test Video")
    )

    mock_result = Mock()
    mock_result.returncode = 0
    mock_result.stderr = ""

    download_dir = tmp_path / "downloads"

    with patch("subprocess.run", return_value=mock_result):
        # Act
        success = DownloadPipeline(
            max_retries=3,
            download_dir=download_dir,
            repository=repository,
        ).download_video("video1")

    # Assert
    assert success is True
    result = repository.get("video1")
    assert result is not None
    assert result.status == "downloaded"


def test_download_video_reverts_status_on_failure(
    repository: StreamRepository, tmp_path: Path
) -> None:
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
    repository.insert(
        Stream(video_id="video1", status="discovered", title="Test Video")
    )

    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "Download failed"

    download_dir = tmp_path / "downloads"

    with patch("subprocess.run", return_value=mock_result):
        # Act
        success = DownloadPipeline(
            max_retries=3,
            download_dir=download_dir,
            repository=repository,
        ).download_video("video1")

    # Assert
    assert success is False
    result = repository.get("video1")
    assert result is not None
    assert result.status == "discovered"
    assert result.retry_count == 1


def test_download_video_fails_on_cas_mismatch(
    repository: StreamRepository, tmp_path: Path
) -> None:
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
    repository.insert(
        Stream(video_id="video1", status="downloaded", title="Test Video")
    )

    download_dir = tmp_path / "downloads"

    # Act
    success = DownloadPipeline(
        max_retries=3,
        download_dir=download_dir,
        repository=repository,
    ).download_video("video1")

    # Assert
    assert success is False
