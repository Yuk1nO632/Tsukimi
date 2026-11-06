"""Account/OTP/migration/progress regressions run against isolated SQLite files."""

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
from fastapi import HTTPException
from catalog import BangumiClient
from database import Database
from main import create_app, COOKIE_NAME

ANIME = "bgm-400602"
OTHER = "bgm-328609"
PASSWORD = "test-password-123"


class FakeMailer:
    ready = True
    mode = "test"

    def __init__(self):
        self.messages = []

    def send(self, email, purpose, code):
        self.messages.append((email, purpose, code))


class AccountProgressTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.directory) / "test.db"
        self.mail = FakeMailer()

    def client(self):
        return self.enterContext(
            TestClient(
                create_app(
                    database_path=self.path,
                    mail_sender=self.mail,
                    metadata_source=BangumiClient(
                        transport=httpx.MockTransport(
                            lambda request: httpx.Response(404)
                        )
                    ),
                )
            )
        )

    def register(self, client, email="first@example.com"):
        client.get("/api/account")
        self.assertEqual(
            client.post(
                "/api/account/code", json={"email": email, "purpose": "register"}
            ).status_code,
            200,
        )
        response = client.post(
            "/api/account/register",
            json={
                "email": email,
                "password": PASSWORD,
                "nickname": "测试用户",
                "code": self.mail.messages[-1][2],
            },
        )
        self.assertEqual(response.status_code, 200, response.text)
        return response.json()

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

    def sql(self, statement, args=()):
        with closing(sqlite3.connect(self.path)) as connection, connection:
            return connection.execute(statement, args).fetchall()

    def test_verified_registration_normalizes_email_and_hashes_secrets(self):
        client = self.client()
        state = self.register(client, "FIRST@example.com")
        self.assertEqual(state["user"]["email"], "first@example.com")
        saved = self.sql("SELECT password_hash FROM users")[0][0]
        self.assertTrue(saved.startswith("$argon2id$"))
        self.assertNotIn(PASSWORD, saved)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM email_codes")[0][0], 0)

    def test_registration_requires_valid_unexpired_otp(self):
        client = self.client()
        client.post(
            "/api/account/code",
            json={"email": "first@example.com", "purpose": "register"},
        )
        code = self.mail.messages[-1][2]
        stored = self.sql("SELECT digest FROM email_codes")[0][0]
        self.assertNotEqual(stored, code)
        self.sql("UPDATE email_codes SET expires_at=0")
        response = client.post(
            "/api/account/register",
            json={
                "email": "first@example.com",
                "password": PASSWORD,
                "nickname": "用户",
                "code": code,
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM users")[0][0], 0)

    def test_five_failed_attempts_persist_and_disable_code(self):
        client = self.client()
        client.post(
            "/api/account/code",
            json={"email": "first@example.com", "purpose": "register"},
        )
        code = self.mail.messages[-1][2]
        wrong = "000000" if code != "000000" else "111111"
        data = {
            "email": "first@example.com",
            "password": PASSWORD,
            "nickname": "用户",
            "code": wrong,
        }
        for _ in range(5):
            self.assertEqual(
                client.post("/api/account/register", json=data).status_code, 400
            )
        self.assertEqual(self.sql("SELECT attempts FROM email_codes")[0][0], 5)
        data["code"] = code
        self.assertEqual(
            client.post("/api/account/register", json=data).status_code, 400
        )

    def test_cooldown_resend_replaces_old_code_and_purposes_are_isolated(self):
        client = self.client()
        client.post(
            "/api/account/code",
            json={"email": "first@example.com", "purpose": "register"},
        )
        self.assertEqual(
            client.post(
                "/api/account/code",
                json={"email": "first@example.com", "purpose": "register"},
            ).status_code,
            429,
        )
        old = self.mail.messages[-1][2]
        self.sql("UPDATE email_codes SET sent_at=0")
        with patch("accounts.secrets.randbelow", return_value=(int(old) + 1) % 1000000):
            self.assertEqual(
                client.post(
                    "/api/account/code",
                    json={"email": "first@example.com", "purpose": "register"},
                ).status_code,
                200,
            )
        data = {
            "email": "first@example.com",
            "password": PASSWORD,
            "nickname": "用户",
            "code": old,
        }
        self.assertEqual(
            client.post("/api/account/register", json=data).status_code, 400
        )
        data["code"] = self.mail.messages[-1][2]
        self.assertEqual(
            client.post("/api/account/reset-password", json=data).status_code, 400
        )
        self.assertEqual(
            client.post("/api/account/register", json=data).status_code, 200
        )

    def test_delivery_failure_discards_code_without_leaking_it(self):
        client = self.client()
        with patch.object(
            self.mail, "send", side_effect=HTTPException(503, "暂时无法发送")
        ):
            response = client.post(
                "/api/account/code",
                json={"email": "first@example.com", "purpose": "register"},
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.sql("SELECT COUNT(*) FROM email_codes")[0][0], 0)

    def test_unregistered_reset_and_existing_registration_have_generic_response(self):
        client = self.client()
        response = client.post(
            "/api/account/code",
            json={"email": "missing@example.com", "purpose": "reset"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(self.mail.messages), 0)
        self.register(client)
        self.sql("UPDATE email_codes SET sent_at=0")
        response2 = client.post(
            "/api/account/code",
            json={"email": "first@example.com", "purpose": "register"},
        )
        self.assertEqual(response.json(), response2.json())
        self.assertEqual(len(self.mail.messages), 1)

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
            json={"email": "first@example.com", "password": PASSWORD},
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
            json={"email": "first@example.com", "password": PASSWORD},
        )
        result = client.post("/api/account/import", json={"action": "skip"}).json()
        self.assertFalse(result["pending_import"])
        self.assertIsNone(client.get(f"/api/progress/{ANIME}").json()["item"])

    def test_two_devices_share_account_but_other_account_is_isolated(self):
        first = self.client()
        second = self.client()
        other = self.client()
        self.register(first)
        self.register(other, "other@example.com")
        response = second.post(
            "/api/account/login",
            json={"email": "first@example.com", "password": PASSWORD},
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

    def test_reset_consumes_code_revokes_all_sessions_and_preserves_data(self):
        first = self.client()
        second = self.client()
        self.register(first)
        second.post(
            "/api/account/login",
            json={"email": "first@example.com", "password": PASSWORD},
        )
        first.put(f"/api/collection/{ANIME}", json={"status": "watching"})
        first.post(
            "/api/account/code", json={"email": "first@example.com", "purpose": "reset"}
        )
        payload = {
            "email": "first@example.com",
            "password": "new-password-456",
            "code": self.mail.messages[-1][2],
        }
        self.assertEqual(
            first.post("/api/account/reset-password", json=payload).status_code, 200
        )
        self.assertEqual(
            second.put(f"/api/collection/{ANIME}", json={"status": "wish"}).status_code,
            401,
        )
        self.assertEqual(
            first.post("/api/account/reset-password", json=payload).status_code, 400
        )
        self.assertEqual(
            first.post(
                "/api/account/login",
                json={"email": "first@example.com", "password": PASSWORD},
            ).status_code,
            401,
        )
        self.assertEqual(
            first.post(
                "/api/account/login",
                json={"email": "first@example.com", "password": "new-password-456"},
            ).status_code,
            200,
        )
        self.assertEqual(len(first.get("/api/collection").json()["items"]), 1)

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

    def test_otp_attempts_rate_limit_survives_new_app_instance(self):
        client = self.client()
        for _ in range(10):
            client.post(
                "/api/account/login",
                json={"email": "first@example.com", "password": PASSWORD},
            )
        other = self.client()
        self.assertEqual(
            other.post(
                "/api/account/login",
                json={"email": "first@example.com", "password": PASSWORD},
            ).status_code,
            429,
        )

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

    def test_ses_sdk_request_uses_template_and_hides_credentials(self):
        import os
        from mailer import Mailer

        environment = {
            "TSUKIMI_MAIL_MODE": "ses",
            "TSUKIMI_MAIL_FROM": "Tsukimi <noreply@mail.example.com>",
            "TENCENTCLOUD_SECRET_ID": "test-id",
            "TENCENTCLOUD_SECRET_KEY": "test-secret",
            "TSUKIMI_SES_TEMPLATE_REGISTER": "100",
            "TSUKIMI_SES_TEMPLATE_RESET": "200",
        }
        with patch.dict(os.environ, environment), patch(
            "tencentcloud.ses.v20201002.ses_client.SesClient"
        ) as client:
            mailer = Mailer()
            self.assertTrue(mailer.ready)
            mailer.send("first@example.com", "register", "123456")
            request = client.return_value.SendEmail.call_args.args[0]
            self.assertEqual(request.Destination, ["first@example.com"])
            self.assertEqual(request.Template.TemplateID, 100)
            self.assertEqual(
                json.loads(request.Template.TemplateData)["code"], "123456"
            )
            self.assertEqual(request.TriggerType, 1)

    def test_file_mail_requires_explicit_development_mode(self):
        import os
        from mailer import Mailer

        with patch.dict(
            os.environ, {"TSUKIMI_MAIL_MODE": "file", "TSUKIMI_ENV": "production"}
        ):
            self.assertFalse(Mailer().ready)
        with patch.dict(
            os.environ,
            {
                "TSUKIMI_MAIL_MODE": "file",
                "TSUKIMI_ENV": "development",
                "TSUKIMI_DEV_MAIL_FILE": str(Path(self.directory) / "mail.jsonl"),
            },
        ):
            mailer = Mailer()
            self.assertTrue(mailer.ready)
            mailer.send("first@example.com", "register", "123456")
            self.assertEqual(json.loads(mailer.file.read_text())["code"], "123456")


if __name__ == "__main__":
    unittest.main()
