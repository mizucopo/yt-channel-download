"""ストリームリポジトリ.

SQLiteを使用してストリーム情報を管理する。
"""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models.stream import Stream
from src.models.stream_status import StreamStatus


class StreamRepository:
    """ストリーム情報のリポジトリ."""

    def __init__(self, database_path: Path) -> None:
        """リポジトリを初期化する.

        Args:
            database_path: データベースファイルのパス
        """
        self._database_path = database_path

    def _get_connection(self) -> sqlite3.Connection:
        """データベース接続を取得する.

        Returns:
            SQLite接続オブジェクト
        """
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self._database_path))
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """データベースを初期化する.

        streamsテーブルが存在しない場合は作成する。
        """
        conn = self._get_connection()
        try:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS streams (
                    video_id TEXT PRIMARY KEY,
                    status TEXT NOT NULL DEFAULT 'discovered',
                    title TEXT,
                    published_at TEXT,
                    local_path TEXT,
                    gdrive_file_id TEXT,
                    gdrive_file_name TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def _row_to_stream(row: sqlite3.Row) -> Stream:
        """データベース行をStreamオブジェクトに変換する.

        Args:
            row: SQLiteの行オブジェクト

        Returns:
            Streamオブジェクト
        """
        return Stream(
            video_id=row["video_id"],
            status=StreamStatus(row["status"]),
            title=row["title"],
            published_at=row["published_at"],
            local_path=row["local_path"],
            gdrive_file_id=row["gdrive_file_id"],
            gdrive_file_name=row["gdrive_file_name"],
            error_message=row["error_message"],
            retry_count=row["retry_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def insert(self, stream: Stream) -> None:
        """新しいストリームを登録する.

        Args:
            stream: 登録するストリーム情報
        """
        conn = self._get_connection()
        try:
            now = datetime.now().isoformat()
            conn.execute(
                """
                INSERT INTO streams (
                    video_id, status, title, published_at,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    stream.video_id,
                    stream.status.value,
                    stream.title,
                    stream.published_at,
                    now,
                    now,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get(self, video_id: str) -> Stream | None:
        """指定されたvideo_idのストリームを取得する.

        Args:
            video_id: YouTube動画ID

        Returns:
            ストリーム情報（存在しない場合はNone）
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM streams WHERE video_id = ?",
                (video_id,),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_stream(row)
        finally:
            conn.close()

    def get_by_status(self, status: StreamStatus) -> list[Stream]:
        """指定されたステータスのストリーム一覧を取得する.

        Args:
            status: ステータス値

        Returns:
            ストリームのリスト
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM streams WHERE status = ? ORDER BY published_at DESC",
                (status.value,),
            )
            rows = cursor.fetchall()
            return [self._row_to_stream(row) for row in rows]
        finally:
            conn.close()

    def update_status(
        self,
        video_id: str,
        new_status: StreamStatus,
        *,
        expected_old_status: StreamStatus | None = None,
        local_path: str | None = None,
        gdrive_file_id: str | None = None,
        gdrive_file_name: str | None = None,
        error_message: str | None = None,
        increment_retry: bool = False,
    ) -> bool:
        """ストリームのステータスを更新する（CAS更新）.

        Args:
            video_id: YouTube動画ID
            new_status: 新しいステータス
            expected_old_status: 期待される現在のステータス（指定時はCAS更新）
            local_path: ローカルパス
            gdrive_file_id: Google DriveファイルID
            gdrive_file_name: Google Driveファイル名
            error_message: エラーメッセージ
            increment_retry: リトライカウントを増やすかどうか

        Returns:
            更新が成功した場合はTrue、失敗した場合はFalse
        """
        conn = self._get_connection()
        try:
            now = datetime.now().isoformat()

            # 動的SQLを構築
            updates: list[str] = ["status = ?", "updated_at = ?"]
            params: list[Any] = [new_status.value, now]

            if local_path is not None:
                updates.append("local_path = ?")
                params.append(local_path)

            if gdrive_file_id is not None:
                updates.append("gdrive_file_id = ?")
                params.append(gdrive_file_id)

            if gdrive_file_name is not None:
                updates.append("gdrive_file_name = ?")
                params.append(gdrive_file_name)

            if error_message is not None:
                updates.append("error_message = ?")
                params.append(error_message)

            if increment_retry:
                updates.append("retry_count = retry_count + 1")

            params.append(video_id)

            sql = f"UPDATE streams SET {', '.join(updates)} WHERE video_id = ?"  # noqa: S608

            if expected_old_status is not None:
                sql += " AND status = ?"
                params.append(expected_old_status.value)

            cursor = conn.execute(sql, params)
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    def get_next_pending(self, status: StreamStatus, max_retries: int) -> Stream | None:
        """次の処理対象を取得する.

        リトライ回数が上限に達していないストリームを取得する。

        Args:
            status: 取得するステータス
            max_retries: 最大リトライ回数

        Returns:
            次の処理対象（存在しない場合はNone）
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                SELECT * FROM streams
                WHERE status = ? AND retry_count < ?
                ORDER BY created_at ASC
                LIMIT 1
                """,
                (status.value, max_retries),
            )
            row = cursor.fetchone()
            if row is None:
                return None
            return self._row_to_stream(row)
        finally:
            conn.close()

    def is_empty(self) -> bool:
        """ストリームテーブルが空かどうかを判定する.

        Returns:
            テーブルが空の場合はTrue、レコードが存在する場合はFalse
        """
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT COUNT(*) FROM streams")
            count = cursor.fetchone()[0]
            return int(count) == 0
        finally:
            conn.close()
