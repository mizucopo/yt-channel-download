"""再ダウンロードコマンドのテスト."""

from pathlib import Path
from unittest.mock import patch

import pytest

from src.commands.redownload_command import RedownloadCommand
from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.repository.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo


def test_execute_resets_existing_video(repository: StreamRepository) -> None:
    """既存の動画が再ダウンロード用にリセットされること.

    Arrange:
        UPLOADEDステータスのストリームを登録する。

    Act:
        execute()を呼び出す。

    Assert:
        ステータスがDISCOVEREDにリセットされること。
        成功メッセージが表示されること。
    """
    # Arrange
    stream = Stream(
        video_id="test_video_id",
        status=StreamStatus.UPLOADED,
        title="Test Video",
    )
    repository.insert(stream)

    command = RedownloadCommand(repository)

    with patch("src.commands.redownload_command.click.echo") as mock_echo:
        # Act
        command.execute("test_video_id")

        # Assert
        # ステータスがリセットされていることを確認
        updated_stream = repository.get("test_video_id")
        assert updated_stream is not None
        assert updated_stream.status == StreamStatus.DISCOVERED

        # 成功メッセージが表示されること
        success_calls = [
            call
            for call in mock_echo.call_args_list
            if "reset for redownload" in str(call)
        ]
        assert len(success_calls) == 1


def test_execute_fails_when_video_not_found(repository: StreamRepository) -> None:
    """存在しない動画IDの場合に失敗すること.

    Arrange:
        何も登録しない。

    Act:
        存在しないvideo_idでexecute()を呼び出す。

    Assert:
        SystemExit(1)が発生すること。
    """
    # Arrange
    command = RedownloadCommand(repository)

    # Act & Assert
    with pytest.raises(SystemExit) as exc_info:
        command.execute("nonexistent_video_id")
    assert exc_info.value.code == 1


def test_execute_fails_when_reset_fails(repository: StreamRepository) -> None:
    """リセットに失敗した場合にSystemExitが発生すること.

    Arrange:
        リポジトリのreset_for_redownloadをモックしてFalseを返すようにする。
        getはストリームを返すようにモックする。

    Act:
        execute()を呼び出す。

    Assert:
        SystemExit(1)が発生すること。
    """
    # Arrange
    stream = Stream(
        video_id="test_video_id",
        status=StreamStatus.UPLOADED,
        title="Test Video",
    )
    repository.insert(stream)

    command = RedownloadCommand(repository)

    # reset_for_redownloadがFalseを返すようにモック
    with (
        patch.object(repository, "reset_for_redownload", return_value=False),
        pytest.raises(SystemExit) as exc_info,
    ):
        # Act
        command.execute("test_video_id")

        # Assert
        assert exc_info.value.code == 1
