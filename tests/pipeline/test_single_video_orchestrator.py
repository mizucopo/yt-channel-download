"""SingleVideoOrchestratorのテスト."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.pipeline.cleanup_pipeline import CleanupPipeline
from src.pipeline.download_pipeline import DownloadPipeline
from src.pipeline.single_video_orchestrator import SingleVideoOrchestrator
from src.pipeline.thumbs_pipeline import ThumbsPipeline
from src.pipeline.upload_pipeline import UploadPipeline
from src.repository.stream_repository import StreamRepository
from src.utils.path_manager import PathManager


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


@pytest.fixture
def download_pipeline(repository: StreamRepository, tmp_path: Path) -> DownloadPipeline:
    """テスト用ダウンロードパイプラインを作成する."""
    return DownloadPipeline(
        max_retries=3,
        download_dir=tmp_path / "downloads",
        repository=repository,
    )


@pytest.fixture
def path_manager(tmp_path: Path) -> PathManager:
    """テスト用パスマネージャを作成する."""
    return PathManager(
        download_dir=tmp_path / "downloads",
        thumbnail_dir=tmp_path / "thumbnails",
        database_path=tmp_path / "test.db",
    )


@pytest.fixture
def thumbs_pipeline(
    repository: StreamRepository, path_manager: PathManager
) -> ThumbsPipeline:
    """テスト用サムネイル抽出パイプラインを作成する."""
    return ThumbsPipeline(
        max_retries=3,
        thumbnail_interval=60,
        thumbnail_quality=2,
        path_manager=path_manager,
        repository=repository,
    )


@pytest.fixture
def upload_pipeline(
    repository: StreamRepository, path_manager: PathManager
) -> UploadPipeline:
    """テスト用アップロードパイプラインを作成する."""
    mock_provider = Mock()
    return UploadPipeline(
        max_retries=3,
        gdrive_provider=mock_provider,
        gdrive_root_folder_id="root_folder_id",
        path_manager=path_manager,
        repository=repository,
    )


@pytest.fixture
def cleanup_pipeline(
    repository: StreamRepository, tmp_path: Path, path_manager: PathManager
) -> CleanupPipeline:
    """テスト用クリーンアップパイプラインを作成する."""
    return CleanupPipeline(
        max_retries=3,
        download_dir=tmp_path / "downloads",
        path_manager=path_manager,
        repository=repository,
    )


def test_process_single_video_completes_all_stages(
    repository: StreamRepository,
    download_pipeline: DownloadPipeline,
    thumbs_pipeline: ThumbsPipeline,
    upload_pipeline: UploadPipeline,
    cleanup_pipeline: CleanupPipeline,
    tmp_path: Path,
) -> None:
    """process_single_videoが全ステージを完了すること.

    Arrange:
        discoveredステータスのストリームを登録する。
        各パイプラインをモックして成功を返す。
        動画ファイルとサムネイルディレクトリを作成する。

    Act:
        process_single_video()を呼び出す。

    Assert:
        ステータスがcleanedに更新されていること。
    """
    # Arrange
    video_id = "video1"
    repository.insert(
        Stream(video_id=video_id, status=StreamStatus.DISCOVERED, title="Test Video")
    )

    download_dir = tmp_path / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)
    video_file = download_dir / f"{video_id}.webm"
    video_file.touch()

    thumbnail_dir = tmp_path / "thumbnails" / video_id
    thumbnail_dir.mkdir(parents=True, exist_ok=True)

    # subprocess.runをモック
    mock_download_result = Mock()
    mock_download_result.returncode = 0
    mock_download_result.stderr = ""
    mock_download_result.stdout = str(video_file)

    mock_thumbs_result = Mock()
    mock_thumbs_result.returncode = 0
    mock_thumbs_result.stderr = ""

    orchestrator = SingleVideoOrchestrator(
        repository=repository,
        download_pipeline=download_pipeline,
        thumbs_pipeline=thumbs_pipeline,
        upload_pipeline=upload_pipeline,
        cleanup_pipeline=cleanup_pipeline,
        max_retries=3,
    )

    with (
        patch("subprocess.run", side_effect=[mock_download_result, mock_thumbs_result]),
        patch.object(upload_pipeline._gdrive_provider, "upload"),
    ):
        # Act
        result = orchestrator.process_single_video()

    # Assert
    assert result is True
    stream = repository.get(video_id)
    assert stream is not None
    assert stream.status == StreamStatus.CLEANED


def test_process_single_video_stops_on_download_failure(
    repository: StreamRepository,
    download_pipeline: DownloadPipeline,
    thumbs_pipeline: ThumbsPipeline,
    upload_pipeline: UploadPipeline,
    cleanup_pipeline: CleanupPipeline,
) -> None:
    """process_single_videoがダウンロード失敗時に次の動画へ進むこと.

    Arrange:
        discoveredステータスのストリームを登録する。
        subprocess.runをモックしてダウンロード失敗を返す。

    Act:
        process_single_video()を呼び出す。

    Assert:
        ステータスがdiscoveredのままであること。
        処理対象があったためTrueが返されること。
    """
    # Arrange
    video_id = "video1"
    repository.insert(
        Stream(video_id=video_id, status=StreamStatus.DISCOVERED, title="Test Video")
    )

    mock_result = Mock()
    mock_result.returncode = 1
    mock_result.stderr = "Download failed"
    mock_result.stdout = ""

    orchestrator = SingleVideoOrchestrator(
        repository=repository,
        download_pipeline=download_pipeline,
        thumbs_pipeline=thumbs_pipeline,
        upload_pipeline=upload_pipeline,
        cleanup_pipeline=cleanup_pipeline,
        max_retries=3,
    )

    with patch("subprocess.run", return_value=mock_result):
        # Act
        result = orchestrator.process_single_video()

    # Assert
    assert result is True  # 処理対象はあった
    stream = repository.get(video_id)
    assert stream is not None
    assert stream.status == StreamStatus.DISCOVERED
    assert stream.retry_count == 1


def test_process_single_video_returns_false_when_no_videos(
    repository: StreamRepository,
    download_pipeline: DownloadPipeline,
    thumbs_pipeline: ThumbsPipeline,
    upload_pipeline: UploadPipeline,
    cleanup_pipeline: CleanupPipeline,
) -> None:
    """process_single_videoが処理対象なし時にFalseを返すこと.

    Arrange:
        ストリームを登録しない。

    Act:
        process_single_video()を呼び出す。

    Assert:
        Falseが返されること。
    """
    # Arrange
    orchestrator = SingleVideoOrchestrator(
        repository=repository,
        download_pipeline=download_pipeline,
        thumbs_pipeline=thumbs_pipeline,
        upload_pipeline=upload_pipeline,
        cleanup_pipeline=cleanup_pipeline,
        max_retries=3,
    )

    # Act
    result = orchestrator.process_single_video()

    # Assert
    assert result is False


def test_process_all_videos_processes_multiple_videos(
    repository: StreamRepository,
    download_pipeline: DownloadPipeline,
    thumbs_pipeline: ThumbsPipeline,
    upload_pipeline: UploadPipeline,
    cleanup_pipeline: CleanupPipeline,
    tmp_path: Path,
) -> None:
    """process_all_videosが複数動画を処理すること.

    Arrange:
        2つのdiscoveredステータスのストリームを登録する。
        各パイプラインをモックして成功を返す。

    Act:
        process_all_videos()を呼び出す。

    Assert:
        2つの動画が処理されること。
    """
    # Arrange
    download_dir = tmp_path / "downloads"
    download_dir.mkdir(parents=True, exist_ok=True)

    for i in range(1, 3):
        video_id = f"video{i}"
        repository.insert(
            Stream(
                video_id=video_id,
                status=StreamStatus.DISCOVERED,
                title=f"Test Video {i}",
            )
        )
        video_file = download_dir / f"{video_id}.webm"
        video_file.touch()

    # モックを準備
    mock_results = []
    for i in range(1, 3):
        video_file = download_dir / f"video{i}.webm"
        mock_download = Mock()
        mock_download.returncode = 0
        mock_download.stderr = ""
        mock_download.stdout = str(video_file)
        mock_results.append(mock_download)

        mock_thumbs = Mock()
        mock_thumbs.returncode = 0
        mock_thumbs.stderr = ""
        mock_results.append(mock_thumbs)

    orchestrator = SingleVideoOrchestrator(
        repository=repository,
        download_pipeline=download_pipeline,
        thumbs_pipeline=thumbs_pipeline,
        upload_pipeline=upload_pipeline,
        cleanup_pipeline=cleanup_pipeline,
        max_retries=3,
    )

    with (
        patch("subprocess.run", side_effect=mock_results),
        patch.object(upload_pipeline._gdrive_provider, "upload"),
    ):
        # Act
        count = orchestrator.process_all_videos()

    # Assert
    assert count == 2
    for i in range(1, 3):
        stream = repository.get(f"video{i}")
        assert stream is not None
        assert stream.status == StreamStatus.CLEANED
