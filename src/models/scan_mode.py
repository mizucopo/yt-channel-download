"""スキャンモードの定義."""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class ScanMode:
    """スキャンモードを表す値オブジェクト.

    Attributes:
        days: None=フルスキャン（全期間）、N=過去N日分
    """

    days: int | None = None

    def get_published_after(self) -> datetime | None:
        """公開日時のフィルタ基準を取得する.

        Returns:
            フルスキャンの場合はNone、期間指定の場合は基準日時
        """
        if self.days is None:
            return None
        return datetime.now(timezone.utc) - timedelta(days=self.days)

    def is_full_scan(self) -> bool:
        """フルスキャンかどうかを判定する.

        Returns:
            フルスキャンの場合はTrue
        """
        return self.days is None
