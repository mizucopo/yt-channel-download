"""中断状態回復パイプラインのテスト."""

from pathlib import Path

import pytest

from src.models.stream import Stream
from src.models.stream_status import StreamStatus
from src.pipeline.recover import RecoverPipeline
from src.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


def test_recover_all_reverts_downloading_to_discovered(
    repository: StreamRepository,
) -> None:
    """recover_allがdownloading状態をdiscoveredに戻すこと.

    Arrange:
        downloadingステータスのストリームを登録する。

    Act:
        recover_all()を呼び出す。

    Assert:
        ステータスがdiscoveredに戻っていること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.DOWNLOADING, title="Test Video")
    )

    # Act
    count = RecoverPipeline(max_retries=3, repository=repository).recover_all()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DISCOVERED


def test_recover_all_reverts_uploading_to_thumbs_done(
    repository: StreamRepository,
) -> None:
    """recover_allがuploading状態をthumbs_doneに戻すこと.

    Arrange:
        uploadingステータスのストリームを登録する。

    Act:
        recover_all()を呼び出す。

    Assert:
        ステータスがthumbs_doneに戻っていること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.UPLOADING, title="Test Video")
    )

    # Act
    count = RecoverPipeline(max_retries=3, repository=repository).recover_all()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.THUMBS_DONE


def test_recover_all_respects_max_retries(repository: StreamRepository) -> None:
    """recover_allがリトライ上限に達したストリームをスキップすること.

    Arrange:
        リトライ回数が上限に達したdownloadingストリームを登録する。

    Act:
        recover_all()を呼び出す。

    Assert:
        ステータスが変更されないこと。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.DOWNLOADING, title="Test Video")
    )
    # リトライ回数を上限まで増やす
    for _ in range(3):
        repository.update_status(
            "video1",
            StreamStatus.DOWNLOADING,
            expected_old_status=StreamStatus.DOWNLOADING,
            increment_retry=True,
        )

    # Act
    count = RecoverPipeline(max_retries=3, repository=repository).recover_all()

    # Assert
    assert count == 0
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADING
