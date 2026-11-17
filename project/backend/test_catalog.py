"""External metadata and collection behavior; requests never reach live providers."""
from contextlib import closing
from copy import deepcopy
from datetime import date, datetime, timezone
from unittest.mock import patch
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

import httpx
from fastapi.testclient import TestClient
from catalog import BangumiClient, SHANGHAI, airing_info, episode_date
from anich import AniChSource
from main import COOKIE_NAME, create_app

SUBJECT = {"id": 10380, "type": 2, "name": "STEINS;GATE", "name_cn": "命运石之门", "date": "2011-04-06",
           "eps": 24, "total_episodes": 29, "images": {"large": "https://lain.bgm.tv/cover.jpg"},
           "summary": "时间旅行故事", "tags": [{"name": "科幻"}], "rating": {"score": 8.8, "total": 1000},
           "infobox": [{"key": "动画制作", "value": "WHITE FOX"}]}


class CatalogCollectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.database = Path(self.directory) / "test.db"
        self.requests = []
        self.failure = None
        self.episode_rows = None
        self.episode_failure = None

    def handle(self, request):
        self.requests.append(request)
        if self.failure == "timeout":
            raise httpx.ReadTimeout("test", request=request)
        if self.failure == "limited":
            return httpx.Response(429)
        if self.failure == "missing":
            return httpx.Response(404)
        if self.failure == "wrongid":
            return httpx.Response(200, json={**SUBJECT, "id": 999})
        if self.failure == "bad":
            return httpx.Response(200, json={"unexpected": True})
        if request.url.path == "/v0/episodes" and self.episode_rows is not None:
            if self.episode_failure:
                return httpx.Response(self.episode_failure)
            self.assertEqual(request.url.params["type"], "0")
            self.assertEqual(request.url.params["subject_id"], "10380")
            offset = int(request.url.params["offset"])
            return httpx.Response(200, json={"total": len(self.episode_rows), "data": self.episode_rows[offset:offset + 200]})
        if request.url.path == "/v0/search/subjects":
            return httpx.Response(200, json={"data": [deepcopy(SUBJECT)], "total": 42})
        if request.url.path == "/calendar":
            item = deepcopy(SUBJECT)
            item.pop("infobox")
            item["air_weekday"] = 3
            return httpx.Response(200, json=[{"weekday": {"id": 3}, "items": [item]}])
        if request.url.path == "/v0/subjects/10380":
            return httpx.Response(200, json=deepcopy(SUBJECT))
        return httpx.Response(404)

    def client(self):
        provider = BangumiClient(transport=httpx.MockTransport(self.handle))
        return TestClient(create_app(database_path=self.database, metadata_source=provider, playback_source=AniChSource(transport=httpx.MockTransport(lambda request: httpx.Response(200,content=b"")))))

    def test_search_outside_seed_and_filter_pagination_reaches_provider(self):
        with self.client() as client:
            response = client.get('/api/catalog', params={'q':'石头门','year':2011,'season':2,'genre':'科幻','sort':'score','page':2,'limit':18})
            self.assertEqual(response.status_code,200)
            data=response.json()
            self.assertEqual((data['items'][0]['id'], data['total']), ('bgm-10380',42))
            body=json.loads(self.requests[0].content)
            self.assertEqual(body['keyword'],'石头门')
            self.assertEqual(body['filter']['air_date'],['>=2011-04-01','<2011-07-01'])
            self.assertEqual(body['filter']['type'],[2])
            self.assertEqual(body['filter']['tag'],['科幻'])
            self.assertEqual(self.requests[0].url.params['offset'],'18')
            self.assertEqual(body['sort'],'score')

    def test_winter_end_boundary_and_invalid_filters(self):
        with self.client() as client:
            client.get('/api/catalog',params={'year':2026,'season':4})
            self.assertEqual(json.loads(self.requests[0].content)['filter']['air_date'],['>=2026-10-01','<2027-01-01'])
            for params in [{'season':5},{'year':1800},{'sort':'unknown'},{'page':0},{'limit':100}]:
                self.assertEqual(client.get('/api/catalog',params=params).status_code,422)

    def test_detail_main_episode_count_and_unknown_ids(self):
        with self.client() as client:
            data=client.get('/api/catalog/bgm-10380').json()
            self.assertEqual(data['episodes'],24)  # Special episodes in total_episodes must not inflate the list.
            self.assertEqual(data['staff'][0]['value'],'WHITE FOX')
            self.assertEqual(client.get('/api/catalog/not-an-id').status_code,404)
            self.assertEqual(client.get('/api/catalog/bgm-999999999').status_code,404)

    def test_new_anime_collection_states_persist_and_browsers_are_isolated(self):
        with self.client() as first, self.client() as second:
            first.get('/api/collection'); second.get('/api/collection')
            for status in ['wish','watching','completed']:
                response=first.put('/api/collection/bgm-10380',json={'status':status})
                self.assertEqual(response.status_code,200)
                self.assertEqual(response.json()['items'][0]['status'],status)
            self.assertEqual(second.get('/api/collection').json()['items'],[])
            self.assertEqual(first.get('/api/favorites').json()['favorite_ids'],['bgm-10380'])
            cookies=dict(first.cookies)
        self.failure='timeout'
        with self.client() as restarted:
            restarted.cookies.update(cookies)
            data=restarted.get('/api/collection').json()['items'][0]
            self.assertEqual((data['anime']['title'],data['status']),('命运石之门','completed'))
            restarted.delete('/api/collection/bgm-10380')
            self.assertEqual(restarted.get('/api/favorites').json()['favorite_ids'],[])

    def test_status_validation_and_session_origin_guards(self):
        with self.client() as client:
            self.assertEqual(client.put('/api/collection/bgm-10380',json={'status':'wish'}).status_code,401)
            client.get('/api/collection')
            self.assertEqual(client.put('/api/collection/bgm-10380',json={'status':'other'}).status_code,422)
            self.assertEqual(client.put('/api/collection/bgm-10380',json={'status':'wish'},headers={'Origin':'https://other.example'}).status_code,403)
            self.assertEqual(client.get('/api/collection').json()['items'],[])

    def test_legacy_favorites_migrate_without_loss_and_put_does_not_reset_status(self):
        token='a'*43; digest=hashlib.sha256(token.encode()).hexdigest()
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.executescript('CREATE TABLE sessions(token_hash TEXT PRIMARY KEY, expires_at INTEGER NOT NULL); CREATE TABLE favorites(session_id TEXT, anime_id TEXT, created_at INTEGER, PRIMARY KEY(session_id,anime_id));')
            connection.execute('INSERT INTO sessions VALUES (?,?)',(digest,int(time.time())+600))
            connection.execute('INSERT INTO favorites VALUES (?,?,?)',(digest,'bgm-400602',time.time_ns()))
        with self.client() as client:
            client.cookies.set(COOKIE_NAME,token,path='/api')
            item=client.get('/api/collection').json()['items'][0]
            self.assertEqual((item['anime']['id'],item['status']),('bgm-400602','wish'))
            client.put('/api/collection/bgm-400602',json={'status':'watching'})
            client.put('/api/favorites/bgm-400602')
            self.assertEqual(client.get('/api/collection').json()['items'][0]['status'],'watching')

    def test_calendar_uses_live_items_without_replacing_rich_details(self):
        with self.client() as client:
            client.get('/api/catalog/bgm-10380')
            calendar=client.get('/api/catalog/calendar').json()
            self.assertEqual(calendar['days'][0]['weekday'],3)
            self.assertEqual(calendar['days'][0]['items'][0]['id'],'bgm-10380')
            self.assertIn('实际资源',calendar['note'])
            self.assertTrue(client.get('/api/catalog/bgm-10380').json()['detailComplete'])

    def test_source_and_playback_accept_external_anime(self):
        with self.client() as client:
            response=client.get('/api/playback/bgm-10380?episode=2')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['status'],'unmatched')
            self.assertEqual(client.get('/api/playback/bgm-10380?episode=25').status_code,404)

    def test_retry_after_upstream_failure_and_malformed_response(self):
        with self.client() as client:
            for failure,code in [('timeout',504),('limited',503),('bad',502)]:
                self.failure=failure
                self.assertEqual(client.get('/api/catalog',params={'q':failure}).status_code,code)
            self.failure=None
            self.assertEqual(client.get('/api/catalog',params={'q':'timeout'}).status_code,200)

    def test_mismatched_detail_does_not_create_an_orphaned_collection(self):
        self.failure='wrongid'
        with self.client() as client:
            client.get('/api/collection')
            self.assertEqual(client.put('/api/collection/bgm-10380',json={'status':'wish'}).status_code,502)
            self.assertEqual(client.get('/api/collection').json()['items'],[])
    def test_stale_detail_fallback_and_true_404_are_distinct(self):
        with self.client() as client:
            client.get('/api/catalog/bgm-10380')
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute('UPDATE catalog_cache SET fetched_at=0')
        self.failure='timeout'
        with self.client() as client:
            data=client.get('/api/catalog/bgm-10380').json()
            self.assertIn('detailWarning',data)
        self.failure='missing'
        with self.client() as client:
            self.assertEqual(client.get('/api/catalog/bgm-10380').status_code,404)

    def test_summary_navigation_does_not_wait_for_external_enrichment(self):
        from catalog import normalize
        from database import Database
        store = Database(self.database)
        with self.client() as client:
            summary = normalize({**SUBJECT, 'infobox': []})
            store.cache_anime(summary, 100)
            self.failure = 'timeout'
            response = client.get('/api/catalog/bgm-10380?summary=true')
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.json()['detailComplete'])
            self.assertEqual(self.requests, [])
            # Full detail still refreshes separately and falls back honestly on failure.
            data = client.get('/api/catalog/bgm-10380').json()
            self.assertIn('detailWarning', data)
            self.assertTrue(self.requests)

    def test_search_summary_preserves_rich_detail_and_its_original_age(self):
        from catalog import normalize
        from database import Database
        store = Database(self.database)
        with self.client() as client:
            rich = client.get('/api/catalog/bgm-10380').json()
            store.cache_anime(rich, 100)
            # Exercise the actual bulk cache writer used by search.
            summary = normalize({**SUBJECT, 'infobox': []})
            store.cache_animes([summary], 200)
            cached, stamp = store.cached_anime('bgm-10380')
            self.assertEqual(stamp, 100)
            self.assertTrue(cached['detailComplete'])
            self.assertEqual(cached['staff'][0]['value'], 'WHITE FOX')
            self.assertTrue(client.get('/api/catalog/bgm-10380?summary=true').json()['detailComplete'])
            self.assertNotIn('detailWarning', client.get('/api/catalog/bgm-10380').json())

    def test_summary_miss_fetches_real_details_and_preserves_true_404(self):
        with self.client() as client:
            self.assertEqual(client.get('/api/catalog/bgm-10380?summary=true').json()['id'], 'bgm-10380')
            self.assertEqual(client.get('/api/catalog/bgm-999999999?summary=true').status_code, 404)

    def test_detail_returns_real_airing_progress_without_changing_total(self):
        self.episode_rows = [{"type": 0, "ep": n, "sort": n, "airdate": "2000-01-01" if n <= 7 else "2099-01-01"} for n in range(1, 25)]
        with self.client() as client:
            data = client.get("/api/catalog/bgm-10380").json()
            self.assertEqual(data["episodes"], 24)
            self.assertEqual((data["airing"]["status"], data["airing"]["airedCount"], data["airing"]["latestEpisode"]), ("airing", 7, 7))
            self.assertEqual(data["airing"]["episodes"][7]["status"], "upcoming")
            self.assertNotIn("airing", client.get("/api/catalog/bgm-10380?summary=true").json())
            self.assertEqual(len([r for r in self.requests if r.url.path == "/v0/episodes"]), 1)

    def test_episode_pagination_and_schedule_cache_do_not_truncate_long_series(self):
        self.episode_rows = [{"type": 0, "ep": n, "airdate": "2000-01-01"} for n in range(1, 202)]
        with self.client() as client:
            first = client.get("/api/catalog/bgm-10380").json()
            self.assertEqual(first["airing"]["airedCount"], 201)
            # More known episodes than the metadata total cannot be called completed.
            self.assertEqual(first["airing"]["status"], "unknown")
            client.get("/api/catalog/bgm-10380")
            offsets = [r.url.params["offset"] for r in self.requests if r.url.path == "/v0/episodes"]
            self.assertEqual(offsets, ["0", "200"])

    def test_schedule_failure_keeps_details_and_honest_unknown_progress(self):
        self.episode_rows = []
        self.episode_failure = 503
        with self.client() as client:
            data = client.get("/api/catalog/bgm-10380").json()
            self.assertEqual(data["title"], "命运石之门")
            self.assertEqual(data["airing"]["status"], "unknown")
            self.assertIn("warning", data["airing"])
            self.episode_failure = None
            self.episode_rows = [{"type": 0, "ep": n, "airdate": "2000-01-01"} for n in range(1, 25)]
            self.assertEqual(client.get("/api/catalog/bgm-10380").json()["airing"]["status"], "completed")

    def test_incomplete_or_malformed_schedule_is_not_reported_as_completed(self):
        provider = BangumiClient(transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"total": 24, "data": []})))
        from catalog import Catalog, normalize
        from database import Database
        store = Database(self.database)
        store.initialize()
        store.cache_anime(normalize(SUBJECT), int(time.time()))
        result = Catalog(store, provider).detail("bgm-10380")
        self.assertEqual(result["airing"]["status"], "unknown")
        self.assertIn("warning", result["airing"])
        provider.close()


class AiringInfoTests(unittest.TestCase):
    today = date(2026, 11, 18)

    def test_airing_completed_upcoming_and_unknown(self):
        anime = {"episodes": 2, "releaseDate": "2026-11-01"}
        first = {"type": 0, "ep": 1, "airdate": "2026-11-11"}
        final = {"type": 0, "ep": 2, "airdate": "2026-11-21"}
        self.assertEqual(airing_info(anime, [first, final], self.today)["status"], "airing")
        self.assertEqual(airing_info(anime, [first, {**final, "airdate": "2026-11-18"}], self.today)["status"], "completed")
        self.assertEqual(airing_info(anime, [{**first, "airdate": "2026-11-20"}, final], self.today)["status"], "upcoming")
        self.assertEqual(airing_info(anime, [first], self.today)["status"], "unknown")
        self.assertEqual(airing_info(anime, [], self.today)["status"], "unknown")
        self.assertEqual(airing_info(anime, [final], self.today)["status"], "unknown")
        self.assertEqual(airing_info({"episodes": 0}, [first], self.today)["status"], "unknown")

    def test_future_episode_beyond_an_outdated_total_prevents_completion(self):
        rows = [{"type": 0, "ep": 1, "airdate": "2000-01-01"},
                {"type": 0, "ep": 2, "airdate": "2099-01-01"}]
        result = airing_info({"episodes": 1}, rows, self.today)
        self.assertEqual(result["status"], "airing")
        self.assertEqual(result["latestEpisode"], 1)

    def test_missing_invalid_fractional_and_special_episodes(self):
        rows = [{"type": 0, "ep": 1, "airdate": "2026-11-1"},
                {"type": 0, "ep": 2, "airdate": ""},
                {"type": 0, "ep": 3, "airdate": "2026-02-30"},
                {"type": 1, "ep": 4, "airdate": "2000-01-01"},
                {"type": 0, "ep": 4.5, "airdate": "2000-01-01"},
                {"type": 0, "ep": True, "airdate": "2000-01-01"},
                {"type": 0, "ep": 0, "airdate": "2000-01-01"}]
        result = airing_info({"episodes": 3}, rows, self.today)
        self.assertEqual(result["airedCount"], 1)
        self.assertEqual([row["status"] for row in result["episodes"]], ["aired", "unknown", "unknown"])
        self.assertIsNone(episode_date("2026-11"))
        self.assertEqual(episode_date("2026-11-1"), date(2026, 11, 1))

    def test_relative_episode_numbers_gaps_and_conflicting_duplicates(self):
        rows = [{"type": 0, "ep": 1, "sort": 13, "airdate": "2000-01-01"},
                {"type": 0, "ep": 3, "sort": 15, "airdate": "2000-01-01"}]
        result = airing_info({"episodes": 3}, rows, self.today)
        self.assertEqual((result["latestEpisode"], result["airedCount"], result["status"]), (3, 2, "unknown"))
        result = airing_info({"episodes": 1}, [rows[0], {**rows[0], "airdate": "2099-01-01"}], self.today)
        self.assertEqual(result["episodes"][0]["status"], "unknown")
        self.assertEqual(result["status"], "unknown")

    def test_explicit_end_date_handles_totals_including_a_separate_special(self):
        anime = {"episodes": 25, "staff": [{"label": "播放结束", "value": "2011年9月14日"}]}
        rows = [{"type": 0, "ep": n, "airdate": "2011-09-13"} for n in range(1, 25)]
        self.assertEqual(airing_info(anime, rows, self.today)["status"], "completed")
        self.assertEqual(airing_info(anime, rows, self.today)["airedCount"], 24)
        # A new scheduled episode takes precedence over an outdated end date.
        rows.append({"type": 0, "ep": 25, "airdate": "2099-01-01"})
        self.assertEqual(airing_info(anime, rows, self.today)["status"], "airing")

    def test_beijing_date_boundary_and_cached_schedule_recalculation(self):
        rows = [{"type": 0, "ep": 1, "airdate": "2026-11-19"}]
        with patch("catalog.datetime") as clock:
            clock.now.return_value = datetime(2026, 11, 18, 16, 1, tzinfo=timezone.utc).astimezone(SHANGHAI)
            result = airing_info({"episodes": 1}, rows)
            self.assertEqual(result["asOf"], "2026-11-19")
            self.assertEqual(result["status"], "completed")
        self.assertEqual(airing_info({"episodes": 1}, rows, self.today)["status"], "upcoming")


if __name__ == '__main__':
    unittest.main()
