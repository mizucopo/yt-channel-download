"""ローカルファイルクリーンアップパイプラインのテスト."""

from pathlib import Path

import pytest

from src import db
from src.pipeline import cleanup


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """テスト用データベースをセットアップする."""
    test_db_path = str(tmp_path / "test.db")
    monkeypatch.setattr("src.config.settings.database_path", test_db_path)
    monkeypatch.setattr("src.config.settings.download_dir", str(tmp_path / "downloads"))
    monkeypatch.setattr(
        "src.config.settings.thumbnail_dir", str(tmp_path / "thumbnails")
    )
    monkeypatch.setattr("src.config.settings.max_retries", 3)
    db.init_db()


def test_cleanup_video_deletes_files(tmp_path: Path) -> None:
    """cleanup_videoがローカルファイルを削除すること.

    Arrange:
        uploadedステータスのストリームを登録する。
        動画ファイルとサムネイルディレクトリを作成する。

    Act:
        cleanup_video()を呼び出す。

    Assert:
        ファイルが削除され、ステータスがcleanedに更新されていること。
    """
    # Arrange
    video_path = tmp_path / "downloads" / "video1.mp4"
    video_path.parent.mkdir(parents=True, exist_ok=True)
    video_path.touch()

    thumb_dir = tmp_path / "thumbnails" / "video1"
    thumb_dir.mkdir(parents=True)
    (thumb_dir / "thumb_0001.jpg").touch()

    db.insert_stream(
        db.Stream(
            video_id="video1",
            status="uploaded",
            title="Test Video",
            local_path=str(video_path),
        )
    )

    # Act
    success = cleanup.cleanup_video("video1", str(video_path))

    # Assert
    assert success is True
    assert not video_path.exists()
    assert not thumb_dir.exists()
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "cleaned"


def test_cleanup_video_handles_missing_files() -> None:
    """cleanup_videoが存在しないファイルを適切に処理すること.

    Arrange:
        uploadedステータスのストリームを登録する。
        ファイルは作成しない。

    Act:
        cleanup_video()を呼び出す。

    Assert:
        成功し、ステータスがcleanedに更新されていること。
    """
    # Arrange
    db.insert_stream(
        db.Stream(
            video_id="video1",
            status="uploaded",
            title="Test Video",
            local_path="/nonexistent/video.mp4",
        )
    )

    # Act
    success = cleanup.cleanup_video("video1", "/nonexistent/video.mp4")

    # Assert
    assert success is True
    result = db.get_stream("video1")
    assert result is not None
    assert result.status == "cleaned"
