"""ステータス表示コマンドのテスト."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.commands.status_command import StatusCommand
from src.constants.stream_status import StreamStatus
from src.repository.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


def test_execute_displays_all_stream_statuses(repository: StreamRepository) -> None:
    """全ステータスのストリーム数が表示されること.

    Arrange:
        各ステータスのストリームを登録する。
        click.echoをモックする。

    Act:
        execute()を呼び出す。

    Assert:
        各ステータスの件数が出力されること。
    """
    # Arrange
    from src.models.stream import Stream

    # 各ステータスにストリームを追加
    stream1 = Stream(
        video_id="video1",
        status=StreamStatus.DISCOVERED,
        title="Test Video 1",
    )
    stream2 = Stream(
        video_id="video2",
        status=StreamStatus.DOWNLOADED,
        title="Test Video 2",
    )
    stream3 = Stream(
        video_id="video3",
        status=StreamStatus.DISCOVERED,
        title="Test Video 3",
    )
    repository.insert(stream1)
    repository.insert(stream2)
    repository.insert(stream3)

    command = StatusCommand(repository)

    with patch("src.commands.status_command.click.echo") as mock_echo:
        # Act
        command.execute()

        # Assert
        # "Current status:" + 各ステータスの行が出力される
        assert mock_echo.call_count == len(StreamStatus) + 1
        # 最初の呼び出しが "Current status:" であること
        assert mock_echo.call_args_list[0][0][0] == "Current status:"

        # discoveredが2件であることを確認
        discovered_call = next(
            call
            for call in mock_echo.call_args_list
            if "discovered" in str(call) and "2" in str(call)
        )
        assert discovered_call is not None


def test_execute_shows_zero_for_empty_status(repository: StreamRepository) -> None:
    """ストリームが存在しないステータスは0と表示されること.

    Arrange:
        何も登録しない（空の状態）。
        click.echoをモックする。

    Act:
        execute()を呼び出す。

    Assert:
        各ステータスが0件と表示されること。
    """
    # Arrange
    command = StatusCommand(repository)

    with patch("src.commands.status_command.click.echo") as mock_echo:
        # Act
        command.execute()

        # Assert
        # 全ステータスが0件であることを確認
        for status in StreamStatus:
            status_call = next(
                call for call in mock_echo.call_args_list if status.value in str(call)
            )
            assert f"{status.value}: 0" in str(status_call)


def test_execute_shows_count_for_streams(repository: StreamRepository) -> None:
    """ストリーム数が正しくカウントされること.

    Arrange:
        同じステータスに複数のストリームを登録する。
        click.echoをモックする。

    Act:
        execute()を呼び出す。

    Assert:
        正しい件数が表示されること。
    """
    # Arrange
    from src.models.stream import Stream

    # UPLOADEDステータスに3件登録
    for i in range(3):
        stream = Stream(
            video_id=f"video{i}",
            status=StreamStatus.UPLOADED,
            title=f"Test Video {i}",
        )
        repository.insert(stream)

    command = StatusCommand(repository)

    with patch("src.commands.status_command.click.echo") as mock_echo:
        # Act
        command.execute()

        # Assert
        # UPLOADEDが3件であることを確認
        uploaded_call = next(
            call
            for call in mock_echo.call_args_list
            if StreamStatus.UPLOADED.value in str(call) and "3" in str(call)
        )
        assert uploaded_call is not None
