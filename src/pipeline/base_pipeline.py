"""パイプライン基底クラス."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from src.constants.stream_status import StreamStatus
from src.models.stream import Stream
from src.repository.stream_repository import StreamRepository

logger = logging.getLogger(__name__)


class BasePipeline(ABC):
    """パイプラインの基底クラス.

    共通のリトライロジックとCAS更新パターンを提供する。
    """

    def __init__(
        self,
        max_retries: int,
        repository: StreamRepository,
    ) -> None:
        """パイプラインを初期化する.

        Args:
            max_retries: 最大リトライ回数
            repository: ストリームリポジトリ
        """
        self._max_retries = max_retries
        self._repository = repository

    @property
    def repository(self) -> StreamRepository:
        """リポジトリを取得する."""
        return self._repository

    @property
    def max_retries(self) -> int:
        """最大リトライ回数を取得する."""
        return self._max_retries

    def process_next(self) -> bool:
        """次の処理対象を処理する.

        Returns:
            処理対象があった場合はTrue
        """
        stream = self._repository.get_next_pending(
            self._get_pending_status(), self._max_retries
        )
        if stream is None:
            return False

        return self._process_single(stream.video_id, stream)

    def process_all(self) -> int:
        """すべての処理対象を処理する.

        Returns:
            処理に成功した件数
        """
        count = 0
        while True:
            if not self.process_next():
                break
            count += 1
        return count

    def _validate_file_exists(self, file_path: Path, video_id: str) -> bool:
        """ファイルの存在を検証する.

        Args:
            file_path: 検証するファイルパス
            video_id: 動画ID（ログ用）

        Returns:
            ファイルが存在する場合はTrue
        """
        if not file_path.exists():
            logger.warning("File not found for %s: %s", video_id, file_path)
            return False
        return True

    @staticmethod
    def truncate_error(message: str | None, max_length: int = 500) -> str:
        """エラーメッセージを切り詰める.

        完全なメッセージをログに記録し、DB保存用に切り詰めたメッセージを返す。

        Args:
            message: エラーメッセージ
            max_length: 最大文字数

        Returns:
            切り詰められたメッセージ
        """
        if not message:
            return "Unknown error"

        # 完全なエラーメッセージをログに記録
        if len(message) > max_length:
            logger.debug("Full error message (truncated for DB): %s", message)

        return message[:max_length]

    @abstractmethod
    def _get_pending_status(self) -> StreamStatus:
        """処理待ちステータスを取得する."""
        pass

    def _get_processing_status(self) -> StreamStatus:
        """処理中ステータスを取得する.

        デフォルトは処理待ちステータスと同じ（ロック取得をスキップ）。
        """
        return self._get_pending_status()

    @abstractmethod
    def _get_completed_status(self) -> StreamStatus:
        """完了ステータスを取得する."""
        pass

    @abstractmethod
    def _execute_process(self, video_id: str, stream: Stream) -> bool:
        """実際の処理を実行する.

        Args:
            video_id: 動画ID
            stream: ストリーム情報

        Returns:
            処理が成功した場合はTrue
        """
        pass

    def _rollback_on_failure(
        self, video_id: str, error_message: str | None = None
    ) -> None:
        """失敗時の巻き戻し処理.

        デフォルトは処理前ステータスに戻し、リトライカウントを増やす。
        処理中ステータスがない場合（processing_status == pending_status）は何もしない。

        Args:
            video_id: 動画ID
            error_message: エラーメッセージ
        """
        status_to_rollback = self._get_pending_status()
        processing_status = self._get_processing_status()
        if processing_status != status_to_rollback:
            self._repository.update_status(
                video_id,
                status_to_rollback,
                expected_old_status=processing_status,
                error_message=error_message,
                increment_retry=True,
            )

    def _process_single(self, video_id: str, stream: Stream) -> bool:
        """単一のストリームを処理する.

        テンプレートメソッドパターンで共通フローを提供する。

        Args:
            video_id: 動画ID
            stream: ストリーム情報

        Returns:
            処理が成功した場合はTrue
        """
        processing_status = self._get_processing_status()
        pending_status = self._get_pending_status()

        # ロック取得（処理中ステータスがある場合のみ）
        if processing_status != pending_status:
            updated = self._repository.update_status(
                video_id,
                processing_status,
                expected_old_status=pending_status,
            )
            if not updated:
                logger.warning("Failed to acquire lock: %s", video_id)
                return False

        try:
            success = self._execute_process(video_id, stream)
            if success:
                self._update_completed_status(video_id, processing_status)
                return True
            else:
                self._rollback_on_failure(video_id)
                return False
        except Exception as e:
            logger.exception("Process error: %s", video_id)
            self._rollback_on_failure(
                video_id, error_message=self.truncate_error(str(e))
            )
            return False

    def _update_completed_status(
        self, video_id: str, processing_status: StreamStatus
    ) -> None:
        """処理完了時のステータス更新.

        サブクラスで追加パラメータを設定するためにオーバーライド可能。

        Args:
            video_id: 動画ID
            processing_status: 処理中ステータス
        """
        self._repository.update_status(
            video_id,
            self._get_completed_status(),
            expected_old_status=processing_status,
        )
