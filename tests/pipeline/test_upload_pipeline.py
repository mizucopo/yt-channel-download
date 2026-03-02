"""Google Driveアップロードパイプラインのテスト."""

from pathlib import Path
from unittest.mock import Mock

from src.pipeline.upload_pipeline import UploadPipeline
from src.repository.stream_repository import StreamRepository


def test_upload_thumbnails_parallel_uploads_all_files(
    repository: StreamRepository, tmp_path: Path
) -> None:
    """_upload_thumbnails_parallelが全サムネイルを並列アップロードすること.

    Arrange:
        UploadPipelineを作成する。
        サムネイルファイルを準備する。
        GoogleDriveProviderをモックする。

    Act:
        _upload_thumbnails_parallel()を呼び出す。

    Assert:
        全てのサムネイルがアップロードされること。
    """
    # Arrange
    thumb_dir = tmp_path / "thumbnails" / "video1"
    thumb_dir.mkdir(parents=True)
    (thumb_dir / "thumb1.jpg").touch()
    (thumb_dir / "thumb2.jpg").touch()
    (thumb_dir / "thumb3.jpg").touch()

    thumb_files = sorted(thumb_dir.iterdir())

    mock_gdrive_provider = Mock()
    mock_path_manager = Mock()

    pipeline = UploadPipeline(
        max_retries=3,
        upload_parallel_workers=4,
        gdrive_provider=mock_gdrive_provider,
        gdrive_root_folder_id="root_folder_id",
        path_manager=mock_path_manager,
        repository=repository,
    )

    # Act
    pipeline._upload_thumbnails_parallel(list(thumb_files), "Test_Video")

    # Assert
    assert mock_gdrive_provider.upload.call_count == 3
    # 各ファイルが正しいdestination_filenameでアップロードされること
    calls = mock_gdrive_provider.upload.call_args_list
    destinations = [call[0][1] for call in calls]
    assert "Test_Video/thumb1.jpg" in destinations
    assert "Test_Video/thumb2.jpg" in destinations
    assert "Test_Video/thumb3.jpg" in destinations


def test_upload_thumbnails_parallel_propagates_exception(
    repository: StreamRepository, tmp_path: Path
) -> None:
    """_upload_thumbnails_parallelが例外を伝播させること.

    Arrange:
        UploadPipelineを作成する。
        サムネイルファイルを準備する。
        GoogleDriveProvider.uploadが例外を投げるようにモックする。

    Act:
        _upload_thumbnails_parallel()を呼び出す。

    Assert:
        例外が伝播されること。
    """
    # Arrange
    thumb_dir = tmp_path / "thumbnails" / "video1"
    thumb_dir.mkdir(parents=True)
    (thumb_dir / "thumb1.jpg").touch()

    thumb_files = list(thumb_dir.iterdir())

    mock_gdrive_provider = Mock()
    mock_gdrive_provider.upload.side_effect = Exception("Upload failed")
    mock_path_manager = Mock()

    pipeline = UploadPipeline(
        max_retries=3,
        upload_parallel_workers=4,
        gdrive_provider=mock_gdrive_provider,
        gdrive_root_folder_id="root_folder_id",
        path_manager=mock_path_manager,
        repository=repository,
    )

    # Act & Assert
    try:
        pipeline._upload_thumbnails_parallel(thumb_files, "Test_Video")
        raise AssertionError("Expected exception was not raised")
    except Exception as e:
        assert str(e) == "Upload failed"


def test_upload_parallel_workers_value_stored(
    repository: StreamRepository,
) -> None:
    """設定された並列数がインスタンスに保存されること.

    Arrange:
        なし

    Act:
        UploadPipelineを作成する（並列数=2）。

    Assert:
        _upload_parallel_workersが2であること。
    """
    # Arrange & Act
    mock_gdrive_provider = Mock()
    mock_path_manager = Mock()

    pipeline = UploadPipeline(
        max_retries=3,
        upload_parallel_workers=2,
        gdrive_provider=mock_gdrive_provider,
        gdrive_root_folder_id="root_folder_id",
        path_manager=mock_path_manager,
        repository=repository,
    )

    # Assert
    assert pipeline._upload_parallel_workers == 2


def test_upload_thumbnails_parallel_handles_empty_list(
    repository: StreamRepository,
) -> None:
    """_upload_thumbnails_parallelが空リストを正常に処理すること.

    Arrange:
        UploadPipelineを作成する。
        空のサムネイルファイルリストを準備する。

    Act:
        _upload_thumbnails_parallel()を空リストで呼び出す。

    Assert:
        uploadが呼び出されないこと。
    """
    # Arrange
    mock_gdrive_provider = Mock()
    mock_path_manager = Mock()

    pipeline = UploadPipeline(
        max_retries=3,
        upload_parallel_workers=4,
        gdrive_provider=mock_gdrive_provider,
        gdrive_root_folder_id="root_folder_id",
        path_manager=mock_path_manager,
        repository=repository,
    )

    # Act
    pipeline._upload_thumbnails_parallel([], "Test_Video")

    # Assert
    mock_gdrive_provider.upload.assert_not_called()
