"""Test provider behavior with fixed HTTP responses, without contacting the real site."""
from copy import deepcopy
from pathlib import Path
import json
import tempfile
import unittest

import httpx
from fastapi.testclient import TestClient

from main import create_app
from xifan import XifanSource


class PlaybackTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.requests = []
        self.play_url = "https://play.xfvod.pro/example.mp4?token=test-only"
        self.fail = None
        self.detail = {"anime": {"id": 26, "title": "葬送的芙莉莲"}, "sources": [
            {"id": 5, "name": "主线", "episodes": [
                {"id": 200, "kind": "special", "episode_number": 0.5, "title": "特别篇"},
                {"id": 329, "kind": "main", "episode_number": 1, "title": "冒险结束"},
                {"id": 330, "kind": "main", "episode_number": 2, "title": "第二集"}]},
            {"id": 2, "name": "备用", "episodes": [{"id": 329, "kind": "main", "episode_number": 1, "title": "冒险结束"}]}]}
        self.provider = XifanSource(transport=httpx.MockTransport(self.handle))

    def handle(self, request):
        body = json.loads(request.content)
        self.requests.append((request.url.path, body))
        if self.fail == "timeout":
            raise httpx.ReadTimeout("simulated timeout", request=request)
        if self.fail == "limited":
            return httpx.Response(429)
        if request.url.path.endswith("search_animes"):
            return httpx.Response(200, json=[{"id":26,"title":"葬送的芙莉莲","release_year":2023,"total_episodes":28}])
        if request.url.path.endswith("get_anime_detail"):
            return httpx.Response(200, json=deepcopy(self.detail))
        if request.url.path.endswith("issue-web-playback"):
            return httpx.Response(200, json={"ok": True,"url":self.play_url,"expires_at":2000000000})
        return httpx.Response(404)

    def client(self):
        return TestClient(create_app(database_path=Path(self.directory)/"test.db", playback_source=self.provider))

    def test_default_binding_and_episode_numbers(self):
        with self.client() as client:
            response=client.get("/api/playback/bgm-400602?episode=1")
            self.assertEqual(response.status_code,200)
            data=response.json()
            self.assertEqual(data["status"],"ready")
            self.assertEqual(data["source_anime_id"],26)
            self.assertEqual(data["source_episode_id"],329)
            self.assertEqual(self.requests[-1][1],{"action":"fallback","episode_id":329,"source_id":5})
            self.assertEqual(response.headers["cache-control"],"no-store")

    def test_explicit_source_and_line(self):
        with self.client() as client:
            data=client.get("/api/playback/bgm-568244?source_anime_id=26&line_id=2").json()
            self.assertEqual(data["line_id"],2)
            self.assertEqual(data["source_title"],"葬送的芙莉莲")
            self.assertEqual(self.requests[-1][1]["source_id"],2)

    def test_unmatched_catalog_item_does_not_guess_a_season(self):
        with self.client() as client:
            response=client.get("/api/playback/bgm-568244")
            self.assertEqual(response.json()["status"],"unmatched")
            self.assertEqual(self.requests,[])

    def test_invalid_episode_source_and_unknown_catalog_are_rejected(self):
        with self.client() as client:
            for url,status in [("/api/playback/unknown",404),("/api/playback/bgm-400602?episode=29",404),
                               ("/api/playback/bgm-400602?episode=0",422),("/api/playback/bgm-400602?source_anime_id=-1",422)]:
                self.assertEqual(client.get(url).status_code,status)
            self.assertEqual(self.requests,[])

    def test_missing_episode_does_not_return_another_episode(self):
        with self.client() as client:
            response=client.get("/api/playback/bgm-400602?episode=3")
            self.assertEqual(response.json()["status"],"unavailable")
            self.assertNotIn("url",response.json())
            self.assertEqual(len(self.requests),1)

    def test_unknown_line_and_untrusted_media_url_are_rejected(self):
        with self.client() as client:
            self.assertEqual(client.get("/api/playback/bgm-400602?line_id=999").status_code,404)
            self.play_url="http://127.0.0.1/private"
            response=client.get("/api/playback/bgm-400602")
            self.assertEqual(response.status_code,502)
            self.assertNotIn("url",response.json())

    def test_hls_backup_format_is_reported(self):
        self.play_url="https://dl.playxf.top/example.m3u8"
        with self.client() as client:
            response=client.get("/api/playback/bgm-400602?line_id=2")
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()["format"],"hls")
    def test_search_preserves_chinese_query(self):
        with self.client() as client:
            data=client.get("/api/sources/xifan/search",params={"q":"芙莉莲"}).json()
            self.assertEqual(data["items"][0]["id"],26)
            self.assertEqual(self.requests[0][1]["search_term"],"芙莉莲")
            self.assertEqual(client.get("/api/sources/xifan/search",params={"q":" "}).status_code,400)

    def test_timeouts_and_rate_limits_have_recoverable_responses(self):
        with self.client() as client:
            self.fail="timeout"
            self.assertEqual(client.get("/api/playback/bgm-400602").status_code,504)
            self.fail="limited"
            self.assertEqual(client.get("/api/playback/bgm-400602").status_code,503)
            self.fail=None
            self.assertEqual(client.get("/api/playback/bgm-400602").status_code,200)

    def test_details_are_cached_but_signed_urls_are_requested_again(self):
        with self.client() as client:
            client.get("/api/playback/bgm-400602")
            client.get("/api/playback/bgm-400602")
            paths=[path for path,_ in self.requests]
            self.assertEqual(sum(path.endswith("get_anime_detail") for path in paths),1)
            self.assertEqual(sum(path.endswith("issue-web-playback") for path in paths),2)


if __name__ == "__main__":
    unittest.main()
