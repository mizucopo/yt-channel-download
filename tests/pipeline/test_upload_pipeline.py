"""Google Driveアップロードパイプラインのテスト."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.upload_pipeline import UploadPipeline
from src.repository.stream_repository import StreamRepository
from src.utils.path_manager import PathManager


def test_upload_video_updates_status_on_success(
    repository: StreamRepository, tmp_path: Path
) -> None:
    """upload_videoが成功時にステータスを更新すること.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        動画ファイルを作成する。
        GoogleDriveProviderをモックする。

    Act:
        upload_video()を呼び出す。

    Assert:
        ステータスがuploadedに更新されていること。
    """
    # Arrange
    video_path = tmp_path / "video.mp4"
    video_path.touch()

    repository.insert(
        Stream(
            video_id="video1",
            status=StreamStatus.THUMBS_DONE,
            title="Test Video",
            local_path=str(video_path),
        )
    )

    mock_provider = Mock()

    thumbnail_dir = tmp_path / "thumbnails"
    path_manager = PathManager(
        download_dir=tmp_path / "downloads",
        thumbnail_dir=thumbnail_dir,
        database_path=tmp_path / "test.db",
    )

    # Act
    success = UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_provider,
        gdrive_root_folder_id="folder_id",
        path_manager=path_manager,
        repository=repository,
    ).upload_video("video1", str(video_path))

    # Assert
    assert success is True
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.UPLOADED
    assert result.gdrive_file_id == ""  # 新APIではファイルIDを返さない
    mock_provider.upload.assert_called_once_with(
        source_path=str(video_path),
        destination_filename="video.mp4",
    )


def test_upload_video_reverts_status_on_failure(
    repository: StreamRepository, tmp_path: Path
) -> None:
    """upload_videoが失敗時にステータスを元に戻すこと.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        動画ファイルを作成する。
        GoogleDriveProviderをモックして例外を発生させる。

    Act:
        upload_video()を呼び出す。

    Assert:
        ステータスがthumbs_doneに戻っていること。
    """
    # Arrange
    video_path = tmp_path / "video.mp4"
    video_path.touch()

    repository.insert(
        Stream(
            video_id="video1",
            status=StreamStatus.THUMBS_DONE,
            title="Test Video",
            local_path=str(video_path),
        )
    )

    mock_provider = Mock()
    mock_provider.upload.side_effect = Exception("Upload failed")

    thumbnail_dir = tmp_path / "thumbnails"
    path_manager = PathManager(
        download_dir=tmp_path / "downloads",
        thumbnail_dir=thumbnail_dir,
        database_path=tmp_path / "test.db",
    )

    # Act
    success = UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_provider,
        gdrive_root_folder_id="folder_id",
        path_manager=path_manager,
        repository=repository,
    ).upload_video("video1", str(video_path))

    # Assert
    assert success is False
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.THUMBS_DONE


@pytest.mark.parametrize(
    "title,expected_filename",
    [
        pytest.param("Test Video Title", "Test Video Title.mp4", id="with_title"),
        pytest.param(None, "video_id.mp4", id="without_title"),
    ],
)
def test_upload_video_uses_correct_filename(
    repository: StreamRepository,
    tmp_path: Path,
    title: str | None,
    expected_filename: str,
) -> None:
    """upload_videoがタイトルに応じて正しいファイル名を使用すること.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        動画ファイルを作成する。
        GoogleDriveProviderをモックする。

    Act:
        タイトルを指定してupload_video()を呼び出す。

    Assert:
        タイトルありの場合はタイトルをファイル名として使用すること。
        タイトルなしの場合は元のファイル名を使用すること。
    """
    # Arrange
    video_path = tmp_path / "video_id.mp4"
    video_path.touch()

    repository.insert(
        Stream(
            video_id="video1",
            status=StreamStatus.THUMBS_DONE,
            title=title,
            local_path=str(video_path),
        )
    )

    mock_provider = Mock()
    thumbnail_dir = tmp_path / "thumbnails"
    path_manager = PathManager(
        download_dir=tmp_path / "downloads",
        thumbnail_dir=thumbnail_dir,
        database_path=tmp_path / "test.db",
    )

    # Act
    success = UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_provider,
        gdrive_root_folder_id="folder_id",
        path_manager=path_manager,
        repository=repository,
    ).upload_video("video1", str(video_path), title=title)

    # Assert
    assert success is True
    mock_provider.upload.assert_called_once_with(
        source_path=str(video_path),
        destination_filename=expected_filename,
    )
