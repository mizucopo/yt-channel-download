"""ログ設定ユーティリティのテスト."""

import io
import logging

from src.utils.logging import get_logger, setup_logging


def test_setup_logging_configures_root_logger() -> None:
    """setup_loggingがルートロガーを設定すること.

    Arrange:
        StringIOをストリームとして準備する。

    Act:
        setup_logging()を呼び出す。

    Assert:
        ルートロガーにハンドラーが追加されていること。
    """
    # Arrange
    stream = io.StringIO()

    # Act
    setup_logging(logging.DEBUG, stream)

    # Assert
    root_logger = logging.getLogger()
    assert len(root_logger.handlers) > 0


def test_get_logger_returns_logger_with_name() -> None:
    """get_loggerが指定した名前のロガーを返すこと.

    Arrange:
        テスト用のロガー名を準備する。

    Act:
        get_logger()を呼び出す。

    Assert:
        正しい名前のロガーが返されること。
    """
    # Arrange
    name = "test.module"

    # Act
    logger = get_logger(name)

    # Assert
    assert logger.name == name
