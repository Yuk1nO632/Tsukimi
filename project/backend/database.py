"""Small SQLite store. Each operation opens and closes its own connection."""

from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time


class Database:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    token_hash TEXT PRIMARY KEY,
                    expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS favorites (
                    session_id TEXT NOT NULL REFERENCES sessions(token_hash) ON DELETE CASCADE,
                    anime_id TEXT NOT NULL,
                    created_at INTEGER NOT NULL,
                    PRIMARY KEY (session_id, anime_id)
                );
            """)

    def session_exists(self, token_hash: str) -> bool:
        with self.connect() as connection:
            return connection.execute(
                "SELECT 1 FROM sessions WHERE token_hash = ? AND expires_at > ?",
                (token_hash, int(time.time())),
            ).fetchone() is not None

    def create_session(self, token_hash: str, expires_at: int):
        with self.connect() as connection:
            connection.execute(
                "INSERT INTO sessions (token_hash, expires_at) VALUES (?, ?)",
                (token_hash, expires_at),
            )

    def list_favorites(self, session_id: str) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT anime_id FROM favorites WHERE session_id = ? ORDER BY created_at, anime_id",
                (session_id,),
            ).fetchall()
        return [row[0] for row in rows]

    def set_favorite(self, session_id: str, anime_id: str, saved: bool):
        # Parameters are bound separately from SQL; an ID is never interpolated into SQL.
        with self.connect() as connection:
            if saved:
                connection.execute(
                    "INSERT OR IGNORE INTO favorites (session_id, anime_id, created_at) VALUES (?, ?, ?)",
                    (session_id, anime_id, time.time_ns()),
                )
            else:
                connection.execute(
                    "DELETE FROM favorites WHERE session_id = ? AND anime_id = ?",
                    (session_id, anime_id),
                )
