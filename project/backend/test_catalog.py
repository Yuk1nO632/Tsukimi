"""External metadata and collection behavior; requests never reach live providers."""
from contextlib import closing
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

import httpx
from fastapi.testclient import TestClient
from catalog import BangumiClient
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
        return TestClient(create_app(database_path=self.database, metadata_source=provider))

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


if __name__ == '__main__':
    unittest.main()
