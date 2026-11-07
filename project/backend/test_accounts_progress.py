from contextlib import closing
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import tempfile
import time
import unittest
from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from catalog import BangumiClient
from database import Database
from main import create_app, COOKIE_NAME

ANIME = "bgm-400602"
OTHER = "bgm-328609"
PASSWORD = "test-password-123"
QUESTIONS = [
    {"question": "第一个自定义问题？", "answer": "secret-answer-one"},
    {"question": "第二个自定义问题？", "answer": "secret-answer-two"},
    {"question": "第三个自定义问题？", "answer": "secret-answer-three"},
]


class AccountProgressTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.directory) / "test.db"

    def client(self):
        return self.enterContext(
            TestClient(
                create_app(
                    database_path=self.path,
                    metadata_source=BangumiClient(
                        transport=httpx.MockTransport(
                            lambda request: httpx.Response(404)
                        )
                    ),
                )
            )
        )

    def register(self, client, username="first_user"):
        client.get("/api/account")
        response = client.post(
            "/api/account/register",
            json={
                "username": username,
                "password": PASSWORD,
                "nickname": "测试用户",
                "questions": QUESTIONS,
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

    def sql(self, statement, args=()):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            return connection.execute(statement, args).fetchall()

    def payload(self, client, revision=0, episode=1, position=120):
        return {
            "episode": episode,
            "position": position,
            "duration": 1500,
            "revision": revision,
            "operation_id": secrets.token_hex(16),
            "scope": client.get("/api/account").json()["scope"],
            "source_id": 32339,
            "line_id": 1,
        }

    def recovery(self, client, username="first_user"):
        response = client.post("/api/account/recovery", json={"username": username})
        self.assertEqual(response.status_code, 200, response.text)
        return {
            "username": username,
            "challenge": response.json()["challenge"],
            "answers": [q["answer"] for q in QUESTIONS],
            "password": "new-password-456",
        }

    def test_anonymous_data_requires_explicit_import_and_import_is_idempotent(self):
        client = self.client()
        old_state = client.get("/api/account").json()
        old_cookie = client.cookies.get(COOKIE_NAME)
        client.put(f"/api/collection/{ANIME}", json={"status": "watching"})
        client.put(f"/api/progress/{ANIME}", json=self.payload(client))
        with Database(self.path).connect() as connection:
            owner = connection.execute("SELECT owner_id FROM sessions").fetchone()[0]
            connection.execute(
                "INSERT INTO owned_source_bindings VALUES (?, ?, ?)",
                (owner, f"anich:{ANIME}", 32339),
            )
        state = self.register(client)
        self.assertTrue(state["pending_import"])
        self.assertNotEqual(old_cookie, client.cookies.get(COOKIE_NAME))
        self.assertEqual(client.get("/api/collection").json()["items"], [])
        self.assertEqual(
            client.put(
                f"/api/progress/{ANIME}",
                json={**self.payload(client), "scope": old_state["scope"]},
            ).status_code,
            409,
        )
        for _ in range(2):
            self.assertEqual(
                client.post(
                    "/api/account/import", json={"action": "merge"}
                ).status_code,
                200,
            )
        self.assertEqual(len(client.get("/api/collection").json()["items"]), 1)
        self.assertEqual(
            client.get(f"/api/progress/{ANIME}").json()["item"]["position"], 120
        )
        self.assertEqual(
            Database(self.path).source_binding(f"anich:{ANIME}", state["user"]["id"]),
            (32339, "saved"),
        )

    def test_import_keeps_existing_account_record_and_can_be_declined(self):
        client = self.client()
        self.register(client)
        client.put(f"/api/collection/{ANIME}", json={"status": "completed"})
        client.post("/api/account/logout")
        client.get("/api/account")
        client.put(f"/api/collection/{ANIME}", json={"status": "wish"})
        client.put(f"/api/collection/{OTHER}", json={"status": "wish"})
        client.post(
            "/api/account/login",
            json={"username": "first_user", "password": PASSWORD},
        )
        client.post("/api/account/import", json={"action": "merge"})
        rows = client.get("/api/collection").json()["items"]
        self.assertEqual(
            {r["anime"]["id"]: r["status"] for r in rows},
            {ANIME: "completed", OTHER: "wish"},
        )
        client.post("/api/account/logout")
        client.get("/api/account")
        client.put(f"/api/progress/{ANIME}", json=self.payload(client))
        client.post(
            "/api/account/login",
            json={"username": "first_user", "password": PASSWORD},
        )
        result = client.post("/api/account/import", json={"action": "skip"}).json()
        self.assertFalse(result["pending_import"])
        self.assertIsNone(client.get(f"/api/progress/{ANIME}").json()["item"])

    def test_two_devices_share_account_but_other_account_is_isolated(self):
        first = self.client()
        second = self.client()
        other = self.client()
        self.register(first)
        self.register(other, "other_user")
        response = second.post(
            "/api/account/login",
            json={"username": "first_user", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(
            first.cookies.get(COOKIE_NAME), second.cookies.get(COOKIE_NAME)
        )
        first.put(f"/api/collection/{ANIME}", json={"status": "watching"})
        first.put(f"/api/progress/{ANIME}", json=self.payload(first))
        self.assertEqual(len(second.get("/api/collection").json()["items"]), 1)
        self.assertEqual(
            second.get(f"/api/progress/{ANIME}").json()["item"]["position"], 120
        )
        self.assertEqual(other.get("/api/collection").json()["items"], [])
        self.assertIsNone(other.get(f"/api/progress/{ANIME}").json()["item"])
        second.post("/api/account/logout")
        self.assertEqual(len(first.get("/api/collection").json()["items"]), 1)
        self.assertEqual(second.get("/api/collection").json()["items"], [])

    def test_password_change_requires_old_password_and_revokes_sessions(self):
        client = self.client()
        self.register(client)
        self.assertEqual(
            client.post(
                "/api/account/password",
                json={
                    "current_password": "incorrect-password",
                    "password": "new-password-456",
                },
            ).status_code,
            400,
        )
        self.assertEqual(
            client.post(
                "/api/account/password",
                json={"current_password": PASSWORD, "password": "new-password-456"},
            ).status_code,
            200,
        )
        self.assertIsNone(client.get("/api/account").json()["user"])

    def test_progress_cas_retries_rewind_and_episode_switch(self):
        client = self.client()
        client.get("/api/account")
        payload = self.payload(client)
        saved = client.put(f"/api/progress/{ANIME}", json=payload)
        self.assertEqual(saved.status_code, 200)
        self.assertEqual(saved.json()["item"]["revision"], 1)
        self.assertEqual(
            client.put(f"/api/progress/{ANIME}", json=payload).json(), saved.json()
        )
        stale = client.put(
            f"/api/progress/{ANIME}", json=self.payload(client, position=300)
        )
        self.assertEqual(stale.status_code, 409)
        self.assertEqual(stale.json()["item"]["position"], 120)
        self.assertEqual(
            client.put(
                f"/api/progress/{ANIME}", json=self.payload(client, 1, position=20)
            ).json()["item"]["position"],
            20,
        )
        self.assertEqual(
            client.put(
                f"/api/progress/{ANIME}", json=self.payload(client, 2, episode=2)
            ).json()["item"]["episode"],
            2,
        )

    def test_progress_validation_and_no_unsigned_cookie_writes(self):
        client = self.client()
        self.assertEqual(
            client.put(
                f"/api/progress/{ANIME}",
                json={**self.payload(client), "position": 1600},
            ).status_code,
            400,
        )
        for values in ({"episode": 99999}, {"duration": 0}, {"position": -1}):
            response = client.put(
                f"/api/progress/{ANIME}", json={**self.payload(client), **values}
            )
            self.assertIn(response.status_code, {400, 422})
        self.assertEqual(
            client.put(
                f"/api/progress/{ANIME}",
                json=self.payload(client),
                headers={"Origin": "https://evil.example"},
            ).status_code,
            403,
        )

    def test_progress_and_account_survive_restart(self):
        client = self.client()
        self.register(client)
        client.put(f"/api/progress/{ANIME}", json=self.payload(client))
        other = self.client()
        other.cookies.update(dict(client.cookies))
        self.assertEqual(
            other.get(f"/api/progress/{ANIME}").json()["item"]["position"], 120
        )
        self.assertIsNotNone(other.get("/api/account").json()["user"])

    def test_legacy_backup_and_migration_copy_once_without_resurrection(self):
        raw = secrets.token_urlsafe(32)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.executescript(
                "CREATE TABLE sessions(token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL); CREATE TABLE favorites(session_id TEXT, anime_id TEXT, created_at INTEGER, PRIMARY KEY(session_id,anime_id));"
            )
            connection.execute(
                "INSERT INTO sessions VALUES (?, ?)", (digest, int(time.time()) + 600)
            )
            connection.execute(
                "INSERT INTO favorites VALUES (?, ?, ?)",
                (digest, ANIME, time.time_ns()),
            )
        client = self.client()
        client.cookies.set(COOKIE_NAME, raw, path="/api")
        self.assertEqual(len(client.get("/api/collection").json()["items"]), 1)
        self.assertTrue(self.path.with_suffix(".pre-accounts.db").exists())
        client.delete(f"/api/collection/{ANIME}")
        other = self.client()
        other.cookies.update(dict(client.cookies))
        self.assertEqual(other.get("/api/collection").json()["items"], [])
        self.assertEqual(self.sql("SELECT COUNT(*) FROM favorites")[0][0], 1)
        self.assertEqual(self.sql("PRAGMA foreign_key_check"), [])

    def test_concurrent_writes_accept_one_revision(self):
        from concurrent.futures import ThreadPoolExecutor

        first = self.client()
        first.get("/api/account")
        second = self.client()
        second.cookies.update(dict(first.cookies))
        payloads = [
            self.payload(first, position=120),
            self.payload(second, position=300),
        ]
        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [
                pool.submit(client.put, f"/api/progress/{ANIME}", json=payload)
                for client, payload in zip((first, second), payloads)
            ]
            statuses = sorted(job.result().status_code for job in jobs)
        self.assertEqual(statuses, [200, 409])

    def test_migration_failure_rolls_back_and_backup_restores_legacy_data(self):
        digest = "a" * 64
        with closing(sqlite3.connect(self.path)) as connection, connection:
            connection.executescript(
                "CREATE TABLE sessions(token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL); CREATE TABLE favorites(session_id TEXT, anime_id TEXT, created_at INTEGER, PRIMARY KEY(session_id,anime_id));"
            )
            connection.execute(
                "INSERT INTO sessions VALUES (?, ?)", (digest, int(time.time()) + 600)
            )
            connection.execute(
                "INSERT INTO favorites VALUES (?, ?, ?)", (digest, ANIME, 123)
            )
        original = Database._initialize_accounts

        def fail_after_copy(store, connection):
            original(store, connection)
            raise sqlite3.OperationalError("test migration interruption")

        with patch.object(Database, "_initialize_accounts", fail_after_copy):
            with self.assertRaises(sqlite3.OperationalError):
                Database(self.path).initialize()
        self.assertEqual(self.sql("SELECT anime_id FROM favorites"), [(ANIME,)])
        with closing(
            sqlite3.connect(self.path.with_suffix(".pre-accounts.db"))
        ) as backup:
            self.assertEqual(
                backup.execute("SELECT anime_id FROM favorites").fetchall(), [(ANIME,)]
            )
        Database(self.path).initialize()
        self.assertEqual(Database(self.path).list_favorites(digest), [ANIME])

    def test_registration_hashes_three_answers_and_normalizes_username(self):
        client = self.client()
        state = self.register(client, "FIRST_USER")
        self.assertEqual(state["user"]["username"], "first_user")
        row = self.sql("SELECT password_hash,security_json FROM users")[0]
        self.assertTrue(row[0].startswith("$argon2id$"))
        for item in json.loads(row[1]):
            self.assertTrue(item["hash"].startswith("$argon2id$"))
        self.assertNotIn("secret-answer-one", row[1])
        self.assertEqual(
            client.post(
                "/api/account/register",
                json={
                    "username": "first_user",
                    "password": PASSWORD,
                    "nickname": "用户",
                    "questions": QUESTIONS,
                },
            ).status_code,
            409,
        )

    def test_reset_requires_all_answers_and_revokes_every_device(self):
        first = self.client()
        second = self.client()
        self.register(first)
        second.post(
            "/api/account/login", json={"username": "first_user", "password": PASSWORD}
        )
        first.put(f"/api/collection/{ANIME}", json={"status": "watching"})
        data = self.recovery(first)
        bad = {**data, "answers": ["wrong-answer-one", *data["answers"][1:]]}
        self.assertEqual(
            first.post("/api/account/reset-password", json=bad).status_code, 400
        )
        data["answers"] = [
            "  SECRET-ANSWER-ONE  ",
            "secret-answer-two",
            "secret-answer-three",
        ]
        self.assertEqual(
            first.post("/api/account/reset-password", json=data).status_code, 200
        )
        self.assertEqual(
            second.put(f"/api/collection/{ANIME}", json={"status": "wish"}).status_code,
            401,
        )
        self.assertEqual(
            first.post("/api/account/reset-password", json=data).status_code, 400
        )
        self.assertEqual(
            first.post(
                "/api/account/login",
                json={"username": "first_user", "password": "new-password-456"},
            ).status_code,
            200,
        )
        self.assertEqual(len(first.get("/api/collection").json()["items"]), 1)

    def test_recovery_expiry_attempt_limit_and_session_binding(self):
        first = self.client()
        second = self.client()
        self.register(first)
        second.get("/api/account")
        data = self.recovery(first)
        self.assertEqual(
            second.post("/api/account/reset-password", json=data).status_code, 400
        )
        bad = {**data, "answers": ["wrong-answer"] * 3}
        for _ in range(5):
            self.assertEqual(
                first.post("/api/account/reset-password", json=bad).status_code, 400
            )
        self.assertEqual(
            first.post("/api/account/reset-password", json=data).status_code, 400
        )
        data = self.recovery(first)
        self.sql("UPDATE recovery_challenges SET expires_at=0")
        self.assertEqual(
            first.post("/api/account/reset-password", json=data).status_code, 400
        )

    def test_recovery_rate_limit_survives_restart(self):
        client = self.client()
        client.get("/api/account")
        for _ in range(10):
            client.post("/api/account/recovery", json={"username": "missing_user"})
        restarted = self.client()
        restarted.get("/api/account")
        self.assertEqual(
            restarted.post(
                "/api/account/recovery", json={"username": "missing_user"}
            ).status_code,
            429,
        )

    def test_legacy_email_login_and_setting_security_preserve_identity(self):
        from accounts import PASSWORDS

        client = self.client()
        with Database(self.path).connect() as connection:
            connection.execute("INSERT INTO owners VALUES ('legacy')")
            connection.execute(
                "INSERT INTO users (id,email,nickname,password_hash,created_at) VALUES ('legacy','old@example.com','旧用户',?,?)",
                (PASSWORDS.hash(PASSWORD), int(time.time())),
            )
        Database(self.path).initialize()
        response = client.post(
            "/api/account/login",
            json={"username": "old@example.com", "password": PASSWORD},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["user"]["id"], "legacy")
        self.assertFalse(response.json()["user"]["security_configured"])
        data = {"current_password": PASSWORD, "questions": QUESTIONS}
        self.assertEqual(
            client.post(
                "/api/account/security-questions",
                json={**data, "current_password": "wrong-password"},
            ).status_code,
            400,
        )
        self.assertTrue(
            client.post("/api/account/security-questions", json=data).json()["user"][
                "security_configured"
            ]
        )
        recovery = self.recovery(client, "old@example.com")
        self.assertEqual(
            client.post("/api/account/security-questions", json=data).status_code, 200
        )
        self.assertEqual(
            client.post("/api/account/reset-password", json=recovery).status_code, 400
        )

    def test_three_distinct_questions_and_answers_required(self):
        client = self.client()
        for questions in (QUESTIONS[:2], [QUESTIONS[0]] * 3):
            response = client.post(
                "/api/account/register",
                json={
                    "username": "valid_user",
                    "password": PASSWORD,
                    "nickname": "用户",
                    "questions": questions,
                },
            )
            self.assertEqual(response.status_code, 422)

    def test_admin_bootstrap_is_idempotent_and_does_not_overwrite_password(self):
        from create_admin import create_admin

        client = self.client()
        store = Database(self.path)
        first = create_admin(store, "TestAdmin", PASSWORD)
        again = create_admin(store, "TestAdmin", PASSWORD)
        self.assertEqual(first["id"], again["id"])
        self.assertEqual(first["role"], "admin")
        with self.assertRaises(ValueError):
            create_admin(store, "TestAdmin", "different-password")
        response = client.post(
            "/api/account/login", json={"username": "TestAdmin", "password": PASSWORD}
        )
        self.assertEqual(response.json()["user"]["role"], "admin")
        self.assertFalse(response.json()["user"]["security_configured"])

    def test_public_registration_cannot_choose_admin_role(self):
        client = self.client()
        payload = {
            "username": "regular_user",
            "password": PASSWORD,
            "nickname": "普通账号",
            "questions": QUESTIONS,
            "role": "admin",
        }
        result = client.post("/api/account/register", json=payload)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["user"]["role"], "user")
