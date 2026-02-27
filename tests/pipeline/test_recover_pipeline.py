"""中断状態回復パイプラインのテスト."""

from pathlib import Path

import pytest

from src.models.stream import Stream
from src.models.stream_status import StreamStatus
from src.pipeline.recover_pipeline import RecoverPipeline
from src.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


@pytest.fixture
def thumbnail_dir(tmp_path: Path) -> Path:
    """テスト用サムネイルディレクトリを作成する."""
    return tmp_path / "thumbnails"


def test_recover_all_reverts_downloading_to_discovered(
    repository: StreamRepository,
    thumbnail_dir: Path,
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
    count = RecoverPipeline(
        max_retries=3, thumbnail_dir=thumbnail_dir, repository=repository
    ).recover_all()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DISCOVERED


def test_recover_all_reverts_uploading_to_thumbs_done(
    repository: StreamRepository,
    thumbnail_dir: Path,
) -> None:
    """recover_allがuploading状態をthumbs_doneに戻すこと.

    Arrange:
        uploadingステータスのストリームを登録する。
        サムネイルディレクトリを作成して、thumbs_done状態が維持されるようにする。

    Act:
        recover_all()を呼び出す。

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
    ).recover_all()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.THUMBS_DONE


def test_recover_all_respects_max_retries(
    repository: StreamRepository,
    thumbnail_dir: Path,
) -> None:
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
    count = RecoverPipeline(
        max_retries=3, thumbnail_dir=thumbnail_dir, repository=repository
    ).recover_all()

    # Assert
    assert count == 0
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADING


def test_recover_all_reverts_thumbs_done_to_downloaded_when_no_thumbnails(
    repository: StreamRepository,
    thumbnail_dir: Path,
) -> None:
    """recover_allがサムネイルディレクトリがないthumbs_done状態をdownloadedに戻すこと.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        サムネイルディレクトリを作成しない。

    Act:
        recover_all()を呼び出す。

    Assert:
        ステータスがdownloadedに戻っていること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.THUMBS_DONE, title="Test Video")
    )

    # Act
    count = RecoverPipeline(
        max_retries=3, thumbnail_dir=thumbnail_dir, repository=repository
    ).recover_all()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADED


def test_recover_all_keeps_thumbs_done_when_thumbnails_exist(
    repository: StreamRepository,
    thumbnail_dir: Path,
) -> None:
    """recover_allがサムネイルが存在するthumbs_done状態を維持すること.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        サムネイルディレクトリにファイルを作成する。

    Act:
        recover_all()を呼び出す。

    Assert:
        ステータスがthumbs_doneのままであること。
    """
    # Arrange
    repository.insert(
        Stream(video_id="video1", status=StreamStatus.THUMBS_DONE, title="Test Video")
    )
    # サムネイルディレクトリにファイルを作成
    thumb_dir = thumbnail_dir / "video1"
    thumb_dir.mkdir(parents=True)
    (thumb_dir / "thumb_0001.jpg").touch()

    # Act
    count = RecoverPipeline(
        max_retries=3, thumbnail_dir=thumbnail_dir, repository=repository
    ).recover_all()

    # Assert
    assert count == 0
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.THUMBS_DONE


def test_recover_all_reverts_thumbs_done_to_downloaded_when_empty_directory(
    repository: StreamRepository,
    thumbnail_dir: Path,
) -> None:
    """recover_allが空のサムネイルディレクトリのthumbs_done状態をdownloadedに戻すこと.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        空のサムネイルディレクトリを作成する。

    Act:
        recover_all()を呼び出す。

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
    ).recover_all()

    # Assert
    assert count == 1
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.DOWNLOADED
