"""中断状態回復パイプラインのテスト."""

from pathlib import Path

import pytest

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.recover_pipeline import RecoverPipeline
from src.repository.stream_repository import StreamRepository


@pytest.fixture
def thumbnail_dir(tmp_path: Path) -> Path:
    """テスト用サムネイルディレクトリを作成する."""
    return tmp_path / "thumbnails"


def test_run_reverts_downloading_to_discovered(
    repository: StreamRepository,
    thumbnail_dir: Path,
) -> None:
    """runがdownloading状態をdiscoveredに戻すこと.

    Arrange:
        downloadingステータスのストリームを登録する。

    Act:
        run()を呼び出す。

    Assert:
        ステータスがdiscoveredに戻っていること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.DOWNLOADING, title="Test Video")
    )

    # Act
    count = RecoverPipeline(
        max_retries=3, thumbnail_dir=thumbnail_dir, repository=repository
    ).run()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DISCOVERED


def test_run_reverts_uploading_to_thumbs_done(
    repository: StreamRepository,
    thumbnail_dir: Path,
) -> None:
    """runがuploading状態をthumbs_doneに戻すこと.

    Arrange:
        uploadingステータスのストリームを登録する。
        サムネイルディレクトリを作成して、thumbs_done状態が維持されるようにする。

    Act:
        run()を呼び出す。

    Assert:
        ステータスがthumbs_doneに戻っていること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.UPLOADING, title="Test Video")
    )
    # サムネイルディレクトリを作成して、thumbs_done状態が維持されるようにする
    thumb_dir = thumbnail_dir / "video1"
    thumb_dir.mkdir(parents=True)
    (thumb_dir / "thumb_0001.jpg").touch()

    # Act
    count = RecoverPipeline(
        max_retries=3, thumbnail_dir=thumbnail_dir, repository=repository
    ).run()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.THUMBS_DONE


def test_run_respects_max_retries(
    repository: StreamRepository,
    thumbnail_dir: Path,
) -> None:
    """runがリトライ上限に達したストリームをスキップすること.

    Arrange:
        リトライ回数が上限に達したdownloadingストリームを登録する。

    Act:
        run()を呼び出す。

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
    count = RecoverPipeline(
        max_retries=3, thumbnail_dir=thumbnail_dir, repository=repository
    ).run()

    # Assert
    assert count == 0
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADING


def test_run_reverts_thumbs_done_to_downloaded_when_empty_directory(
    repository: StreamRepository,
    thumbnail_dir: Path,
) -> None:
    """runが空のサムネイルディレクトリのthumbs_done状態をdownloadedに戻すこと.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        空のサムネイルディレクトリを作成する。

    Act:
        run()を呼び出す。

    Assert:
        ステータスがdownloadedに戻っていること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.THUMBS_DONE, title="Test Video")
    )
    # 空のサムネイルディレクトリを作成
    thumb_dir = thumbnail_dir / "video1"
    thumb_dir.mkdir(parents=True)

    # Act
    count = RecoverPipeline(
        max_retries=3, thumbnail_dir=thumbnail_dir, repository=repository
    ).run()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADED
