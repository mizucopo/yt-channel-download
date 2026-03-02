"""再ダウンロードコマンド."""

import click

from src.repository.stream_repository import StreamRepository


class RedownloadCommand:
    """再ダウンロードコマンド."""

    def __init__(self, repository: StreamRepository) -> None:
        """コマンドを初期化する.

        Args:
            repository: ストリームリポジトリ
        """
        self._repository = repository

    def execute(self, video_id: str) -> None:
        """指定された動画を再ダウンロード対象にする.

        Args:
            video_id: YouTube動画ID
        """
        stream = self._repository.get(video_id)
        if stream is None:
            click.echo(f"Error: Video {video_id} not found in database.", err=True)
            raise SystemExit(1)

        if self._repository.reset_for_redownload(video_id):
            click.echo(f"Video {video_id} has been reset for redownload.")
        else:
            click.echo(f"Error: Failed to reset video {video_id}.", err=True)
            raise SystemExit(1)
