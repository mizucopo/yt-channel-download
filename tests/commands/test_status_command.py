"""ステータス表示コマンドのテスト."""

from unittest.mock import patch

from src.commands.status_command import StatusCommand
from src.constants.stream_status import StreamStatus
from src.repository.stream_repository import StreamRepository


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
