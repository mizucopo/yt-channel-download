"""ストリームリポジトリのテスト."""

from pathlib import Path

import pytest

from src.models.stream import Stream
from src.models.stream_status import StreamStatus
from src.repository.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


def test_insert_creates_new_record(repository: StreamRepository) -> None:
    """新しいストリームを登録すると、レコードが作成されること.

    Arrange:
        テスト用のストリームデータを準備する。

    Act:
        insert()を呼び出してストリームを登録する。

    Assert:
        get()で取得したレコードが登録したデータと一致すること。
    """
    # Arrange
    stream = Stream(
        video_id="test_video_id",
        status=StreamStatus.DISCOVERED,
        title="Test Video",
        published_at="2024-01-01T00:00:00",
    )

    # Act
    repository.insert(stream)

    # Assert
    result = repository.get("test_video_id")
    assert result is not None
    assert result.video_id == "test_video_id"
    assert result.status == StreamStatus.DISCOVERED
    assert result.title == "Test Video"


def test_get_returns_none_for_nonexistent_video(repository: StreamRepository) -> None:
    """存在しないvideo_idでgetを呼び出すとNoneが返されること.

    Arrange:
        リポジトリを初期化する（レコードなし）。

    Act:
        存在しないvideo_idでget()を呼び出す。

    Assert:
        Noneが返されること。
    """
    # Act
    result = repository.get("nonexistent_id")

    # Assert
    assert result is None


def test_get_by_status_returns_matching_records(
    repository: StreamRepository,
) -> None:
    """指定したステータスのストリームのみが取得されること.

    Arrange:
        異なるステータスを持つ複数のストリームを登録する。

    Act:
        get_by_status()で特定のステータスを指定して取得する。

    Assert:
        指定したステータスのストリームのみが返されること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.DISCOVERED, title="Video 1")
    )
    repository.insert(
        Stream(video_id="video2", status=StreamStatus.DOWNLOADED, title="Video 2")
    )
    repository.insert(
        Stream(video_id="video3", status=StreamStatus.DISCOVERED, title="Video 3")
    )

    # Act
    result = repository.get_by_status(StreamStatus.DISCOVERED)

    # Assert
    assert len(result) == 2
    video_ids = [s.video_id for s in result]
    assert "video1" in video_ids
    assert "video3" in video_ids
    assert "video2" not in video_ids


def test_update_status_changes_status(repository: StreamRepository) -> None:
    """update_statusでステータスが更新されること.

    Arrange:
        discoveredステータスのストリームを登録する。

    Act:
        update_status()でステータスをdownloadedに変更する。

    Assert:
        ステータスが正しく更新されていること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.DISCOVERED, title="Test Video")
    )

    # Act
    success = repository.update_status(
        "video1", StreamStatus.DOWNLOADED, expected_old_status=StreamStatus.DISCOVERED
    )

    # Assert
    assert success is True
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADED


def test_update_status_with_cas_fails_on_mismatch(repository: StreamRepository) -> None:
    """CAS更新でステータスが一致しない場合、更新が失敗すること.

    Arrange:
        discoveredステータスのストリームを登録する。

    Act:
        間違った期待値(downloaded)を指定してupdate_status()を呼び出す。

    Assert:
        更新が失敗し、ステータスが変更されないこと。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.DISCOVERED, title="Test Video")
    )

    # Act
    success = repository.update_status(
        "video1",
        StreamStatus.UPLOADING,
        expected_old_status=StreamStatus.DOWNLOADED,
    )

    # Assert
    assert success is False
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DISCOVERED


def test_update_status_updates_local_path(repository: StreamRepository) -> None:
    """update_statusでlocal_pathが更新されること.

    Arrange:
        discoveredステータスのストリームを登録する。

    Act:
        update_status()でステータスとlocal_pathを同時に更新する。

    Assert:
        両方のフィールドが正しく更新されていること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.DISCOVERED, title="Test Video")
    )

    # Act
    success = repository.update_status(
        "video1",
        StreamStatus.DOWNLOADED,
        expected_old_status=StreamStatus.DISCOVERED,
        local_path="/path/to/video.mp4",
    )

    # Assert
    assert success is True
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADED
    assert result.local_path == "/path/to/video.mp4"


def test_get_next_pending_returns_oldest_record(repository: StreamRepository) -> None:
    """get_next_pendingで最も古いレコードが取得されること.

    Arrange:
        複数のdiscoveredストリームを登録する。

    Act:
        get_next_pending()を呼び出す。

    Assert:
        最も古いレコードが返されること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.DISCOVERED, title="Video 1")
    )
    repository.insert(
        Stream(video_id="video2", status=StreamStatus.DISCOVERED, title="Video 2")
    )

    # Act
    result = repository.get_next_pending(StreamStatus.DISCOVERED, max_retries=3)

    # Assert
    assert result is not None
    assert result.video_id == "video1"


def test_get_next_pending_respects_max_retries(repository: StreamRepository) -> None:
    """リトライ回数が上限に達したストリームはget_next_pendingで取得されないこと.

    Arrange:
        リトライ回数が上限のストリームと、そうでないストリームを登録する。

    Act:
        get_next_pending()を呼び出す。

    Assert:
        リトライ回数が上限未満のストリームのみが返されること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.DISCOVERED, title="Video 1")
    )
    repository.insert(
        Stream(video_id="video2", status=StreamStatus.DISCOVERED, title="Video 2")
    )
    # video1のリトライ回数を増やす
    repository.update_status(
        "video1",
        StreamStatus.DISCOVERED,
        expected_old_status=StreamStatus.DISCOVERED,
        increment_retry=True,
    )

    # Act
    result = repository.get_next_pending(StreamStatus.DISCOVERED, max_retries=1)

    # Assert
    assert result is not None
    assert result.video_id == "video2"
