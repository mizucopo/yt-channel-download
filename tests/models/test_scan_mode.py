"""ScanMode 値オブジェクトのテスト."""

from datetime import datetime, timedelta, timezone

from src.models.scan_mode import ScanMode


def test_get_published_after_returns_none_when_days_is_none() -> None:
    """days=Noneの場合、published_afterがNoneで返されること.

    Arrange:
        days=NoneでScanModeを作成する。

    Act:
        get_published_after()を呼び出す。

    Assert:
        Noneが返されること。
    """
    # Arrange
    scan_mode = ScanMode(days=None)

    # Act
    result = scan_mode.get_published_after()

    # Assert
    assert result is None


def test_get_published_after_returns_correct_datetime() -> None:
    """daysが指定された場合、正しい基準日時が返されること.

    Arrange:
        days=7でScanModeを作成する。

    Act:
        get_published_after()を呼び出す。

    Assert:
        現在時刻から7日前の日時が返されること。
        タイムゾーンがUTCであること。
    """
    # Arrange
    scan_mode = ScanMode(days=7)
    now = datetime.now(timezone.utc)

    # Act
    result = scan_mode.get_published_after()

    # Assert
    assert result is not None
    expected = now - timedelta(days=7)
    # 許容誤差1秒で比較
    delta = abs((result - expected).total_seconds())
    assert delta < 1.0
    assert result.tzinfo == timezone.utc
