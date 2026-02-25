"""中断状態回復パイプラインのテスト."""

from pathlib import Path

import pytest

from src import db
from src.pipeline import recover


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト用データベースをセットアップする."""
    test_db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.config.settings.database_path", test_db_path)
    monkeypatch.setattr("src.config.settings.max_retries", 3)
    db.init_db()


def test_recover_streams_reverts_downloading_to_discovered() -> None:
    """recover_streamsがdownloading状態をdiscoveredに戻すこと.

    Arrange:
        downloadingステータスのストリームを登録する。

    Act:
        recover_streams()を呼び出す。

    Assert:
        ステータスがdiscoveredに戻っていること。
    """
    # Arrange
    db.insert_stream(
        db.Stream(video_id="video1", status="downloading", title="Test Video")
    )

    # Act
    count = recover.recover_streams()

    # Assert
    assert count == 1
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "discovered"


def test_recover_streams_reverts_uploading_to_thumbs_done() -> None:
    """recover_streamsがuploading状態をthumbs_doneに戻すこと.

    Arrange:
        uploadingステータスのストリームを登録する。

    Act:
        recover_streams()を呼び出す。

    Assert:
        ステータスがthumbs_doneに戻っていること。
    """
    # Arrange
    db.insert_stream(
        db.Stream(video_id="video1", status="uploading", title="Test Video")
    )

    # Act
    count = recover.recover_streams()

    # Assert
    assert count == 1
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "thumbs_done"


def test_recover_streams_respects_max_retries(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """recover_streamsがリトライ上限に達したストリームをスキップすること.

    Arrange:
        リトライ回数が上限に達したdownloadingストリームを登録する。

    Act:
        recover_streams()を呼び出す。

    Assert:
        ステータスが変更されないこと。
    """
    # Arrange
    db.insert_stream(
        db.Stream(video_id="video1", status="downloading", title="Test Video")
    )
    # リトライ回数を上限まで増やす
    for _ in range(3):
        db.update_status(
            "video1",
            "downloading",
            expected_old_status="downloading",
            increment_retry=True,
        )

    monkeypatch.setattr("src.config.settings.max_retries", 3)

    # Act
    count = recover.recover_streams()

    # Assert
    assert count == 0
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "downloading"
