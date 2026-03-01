"""テスト用共通フィクスチャ."""

from pathlib import Path

import pytest

from src.repository.stream_repository import StreamRepository


@pytest.fixture
def repository(tmp_path: Path) -> StreamRepository:
    """テスト用リポジトリを作成する."""
    db_path = tmp_path / "test.db"
    repo = StreamRepository(db_path)
    repo.init_db()
    return repo
