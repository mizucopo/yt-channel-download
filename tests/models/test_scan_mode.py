"""ScanMode 値オブジェクトのテスト."""

from datetime import datetime, timedelta, timezone

from src.models.scan_mode import ScanMode


def test_is_full_scan_returns_true_when_days_is_none() -> None:
    """days=Noneの場合、フルスキャンとして判定されること.

    Arrange:
        days=NoneでScanModeを作成する。

    Act:
        is_full_scan()を呼び出す。

    Assert:
        Trueが返されること。
    """
    # Arrange
    scan_mode = ScanMode(days=None)

    # Act
    result = scan_mode.is_full_scan()

    # Assert
    assert result is True


def test_is_full_scan_returns_false_when_days_is_specified() -> None:
    """daysが指定された場合、フルスキャンではないと判定されること.

    Arrange:
        days=7でScanModeを作成する。

    Act:
        is_full_scan()を呼び出す。

    Assert:
        Falseが返されること。
    """
    # Arrange
    scan_mode = ScanMode(days=7)

    # Act
    result = scan_mode.is_full_scan()

    # Assert
    assert result is False


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


def test_scan_mode_is_frozen_dataclass() -> None:
    """ScanModeが不変であること.

    Arrange:
        ScanModeのインスタンスを作成する。

    Act & Assert:
        属性を変更しようとするとエラーが発生すること。
    """
    # Arrange
    scan_mode = ScanMode(days=7)

    # Act & Assert
    try:
        scan_mode.days = 14  # type: ignore[misc]
        raise AssertionError("Should not reach here")
    except AttributeError, TypeError:
        pass  # Expected behavior for frozen dataclass
