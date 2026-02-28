"""Google Driveアップロードパイプラインのテスト."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.upload_pipeline import UploadPipeline
from src.repository.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


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

    # Act
    success = UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_provider,
        gdrive_root_folder_id="folder_id",
        thumbnail_dir=thumbnail_dir,
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
        destination_filename="video1/video.mp4",
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

    # Act
    success = UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_provider,
        gdrive_root_folder_id="folder_id",
        thumbnail_dir=thumbnail_dir,
        repository=repository,
    ).upload_video("video1", str(video_path))

    # Assert
    assert success is False
    result = repository.get("video1")
    assert result is not None
    assert result.status == StreamStatus.THUMBS_DONE


def test_upload_video_uses_youtube_title_as_filename(
    repository: StreamRepository, tmp_path: Path
) -> None:
    """upload_videoがYouTubeタイトルをファイル名として使用すること.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        動画ファイルを作成する。
        GoogleDriveProviderをモックする。

    Act:
        タイトルを指定してupload_video()を呼び出す。

    Assert:
        タイトルがファイル名として使用されていること。
    """
    # Arrange
    video_path = tmp_path / "video_id.mp4"
    video_path.touch()

    repository.insert(
        Stream(
            video_id="video1",
            status=StreamStatus.THUMBS_DONE,
            title="Test Video Title",
            local_path=str(video_path),
        )
    )

    mock_provider = Mock()
    thumbnail_dir = tmp_path / "thumbnails"

    # Act
    success = UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_provider,
        gdrive_root_folder_id="folder_id",
        thumbnail_dir=thumbnail_dir,
        repository=repository,
    ).upload_video("video1", str(video_path), title="Test Video Title")

    # Assert
    assert success is True
    mock_provider.upload.assert_called_once_with(
        source_path=str(video_path),
        destination_filename="Test Video Title/Test Video Title.mp4",
    )


def test_upload_video_fallback_to_original_filename_when_title_is_none(
    repository: StreamRepository, tmp_path: Path
) -> None:
    """upload_videoがタイトルなしの場合は元のファイル名を使用すること.

    Arrange:
        thumbs_doneステータスのストリームを登録する。
        動画ファイルを作成する。
        GoogleDriveProviderをモックする。

    Act:
        タイトルなしでupload_video()を呼び出す。

    Assert:
        元のファイル名が使用されていること。
    """
    # Arrange
    video_path = tmp_path / "video_id.mp4"
    video_path.touch()

    repository.insert(
        Stream(
            video_id="video1",
            status=StreamStatus.THUMBS_DONE,
            title=None,
            local_path=str(video_path),
        )
    )

    mock_provider = Mock()
    thumbnail_dir = tmp_path / "thumbnails"

    # Act
    success = UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_provider,
        gdrive_root_folder_id="folder_id",
        thumbnail_dir=thumbnail_dir,
        repository=repository,
    ).upload_video("video1", str(video_path), title=None)

    # Assert
    assert success is True
    mock_provider.upload.assert_called_once_with(
        source_path=str(video_path),
        destination_filename="video1/video_id.mp4",
    )


def test_sanitize_filename_replaces_invalid_characters() -> None:
    """_sanitize_filenameが禁止文字を置換すること.

    Arrange:
        禁止文字を含む文字列を用意する。

    Act:
        _sanitize_filename()を呼び出す。

    Assert:
        禁止文字がアンダースコアに置換されていること。
    """
    # Arrange
    invalid_name = 'Video: Test?"<>|\\/'

    # Act
    result = UploadPipeline._sanitize_filename(invalid_name)

    # Assert
    assert result == "Video_ Test_______"


def test_sanitize_filename_strips_leading_trailing_dots_and_spaces() -> None:
    """_sanitize_filenameが先頭末尾のドットとスペースを削除すること.

    Arrange:
        先頭と末尾にドットとスペースを持つ文字列を用意する。

    Act:
        _sanitize_filename()を呼び出す。

    Assert:
        先頭末尾のドットとスペースが削除されていること。
    """
    # Arrange
    name_with_dots = " .Test Video. "

    # Act
    result = UploadPipeline._sanitize_filename(name_with_dots)

    # Assert
    assert result == "Test Video"


def test_sanitize_filename_returns_untitled_for_empty_result() -> None:
    """_sanitize_filenameが空の結果の場合はuntitledを返すこと.

    Arrange:
        空文字列または削除後に空になる文字列を用意する。

    Act:
        _sanitize_filename()を呼び出す。

    Assert:
        untitledが返されること。
    """
    # Arrange & Act & Assert
    assert UploadPipeline._sanitize_filename("") == "untitled"
    assert UploadPipeline._sanitize_filename("...") == "untitled"
    assert UploadPipeline._sanitize_filename("   ") == "untitled"


def test_generate_gdrive_filename_preserves_extension(
    repository: StreamRepository, tmp_path: Path
) -> None:
    """_generate_gdrive_filenameが拡張子を維持すること.

    Arrange:
        UploadPipelineインスタンスを作成する。
        拡張子付きのパスを用意する。

    Act:
        _generate_gdrive_filename()を呼び出す。

    Assert:
        拡張子が維持されていること。
    """
    # Arrange
    mock_provider = Mock()
    thumbnail_dir = tmp_path / "thumbnails"
    original_path = Path("/some/path/video.webm")

    pipeline = UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_provider,
        gdrive_root_folder_id="folder_id",
        thumbnail_dir=thumbnail_dir,
        repository=repository,
    )

    # Act
    result = pipeline._generate_gdrive_filename("Test Title", original_path)

    # Assert
    assert result == "Test Title.webm"
