"""SQLite persistence: anonymous sessions, collection states and public metadata cache."""
from contextlib import contextmanager
import json
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
                    token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL
                );
                CREATE TABLE IF NOT EXISTS favorites (
                    session_id TEXT NOT NULL REFERENCES sessions(token_hash) ON DELETE CASCADE,
                    anime_id TEXT NOT NULL, created_at INTEGER NOT NULL,
                    status TEXT NOT NULL DEFAULT 'wish', updated_at INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (session_id, anime_id)
                );
                CREATE TABLE IF NOT EXISTS catalog_cache (
                    anime_id TEXT PRIMARY KEY, data TEXT NOT NULL, fetched_at INTEGER NOT NULL
                );
            """)
            # Additive migration: existing favorites are kept and become "want to watch".
            columns = {row[1] for row in connection.execute("PRAGMA table_info(favorites)")}
            if "status" not in columns:
                connection.execute("ALTER TABLE favorites ADD COLUMN status TEXT NOT NULL DEFAULT 'wish'")
            if "updated_at" not in columns:
                connection.execute("ALTER TABLE favorites ADD COLUMN updated_at INTEGER NOT NULL DEFAULT 0")
            connection.execute("UPDATE favorites SET updated_at = CASE WHEN created_at > 1000000000000 THEN created_at / 1000000000 ELSE created_at END WHERE updated_at = 0")

    def session_exists(self, token_hash: str) -> bool:
        with self.connect() as connection:
            return connection.execute("SELECT 1 FROM sessions WHERE token_hash = ? AND expires_at > ?",
                                      (token_hash, int(time.time()))).fetchone() is not None

    def create_session(self, token_hash: str, expires_at: int):
        with self.connect() as connection:
            connection.execute("INSERT INTO sessions (token_hash, expires_at) VALUES (?, ?)", (token_hash, expires_at))

    def list_favorites(self, session_id: str) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute("SELECT anime_id FROM favorites WHERE session_id = ? ORDER BY created_at, anime_id", (session_id,)).fetchall()
        return [row[0] for row in rows]

    def set_favorite(self, session_id: str, anime_id: str, saved: bool):
        with self.connect() as connection:
            if saved:
                connection.execute("INSERT OR IGNORE INTO favorites (session_id, anime_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                                   (session_id, anime_id, time.time_ns(), int(time.time())))
            else:
                connection.execute("DELETE FROM favorites WHERE session_id = ? AND anime_id = ?", (session_id, anime_id))

    def set_collection_status(self, session_id: str, anime_id: str, status: str):
        with self.connect() as connection:
            connection.execute("""INSERT INTO favorites (session_id, anime_id, created_at, status, updated_at)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(session_id, anime_id)
                DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at""",
                (session_id, anime_id, time.time_ns(), status, int(time.time())))

    def list_collection(self, session_id: str):
        with self.connect() as connection:
            rows = connection.execute("""SELECT c.data, f.status, f.updated_at FROM favorites f
                JOIN catalog_cache c ON c.anime_id = f.anime_id WHERE f.session_id = ?
                ORDER BY f.updated_at DESC, f.created_at DESC, f.anime_id""", (session_id,)).fetchall()
        return [{"anime": json.loads(data), "status": status, "updated_at": updated_at} for data, status, updated_at in rows]

    def cache_anime(self, anime: dict, fetched_at: int, seed=False):
        with self.connect() as connection:
            values = (anime["id"], json.dumps(anime, ensure_ascii=False), fetched_at)
            if seed:
                connection.execute("INSERT OR IGNORE INTO catalog_cache VALUES (?, ?, ?)", values)
            else:
                connection.execute("""INSERT INTO catalog_cache VALUES (?, ?, ?)
                    ON CONFLICT(anime_id) DO UPDATE SET data = excluded.data, fetched_at = excluded.fetched_at""", values)

    def cached_anime(self, anime_id: str):
        with self.connect() as connection:
            row = connection.execute("SELECT data, fetched_at FROM catalog_cache WHERE anime_id = ?", (anime_id,)).fetchone()
        return (json.loads(row[0]), row[1]) if row else None
