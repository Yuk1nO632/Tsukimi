"""Behavior tests use a temporary database, never your own collection."""

from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import COOKIE_NAME, create_app

ANIME = "bgm-568244"
OTHER = "bgm-548156"


class FavoritesTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.database = Path(directory) / "test.db"

    def client(self):
        return TestClient(create_app(database_path=self.database))

    def initialize(self, client):
        response = client.get("/api/favorites")
        self.assertEqual(response.status_code, 200)
        return response

    def test_persists_additions_and_removals_after_app_restart(self):
        with self.client() as client:
            self.initialize(client)
            self.assertEqual(client.put(f"/api/favorites/{ANIME}").json()["favorite_ids"], [ANIME])
            client.put(f"/api/favorites/{OTHER}")
            client.delete(f"/api/favorites/{ANIME}")
            cookies = dict(client.cookies)
        # A new FastAPI instance opens the same on-disk database.
        with self.client() as restarted:
            restarted.cookies.update(cookies)
            self.assertEqual(restarted.get("/api/favorites").json()["favorite_ids"], [OTHER])

    def test_two_browsers_have_separate_collections(self):
        with self.client() as first, self.client() as second:
            self.initialize(first)
            self.initialize(second)
            first.put(f"/api/favorites/{ANIME}")
            second.put(f"/api/favorites/{OTHER}")
            self.assertEqual(first.get("/api/favorites").json()["favorite_ids"], [ANIME])
            self.assertEqual(second.get("/api/favorites").json()["favorite_ids"], [OTHER])
            second.delete(f"/api/favorites/{ANIME}")
            self.assertEqual(first.get("/api/favorites").json()["favorite_ids"], [ANIME])

    def test_repeated_put_and_delete_are_idempotent(self):
        with self.client() as client:
            self.initialize(client)
            for _ in range(3):
                self.assertEqual(client.put(f"/api/favorites/{ANIME}").json()["favorite_ids"], [ANIME])
            for _ in range(3):
                self.assertEqual(client.delete(f"/api/favorites/{ANIME}").json()["favorite_ids"], [])

    def test_missing_forged_and_expired_sessions_cannot_write(self):
        with self.client() as client:
            self.assertEqual(client.put(f"/api/favorites/{ANIME}").status_code, 401)
            client.cookies.set(COOKIE_NAME, "a" * 43, path="/api")
            self.assertEqual(client.put(f"/api/favorites/{ANIME}").status_code, 401)
            client.cookies.clear()
            self.initialize(client)
            client.put(f"/api/favorites/{ANIME}")
            with closing(sqlite3.connect(self.database)) as connection, connection:
                connection.execute("UPDATE sessions SET expires_at = 0")
            self.assertEqual(client.delete(f"/api/favorites/{ANIME}").status_code, 401)
            self.assertEqual(self.initialize(client).json()["favorite_ids"], [])

    def test_cookie_is_persistent_http_only_and_token_is_not_stored_plainly(self):
        with self.client() as client:
            response = self.initialize(client)
            cookie_header = response.headers["set-cookie"]
            self.assertIn("HttpOnly", cookie_header)
            self.assertIn("Max-Age=2592000", cookie_header)
            self.assertIn("SameSite=lax", cookie_header)
            self.assertIn("Path=/api", cookie_header)
            self.assertEqual(response.headers["cache-control"], "no-store")
            with closing(sqlite3.connect(self.database)) as connection, connection:
                stored = connection.execute("SELECT token_hash FROM sessions").fetchone()[0]
            self.assertNotEqual(stored, client.cookies.get(COOKIE_NAME))
            self.assertEqual(len(stored), 64)

    def test_unknown_anime_is_rejected(self):
        with self.client() as client:
            self.initialize(client)
            self.assertEqual(client.put("/api/favorites/bgm-999999999").status_code, 404)
            self.assertEqual(client.get("/api/favorites").json()["favorite_ids"], [])

    def test_cross_origin_browser_mutations_are_rejected(self):
        with self.client() as client:
            self.initialize(client)
            blocked = client.put(f"/api/favorites/{ANIME}", headers={"Origin": "https://unrelated.example"})
            self.assertEqual(blocked.status_code, 403)
            blocked = client.put(f"/api/favorites/{ANIME}", headers={"Sec-Fetch-Site": "cross-site"})
            self.assertEqual(blocked.status_code, 403)
            self.assertEqual(client.get("/api/favorites").json()["favorite_ids"], [])
            for origin in ["http://127.0.0.1:3000", "http://127.0.0.1:8000"]:
                allowed = client.put(f"/api/favorites/{ANIME}", headers={"Origin": origin})
                self.assertEqual(allowed.status_code, 200)

    def test_database_failure_has_a_recoverable_response(self):
        with self.client() as client:
            self.initialize(client)
            with patch("database.Database.list_favorites", side_effect=sqlite3.OperationalError("locked")):
                response = client.get("/api/favorites")
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(client.get("/api/favorites").status_code, 200)


if __name__ == "__main__":
    unittest.main()
