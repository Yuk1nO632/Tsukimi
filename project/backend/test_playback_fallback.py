import sqlite3
from contextlib import closing
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from database import Database
from main import create_app
from source_errors import SourceError
from xifan import XifanSource

ANIME = 'bgm-400602'


class FakeSource:
    def __init__(self, name, identifier):
        self.name = name
        self.identifier = identifier
        self.state = 'ready'
        self.invalid = False
        self.calls = []

    def close(self):
        pass

    def search(self, query):
        return [{'id': self.identifier, 'title': '葬送的芙莉莲', 'year': '2023', 'episodes': 28}]

    def discover(self, anime):
        self.calls.append(('discover', anime['id']))
        if self.state == 'error':
            raise SourceError('接口未授权', 503)
        return (None, []) if self.state == 'unmatched' else (self.identifier, [])

    def validate_binding(self, anime, identifier):
        self.calls.append(('validate', identifier))
        if self.invalid:
            raise SourceError('作品身份不符', 409)

    def resolve(self, identifier, episode, line_id=None):
        self.calls.append(('resolve', identifier, episode, line_id))
        if self.state == 'resolve_error':
            raise SourceError('视频接口失败', 502)
        return {
            'provider': self.name, 'source_anime_id': identifier, 'line_id': line_id or 5,
            'status': self.state, 'url': 'https://cdn.example.com/video.mp4',
        }


class PlaybackFallbackTests(unittest.TestCase):
    def setUp(self):
        directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(directory) / 'test.db'
        self.primary = FakeSource('anich', 11)
        self.secondary = FakeSource('xifan', 77)
        self.app = create_app(database_path=self.path, playback_source=self.primary, fallback_source=self.secondary)
        self.client = self.enterContext(TestClient(self.app))

    def test_primary_success_does_not_contact_secondary(self):
        data = self.client.get(f'/api/playback/{ANIME}').json()
        self.assertEqual(data['provider'], 'anich')
        self.assertEqual(self.secondary.calls, [])

    def test_authorization_failure_automatically_uses_secondary(self):
        self.primary.state = 'error'
        data = self.client.get(f'/api/playback/{ANIME}').json()
        self.assertEqual((data['provider'], data['status'], data['fallback_from']), ('xifan', 'ready', 'anich'))
        self.assertEqual(Database(self.path).source_binding(f'xifan:{ANIME}'), (77, 'automatic'))
        self.assertIsNone(Database(self.path).source_binding(f'anich:{ANIME}')[0])

    def test_unmatched_and_unavailable_primary_can_fall_back(self):
        for state in ('unmatched', 'unavailable', 'resolve_error'):
            with self.subTest(state=state):
                self.primary.state = state
                data = self.client.get(f'/api/playback/{ANIME}').json()
                self.assertEqual(data['provider'], 'xifan')
                self.assertEqual(data['fallback_from'], 'anich')

    def test_explicit_ids_and_line_ids_are_not_reused_across_providers(self):
        self.primary.state = 'resolve_error'
        data = self.client.get(f'/api/playback/{ANIME}', params={
            'source_provider': 'anich', 'source_anime_id': 123, 'line_id': 999,
        }).json()
        self.assertEqual(data['provider'], 'xifan')
        self.assertIn(('resolve', 123, 1, 999), self.primary.calls)
        self.assertIn(('resolve', 77, 1, None), self.secondary.calls)

    def test_explicit_identity_conflict_is_reported(self):
        self.primary.invalid = True
        response = self.client.get(f'/api/playback/{ANIME}', params={
            'source_provider': 'anich', 'source_anime_id': 123,
        })
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.secondary.calls, [])

    def test_legacy_unscoped_numeric_ids_are_ignored(self):
        data = self.client.get(f'/api/playback/{ANIME}', params={'source_anime_id': 999, 'line_id': 888}).json()
        self.assertEqual(data['source_anime_id'], 11)
        self.assertIn(('resolve', 11, 1, None), self.primary.calls)

    def test_secondary_preference_search_and_owner_binding_are_isolated(self):
        self.client.get('/api/account')
        self.assertEqual(self.client.get('/api/sources/xifan/search', params={'q': '芙莉莲'}).json()['provider'], 'xifan')
        response = self.client.put(f'/api/sources/xifan/bindings/{ANIME}', json={'source_anime_id': 78})
        self.assertEqual(response.status_code, 200)
        data = self.client.get(f'/api/playback/{ANIME}', params={'source_provider': 'xifan'}).json()
        self.assertEqual((data['source_anime_id'], data['match_kind']), (78, 'saved'))
        self.assertEqual(self.primary.calls, [])
        remembered = self.client.get(f'/api/playback/{ANIME}').json()
        self.assertEqual((remembered['provider'], remembered['source_anime_id']), ('xifan', 78))
        with TestClient(self.app) as other:
            data = other.get(f'/api/playback/{ANIME}', params={'source_provider': 'xifan'}).json()
            self.assertEqual(data['source_anime_id'], 77)

    def test_progress_persists_provider_and_keeps_legacy_default(self):
        account = self.client.get('/api/account').json()
        payload = {
            'episode': 1, 'position': 30, 'duration': 120, 'source_provider': 'xifan',
            'source_id': 77, 'line_id': 5, 'revision': 0, 'operation_id': 'xifan-progress-operation',
            'scope': account['scope'],
        }
        response = self.client.put(f'/api/progress/{ANIME}', json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(f'/api/progress/{ANIME}').json()['item']['source_provider'], 'xifan')
        payload.update(revision=1, operation_id='legacy-progress-operation')
        payload.pop('source_provider')
        self.assertEqual(self.client.put(f'/api/progress/{ANIME}', json=payload).json()['item']['source_provider'], 'anich')
        payload['source_provider'] = 'unknown'
        self.assertEqual(self.client.put(f'/api/progress/{ANIME}', json=payload).status_code, 422)

    def test_both_provider_errors_still_return_actionable_error(self):
        self.primary.state = self.secondary.state = 'error'
        response = self.client.get(f'/api/playback/{ANIME}')
        self.assertEqual(response.status_code, 503)
        self.assertIn('未授权', response.json()['detail'])


class XifanAdapterTests(unittest.TestCase):
    def provider(self, url='https://play.xfvod.pro/video.mp4'):
        self.calls = []

        def handle(request):
            import json
            body = json.loads(request.content)
            self.calls.append((request.url.path, body))
            if request.url.path.endswith('search_animes'):
                return httpx.Response(200, json=[{'id': 588, 'title': '【我推的孩子】', 'release_year': 2023, 'total_episodes': 2}])
            if request.url.path.endswith('get_anime_detail'):
                return httpx.Response(200, json={
                    'anime': {'id': 588, 'title': '【我推的孩子】', 'release_year': 2023, 'total_episodes': 2},
                    'sources': [{'id': 5, 'name': '主线', 'episodes': [
                        {'id': 99, 'kind': 'special', 'episode_number': 99},
                        {'id': 1, 'kind': 'main', 'episode_number': 1.0},
                        {'id': 2, 'kind': 'main', 'episode_number': 2.0},
                    ]}],
                })
            return httpx.Response(200, json={'ok': True, 'url': url})

        provider = XifanSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        return provider

    def test_symbol_title_identity_float_episode_and_fresh_media_url(self):
        provider = self.provider()
        anime = {'id': 'bgm-386809', 'title': '【我推的孩子】', 'year': '2023', 'episodes': 2}
        self.assertEqual(provider.discover(anime)[0], 588)
        provider.validate_binding(anime, 588)
        data = provider.resolve(588, 1)
        self.assertEqual((data['status'], data['episode_count'], data['source_episode_id']), ('ready', 2, 1))
        provider.resolve(588, 2)
        self.assertEqual(sum(path.endswith('issue-web-playback') for path, body in self.calls), 2)
        self.assertEqual(self.calls[-1][1]['episode_id'], 2)

    def test_direct_media_hosts_and_invalid_ports(self):
        for host in ('play.xfvod.pro', 'dl.playxf.top'):
            with self.subTest(host=host):
                self.assertEqual(self.provider(f'https://{host}/video.mp4').resolve(588, 1)['status'], 'ready')
        self.assertEqual(self.provider('https://play.xfvod.pro:8088/video.mp4').resolve(588, 1)['status'], 'ready')
        for url in ('https://apn.moedot.net/video.mp4', 'https://hydownload.pan.wo.cn/video.mp4', 'http://play.xfvod.pro/video.mp4', 'https://play.xfvod.pro:99999/video.mp4',
                    'https://play.xfvod.pro:bad/video.mp4', 'https://user@play.xfvod.pro/video.mp4',
                    'https://play.xfvod.pro.evil.test/video.mp4'):
            with self.subTest(url=url), self.assertRaises(SourceError):
                self.provider(url).resolve(588, 1)

    def test_usable_candidate_is_selected_after_unsupported_primary_url(self):
        provider = self.provider()
        original = provider._post
        def response(path, body):
            if path.endswith('issue-web-playback'):
                return {'ok': True, 'url': 'https://unknown.test/bad.mp4', 'candidates': [None,
                    {'url': 'https://dl.playxf.top/good.m3u8'}]}
            return original(path, body)
        with patch.object(provider, '_post', side_effect=response):
            result = provider.resolve(588, 1)
        self.assertEqual((result['url'], result['format']), ('https://dl.playxf.top/good.m3u8', 'hls'))

    def test_automatic_line_can_fall_back_but_explicit_selection_is_respected(self):
        provider = self.provider()
        detail = provider.detail(588)
        detail['sources'].append({'id': 6, 'name': '备用', 'episodes': [{'id': 3, 'kind': 'main', 'episode_number': 1}]})
        original = provider._post
        def response(path, body):
            if path.endswith('issue-web-playback'):
                host = 'unknown.test' if body['source_id'] == 5 else 'play.xfvod.pro'
                return {'ok': True, 'url': f'https://{host}/video.mp4'}
            return original(path, body)
        with patch.object(provider, '_post', side_effect=response):
            self.assertEqual(provider.resolve(588, 1)['line_id'], 6)
            with self.assertRaises(SourceError):
                provider.resolve(588, 1, 5)

    def test_wrong_identity_unsafe_url_missing_episode_and_line(self):
        provider = self.provider('https://127.0.0.1/private.mp4')
        with self.assertRaises(SourceError):
            provider.validate_binding({'title': '另一部作品', 'year': '2023'}, 588)
        with self.assertRaises(SourceError):
            provider.resolve(588, 1)
        self.assertEqual(provider.resolve(588, 3)['status'], 'unavailable')
        with self.assertRaises(SourceError):
            provider.resolve(588, 1, 999)


class ProviderMigrationTests(unittest.TestCase):
    def test_legacy_progress_is_backed_up_and_defaults_to_anich(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'legacy.db'
            with closing(sqlite3.connect(path)) as connection:
                connection.execute('CREATE TABLE owners (id TEXT PRIMARY KEY)')
                connection.execute("INSERT INTO owners VALUES ('owner')")
                connection.execute('''CREATE TABLE watch_progress (
                    owner_id TEXT, anime_id TEXT, episode INTEGER, position REAL, duration REAL,
                    source_id INTEGER, line_id INTEGER, completed INTEGER, revision INTEGER,
                    updated_at INTEGER, operation_id TEXT, PRIMARY KEY(owner_id, anime_id))''')
                connection.execute('INSERT INTO watch_progress VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                                   ('owner', ANIME, 2, 30, 120, 11, 5, 0, 7, 123, 'old-operation'))
                connection.commit()
            store = Database(path)
            store.initialize()
            store.initialize()
            item = store.progress('owner', ANIME)
            self.assertEqual((item['source_provider'], item['position'], item['revision']), ('anich', 30, 7))
            backup = path.with_suffix('.pre-source-providers.db')
            self.assertTrue(backup.exists())
            with closing(sqlite3.connect(backup)) as connection:
                self.assertNotIn('source_provider', {row[1] for row in connection.execute('PRAGMA table_info(watch_progress)')})
                self.assertEqual(connection.execute('SELECT position FROM watch_progress').fetchone()[0], 30)
