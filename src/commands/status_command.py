"""ステータス表示コマンド."""

import click

from src.constants.stream_status import StreamStatus
from src.repository.stream_repository import StreamRepository


class StatusCommand:
    """ステータス表示コマンド."""

    def __init__(self, repository: StreamRepository) -> None:
        """コマンドを初期化する.

        Args:
            repository: ストリームリポジトリ
        """
        self._repository = repository

    def execute(self) -> None:
        """現在のステータスを表示する."""
        click.echo("Current status:")
        for status in StreamStatus:
            streams = self._repository.get_by_status(status)
            click.echo(f"  {status.value}: {len(streams)}")
