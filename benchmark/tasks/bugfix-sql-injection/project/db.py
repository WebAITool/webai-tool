"""User database with SQL injection vulnerability."""
import sqlite3
from typing import Optional, List, Dict


class UserDB:
    def __init__(self, db_path: str = ":memory:"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT
            )
        """)
        self.conn.commit()

    def add_user(self, username: str, password: str, email: str = "") -> int:
        # BUG: string formatting = SQL injection
        self.conn.execute(
            f"INSERT INTO users (username, password, email) VALUES ('{username}', '{password}', '{email}')"
        )
        self.conn.commit()
        return self.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def get_user(self, username: str) -> Optional[Dict]:
        # BUG: string formatting = SQL injection
        row = self.conn.execute(
            f"SELECT * FROM users WHERE username = '{username}'"
        ).fetchone()
        return dict(row) if row else None

    def verify_user(self, username: str, password: str) -> bool:
        # BUG: string formatting = SQL injection
        row = self.conn.execute(
            f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
        ).fetchone()
        return row is not None

    def delete_user(self, username: str) -> bool:
        # BUG: string formatting = SQL injection
        cursor = self.conn.execute(
            f"DELETE FROM users WHERE username = '{username}'"
        )
        self.conn.commit()
        return cursor.rowcount > 0

    def list_users(self) -> List[Dict]:
        rows = self.conn.execute("SELECT id, username, email FROM users").fetchall()
        return [dict(r) for r in rows]

    def close(self):
        self.conn.close()
