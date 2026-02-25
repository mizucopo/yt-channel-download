"""ローカルファイルクリーンアップパイプラインのテスト."""

from pathlib import Path

import pytest

from src.models.stream import Stream
from src.pipeline.cleanup import CleanupPipeline
from src.repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


def test_cleanup_video_deletes_files(
    repository: StreamRepository, tmp_path: Path
) -> None:
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

    thumbnail_dir = tmp_path / "thumbnails"
    thumb_dir = thumbnail_dir / "video1"
    thumb_dir.mkdir(parents=True)
    (thumb_dir / "thumb_0001.jpg").touch()

    repository.insert(
        Stream(
            video_id="video1",
            status="uploaded",
            title="Test Video",
            local_path=str(video_path),
        )
    )

    # Act
    success = CleanupPipeline(
        max_retries=3,
        download_dir=tmp_path / "downloads",
        thumbnail_dir=thumbnail_dir,
        repository=repository,
    ).cleanup_video("video1", str(video_path))

    # Assert
    assert success is True
    assert not video_path.exists()
    assert not thumb_dir.exists()
    result = repository.get("video1")
    assert result is not None
    assert result.status == "cleaned"


def test_cleanup_video_handles_missing_files(
    repository: StreamRepository, tmp_path: Path
) -> None:
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
    repository.insert(
        Stream(
            video_id="video1",
            status="uploaded",
            title="Test Video",
            local_path="/nonexistent/video.mp4",
        )
    )

    # Act
    success = CleanupPipeline(
        max_retries=3,
        download_dir=tmp_path / "downloads",
        thumbnail_dir=tmp_path / "thumbnails",
        repository=repository,
    ).cleanup_video("video1", "/nonexistent/video.mp4")

    # Assert
    assert success is True
    result = repository.get("video1")
    assert result is not None
    assert result.status == "cleaned"
