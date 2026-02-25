"""ログ設定ユーティリティのテスト."""

import logging
from io import StringIO

from src.utils.logging_config import LoggingConfig


def test_setup_logging_configures_root_logger() -> None:
    """LoggingConfigがルートロガーを設定すること.

    Arrange:
        出力先としてStringIOを準備する。

    Act:
        LoggingConfigを初期化する。

    Assert:
        ルートロガーにハンドラーが追加されていること。
    """
    # Arrange
    stream = StringIO()

    # Act
    LoggingConfig(level=logging.DEBUG, stream=stream)

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
    logger = LoggingConfig.get_logger(name)

    # Assert
    assert logger.name == name
