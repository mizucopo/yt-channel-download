"""データベースモジュールのテスト."""

from pathlib import Path

import pytest

from src import db
from src.models.stream import Stream


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト用データベースをセットアップする.

    Arrange:
        一時ディレクトリにテスト用データベースを作成する。
    """
    test_db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.config.settings.database_path", test_db_path)
    db.init_db()


def test_insert_stream_creates_new_record() -> None:
    """新しいストリームを登録すると、データベースにレコードが作成されること.

    Arrange:
        テスト用のストリームデータを準備する。

    Act:
        insert_stream()を呼び出してストリームを登録する。

    Assert:
        get_stream()で取得したレコードが登録したデータと一致すること。
    """
    # Arrange
    stream = Stream(
        video_id="test_video_id",
        status="discovered",
        title="Test Video",
        published_at="2024-01-01T00:00:00",
    )

    # Act
    db.insert_stream(stream)

    # Assert
    result = db.get_stream("test_video_id")
    assert result is not None
    assert result.video_id == "test_video_id"
    assert result.status == "discovered"
    assert result.title == "Test Video"


def test_get_stream_returns_none_for_nonexistent_video() -> None:
    """存在しないvideo_idでget_streamを呼び出すとNoneが返されること.

    Arrange:
        データベースを初期化する（レコードなし）。

    Act:
        存在しないvideo_idでget_stream()を呼び出す。

    Assert:
        Noneが返されること。
    """
    # Act
    result = db.get_stream("nonexistent_id")

    # Assert
    assert result is None


def test_get_streams_by_status_returns_matching_records() -> None:
    """指定したステータスのストリームのみが取得されること.

    Arrange:
        異なるステータスを持つ複数のストリームを登録する。

    Act:
        get_streams_by_status()で特定のステータスを指定して取得する。

    Assert:
        指定したステータスのストリームのみが返されること。
    """
    # Arrange
    db.insert_stream(Stream(video_id="video1", status="discovered", title="Video 1"))
    db.insert_stream(Stream(video_id="video2", status="downloaded", title="Video 2"))
    db.insert_stream(Stream(video_id="video3", status="discovered", title="Video 3"))

    # Act
    result = db.get_streams_by_status("discovered")

    # Assert
    assert len(result) == 2
    video_ids = [s.video_id for s in result]
    assert "video1" in video_ids
    assert "video3" in video_ids
    assert "video2" not in video_ids


def test_update_status_changes_status() -> None:
    """update_statusでステータスが更新されること.

    Arrange:
        discoveredステータスのストリームを登録する。

    Act:
        update_status()でステータスをdownloadedに変更する。

    Assert:
        ステータスが正しく更新されていること。
    """
    # Arrange
    db.insert_stream(Stream(video_id="video1", status="discovered", title="Test Video"))

    # Act
    success = db.update_status("video1", "downloaded", expected_old_status="discovered")

    # Assert
    assert success is True
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "downloaded"


def test_update_status_with_cas_fails_on_mismatch() -> None:
    """CAS更新でステータスが一致しない場合、更新が失敗すること.

    Arrange:
        discoveredステータスのストリームを登録する。

    Act:
        間違った期待値(downloaded)を指定してupdate_status()を呼び出す。

    Assert:
        更新が失敗し、ステータスが変更されないこと。
    """
    # Arrange
    db.insert_stream(Stream(video_id="video1", status="discovered", title="Test Video"))

    # Act
    success = db.update_status("video1", "uploading", expected_old_status="downloaded")

    # Assert
    assert success is False
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "discovered"


def test_update_status_updates_local_path() -> None:
    """update_statusでlocal_pathが更新されること.

    Arrange:
        discoveredステータスのストリームを登録する。

    Act:
        update_status()でステータスとlocal_pathを同時に更新する。

    Assert:
        両方のフィールドが正しく更新されていること。
    """
    # Arrange
    db.insert_stream(Stream(video_id="video1", status="discovered", title="Test Video"))

    # Act
    success = db.update_status(
        "video1",
        "downloaded",
        expected_old_status="discovered",
        local_path="/path/to/video.mp4",
    )

    # Assert
    assert success is True
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "downloaded"
    assert result.local_path == "/path/to/video.mp4"


def test_get_next_pending_returns_oldest_record() -> None:
    """get_next_pendingで最も古いレコードが取得されること.

    Arrange:
        複数のdiscoveredストリームを登録する。

    Act:
        get_next_pending()を呼び出す。

    Assert:
        最も古いレコードが返されること。
    """
    # Arrange
    db.insert_stream(Stream(video_id="video1", status="discovered", title="Video 1"))
    db.insert_stream(Stream(video_id="video2", status="discovered", title="Video 2"))

    # Act
    result = db.get_next_pending("discovered", max_retries=3)

    # Assert
    assert result is not None
    assert result.video_id == "video1"


def test_get_next_pending_respects_max_retries() -> None:
    """リトライ回数が上限に達したストリームはget_next_pendingで取得されないこと.

    Arrange:
        リトライ回数が上限のストリームと、そうでないストリームを登録する。

    Act:
        get_next_pending()を呼び出す。

    Assert:
        リトライ回数が上限未満のストリームのみが返されること。
    """
    # Arrange
    db.insert_stream(Stream(video_id="video1", status="discovered", title="Video 1"))
    db.insert_stream(Stream(video_id="video2", status="discovered", title="Video 2"))
    # video1のリトライ回数を増やす
    db.update_status(
        "video1", "discovered", expected_old_status="discovered", increment_retry=True
    )

    # Act
    result = db.get_next_pending("discovered", max_retries=1)

    # Assert
    assert result is not None
    assert result.video_id == "video2"
