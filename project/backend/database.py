"""SQLite persistence for anonymous/account libraries and public metadata."""
from contextlib import closing, contextmanager
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
        # A one-time SQLite backup precedes the additive account migration.
        backup = self.path.with_suffix(".pre-accounts.db")
        if self.path.exists() and not backup.exists():
            with closing(sqlite3.connect(self.path)) as source:
                if source.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='owners'").fetchone() is None:
                    with closing(sqlite3.connect(backup)) as destination:
                        source.backup(destination)
        progress_backup = self.path.with_suffix(".pre-source-providers.db")
        if self.path.exists() and not progress_backup.exists():
            with closing(sqlite3.connect(self.path)) as source:
                columns = {row[1] for row in source.execute("PRAGMA table_info(watch_progress)")}
                if columns and "source_provider" not in columns:
                    with closing(sqlite3.connect(progress_backup)) as destination:
                        source.backup(destination)
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
                CREATE TABLE IF NOT EXISTS source_bindings (
                    session_id TEXT NOT NULL REFERENCES sessions(token_hash) ON DELETE CASCADE,
                    anime_id TEXT NOT NULL, source_id INTEGER NOT NULL,
                    PRIMARY KEY (session_id, anime_id)
                );
                CREATE TABLE IF NOT EXISTS auto_source_bindings (
                    anime_id TEXT PRIMARY KEY, source_id INTEGER NOT NULL, matched_at INTEGER NOT NULL
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

            self._initialize_accounts(connection)

    def _initialize_accounts(self, connection):
        # Add new tables and copy legacy records once. Legacy tables are retained.
        connection.execute("CREATE TABLE IF NOT EXISTS owners (id TEXT PRIMARY KEY)")
        columns = {row[1] for row in connection.execute("PRAGMA table_info(sessions)")}
        if "owner_id" not in columns:
            connection.execute("ALTER TABLE sessions ADD COLUMN owner_id TEXT REFERENCES owners(id)")
        connection.execute("INSERT OR IGNORE INTO owners SELECT token_hash FROM sessions WHERE owner_id IS NULL")
        connection.execute("UPDATE sessions SET owner_id = token_hash WHERE owner_id IS NULL")
        statements = [
            """CREATE TABLE IF NOT EXISTS owned_favorites (
                owner_id TEXT NOT NULL REFERENCES owners(id), anime_id TEXT NOT NULL,
                created_at INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'wish', updated_at INTEGER NOT NULL,
                PRIMARY KEY(owner_id, anime_id))""",
            """CREATE TABLE IF NOT EXISTS owned_source_bindings (
                owner_id TEXT NOT NULL REFERENCES owners(id), anime_id TEXT NOT NULL, source_id INTEGER NOT NULL,
                PRIMARY KEY(owner_id, anime_id))""",
            """CREATE TABLE IF NOT EXISTS playback_preferences (
                owner_id TEXT NOT NULL REFERENCES owners(id), anime_id TEXT NOT NULL,
                provider TEXT NOT NULL, PRIMARY KEY(owner_id, anime_id))""",
            """CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY REFERENCES owners(id), email TEXT NOT NULL UNIQUE,
                nickname TEXT NOT NULL, password_hash TEXT NOT NULL, created_at INTEGER NOT NULL)""",
            """CREATE TABLE IF NOT EXISTS watch_progress (
                owner_id TEXT NOT NULL REFERENCES owners(id), anime_id TEXT NOT NULL,
                episode INTEGER NOT NULL, position REAL NOT NULL, duration REAL NOT NULL,
                source_id INTEGER, line_id INTEGER, completed INTEGER NOT NULL DEFAULT 0,
                revision INTEGER NOT NULL, updated_at INTEGER NOT NULL, operation_id TEXT NOT NULL, source_provider TEXT NOT NULL DEFAULT 'anich',
                PRIMARY KEY(owner_id, anime_id))""",
            """CREATE TABLE IF NOT EXISTS email_codes (
                email TEXT NOT NULL, purpose TEXT NOT NULL, digest TEXT NOT NULL,
                expires_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0,
                sent_at INTEGER NOT NULL, generation TEXT NOT NULL, PRIMARY KEY(email, purpose))""",
            "CREATE TABLE IF NOT EXISTS app_secrets (name TEXT PRIMARY KEY, value TEXT NOT NULL)",
            "CREATE TABLE IF NOT EXISTS rate_limits (bucket TEXT PRIMARY KEY, started_at INTEGER NOT NULL, count INTEGER NOT NULL)",
            "CREATE TABLE IF NOT EXISTS migrations (name TEXT PRIMARY KEY)",
            """CREATE TABLE IF NOT EXISTS pending_imports (
                token_hash TEXT PRIMARY KEY REFERENCES sessions(token_hash) ON DELETE CASCADE,
                anonymous_owner TEXT NOT NULL REFERENCES owners(id))""",
            "CREATE INDEX IF NOT EXISTS sessions_owner ON sessions(owner_id)",
        ]
        for statement in statements:
            connection.execute(statement)
        if connection.execute("SELECT 1 FROM migrations WHERE name = 'account_owners'").fetchone() is None:
            connection.execute("INSERT OR IGNORE INTO owned_favorites SELECT * FROM favorites")
            connection.execute("INSERT OR IGNORE INTO owned_source_bindings SELECT * FROM source_bindings")
            connection.execute("INSERT INTO migrations VALUES ('account_owners')")

        columns = {row[1] for row in connection.execute("PRAGMA table_info(watch_progress)")}
        if "source_provider" not in columns:
            connection.execute("ALTER TABLE watch_progress ADD COLUMN source_provider TEXT NOT NULL DEFAULT 'anich'")

        columns = {row[1] for row in connection.execute("PRAGMA table_info(users)")}
        if "username" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN username TEXT")
        if "security_json" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN security_json TEXT NOT NULL DEFAULT '[]'")
        connection.execute("UPDATE users SET username = email WHERE username IS NULL")
        if "role" not in columns:
            connection.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
        connection.execute("CREATE UNIQUE INDEX IF NOT EXISTS users_username ON users(username)")
        connection.execute("""CREATE TABLE IF NOT EXISTS recovery_challenges (
            token_hash TEXT PRIMARY KEY, session_hash TEXT NOT NULL REFERENCES sessions(token_hash) ON DELETE CASCADE,
            username TEXT NOT NULL, user_id TEXT, credential_version TEXT NOT NULL,
            expires_at INTEGER NOT NULL, attempts INTEGER NOT NULL DEFAULT 0)""")

    def user(self, owner_id):
        with self.connect() as connection:
            row = connection.execute("SELECT id, username, nickname, security_json, role FROM users WHERE id = ?", (owner_id,)).fetchone()
        if not row:
            return None
        return {"id": row[0], "username": row[1], "nickname": row[2], "security_configured": bool(json.loads(row[3])), "role": row[4]}

    def progress(self, owner_id, anime_id):
        with self.connect() as connection:
            return self.progress_row(connection, owner_id, anime_id)

    @staticmethod
    def progress_row(connection, owner_id, anime_id):
        cursor = connection.execute("SELECT * FROM watch_progress WHERE owner_id = ? AND anime_id = ?", (owner_id, anime_id))
        row = cursor.fetchone()
        if row is None:
            return None
        return {column[0]: value for column, value in zip(cursor.description, row) if column[0] != "owner_id"}

    def list_progress(self, owner_id):
        with self.connect() as connection:
            rows = connection.execute("""SELECT p.anime_id, c.data FROM watch_progress p
                JOIN catalog_cache c ON c.anime_id = p.anime_id WHERE p.owner_id = ?
                ORDER BY p.updated_at DESC LIMIT 30""", (owner_id,)).fetchall()
            return [{**self.progress_row(connection, owner_id, anime_id), "anime": json.loads(data)} for anime_id, data in rows]

    def session_owner(self, token_hash):
        with self.connect() as connection:
            row = connection.execute("SELECT owner_id FROM sessions WHERE token_hash = ? AND expires_at > ?",
                                     (token_hash, int(time.time()))).fetchone()
        return row[0] if row else None

    def session_exists(self, token_hash):
        return self.session_owner(token_hash) is not None

    def create_session(self, token_hash, expires_at, owner_id=None):
        owner_id = owner_id or token_hash
        with self.connect() as connection:
            connection.execute("INSERT OR IGNORE INTO owners VALUES (?)", (owner_id,))
            connection.execute("INSERT INTO sessions (token_hash, expires_at, owner_id) VALUES (?, ?, ?)",
                               (token_hash, expires_at, owner_id))

    def list_favorites(self, owner_id: str) -> list[str]:
        with self.connect() as connection:
            rows = connection.execute("SELECT anime_id FROM owned_favorites WHERE owner_id = ? ORDER BY created_at, anime_id", (owner_id,)).fetchall()
        return [row[0] for row in rows]

    def set_favorite(self, owner_id: str, anime_id: str, saved: bool):
        with self.connect() as connection:
            if saved:
                connection.execute("INSERT OR IGNORE INTO owned_favorites (owner_id, anime_id, created_at, updated_at) VALUES (?, ?, ?, ?)",
                                   (owner_id, anime_id, time.time_ns(), int(time.time())))
            else:
                connection.execute("DELETE FROM owned_favorites WHERE owner_id = ? AND anime_id = ?", (owner_id, anime_id))

    def set_collection_status(self, owner_id: str, anime_id: str, status: str):
        with self.connect() as connection:
            connection.execute("""INSERT INTO owned_favorites (owner_id, anime_id, created_at, status, updated_at)
                VALUES (?, ?, ?, ?, ?) ON CONFLICT(owner_id, anime_id)
                DO UPDATE SET status = excluded.status, updated_at = excluded.updated_at""",
                (owner_id, anime_id, time.time_ns(), status, int(time.time())))

    def list_collection(self, owner_id: str):
        with self.connect() as connection:
            rows = connection.execute("""SELECT c.data, f.status, f.updated_at FROM owned_favorites f
                JOIN catalog_cache c ON c.anime_id = f.anime_id WHERE f.owner_id = ?
                ORDER BY f.updated_at DESC, f.created_at DESC, f.anime_id""", (owner_id,)).fetchall()
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

    def cache_animes(self, items, fetched_at):
        with self.connect() as connection:
            connection.executemany("""INSERT INTO catalog_cache VALUES (?, ?, ?)
                ON CONFLICT(anime_id) DO UPDATE SET data = excluded.data, fetched_at = excluded.fetched_at
                WHERE COALESCE(json_extract(catalog_cache.data, '$.detailComplete'), 0) != 1
                   OR COALESCE(json_extract(excluded.data, '$.detailComplete'), 0) = 1""",
                [(anime["id"], json.dumps(anime, ensure_ascii=False), fetched_at) for anime in items])

    def source_binding(self, anime_id, owner_id=None):
        with self.connect() as connection:
            if owner_id:
                saved = connection.execute("SELECT source_id FROM owned_source_bindings WHERE owner_id = ? AND anime_id = ?", (owner_id, anime_id)).fetchone()
                if saved:
                    return saved[0], "saved"
            cached = connection.execute("SELECT source_id FROM auto_source_bindings WHERE anime_id = ? AND matched_at > ?", (anime_id, int(time.time()) - 86400)).fetchone()
        return (cached[0], "automatic") if cached else (None, None)

    def save_source_binding(self, anime_id, source_id, owner_id=None, preferred_provider=None):
        with self.connect() as connection:
            if owner_id:
                connection.execute("""INSERT INTO owned_source_bindings VALUES (?, ?, ?)
                    ON CONFLICT(owner_id, anime_id) DO UPDATE SET source_id = excluded.source_id""", (owner_id, anime_id, source_id))
                if preferred_provider:
                    connection.execute("""INSERT INTO playback_preferences VALUES (?, ?, ?)
                        ON CONFLICT(owner_id, anime_id) DO UPDATE SET provider = excluded.provider""",
                        (owner_id, anime_id.split(":", 1)[-1], preferred_provider))
            else:
                connection.execute("""INSERT INTO auto_source_bindings VALUES (?, ?, ?)
                    ON CONFLICT(anime_id) DO UPDATE SET source_id = excluded.source_id, matched_at = excluded.matched_at""", (anime_id, source_id, int(time.time())))

    def preferred_playback_provider(self, anime_id, owner_id):
        if not owner_id:
            return None
        with self.connect() as connection:
            row = connection.execute("SELECT provider FROM playback_preferences WHERE owner_id = ? AND anime_id = ?",
                                     (owner_id, anime_id)).fetchone()
        return row[0] if row else None

    def forget_auto_source(self, anime_id):
        with self.connect() as connection:
            connection.execute("DELETE FROM auto_source_bindings WHERE anime_id = ?", (anime_id,))
