"""AniCh protocol, candidate safety, stable lines and provider migration contracts."""
import base64
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

import httpx
from fastapi.testclient import TestClient

from anich import AniChSource, public_media_url
from anich_protocol import fields, decode_url
from database import Database
from main import create_app
from source_errors import SourceError


def varint(n):
    result = bytearray()
    while n > 127:
        result.append((n & 127) | 128)
        n >>= 7
    return bytes(result + bytes([n]))


def field(n, value):
    if isinstance(value, int):
        return varint(n << 3) + varint(value)
    value = value.encode() if isinstance(value, str) else value
    return varint((n << 3) | 2) + varint(len(value)) + value


def encoded(url):
    value = base64.b64encode(url.encode()).decode()
    return value[:3] + 'A' + value[3:]


class AniChTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory())
        self.path = Path(self.directory) / 'test.db'
        self.calls = []
        self.bgm = '400602'
        self.fail = None
        self.episode2_missing = False
        self.rows = [('main', '葬送的芙莉莲', 'H.264', 'https://cdn.example.com/ep.mp4'),
                     ('main', '葬送的芙莉莲', 'H.264', 'https://mirror.example.com/ep.mp4'),
                     ('other', '葬送的芙莉莲', 'H.264', 'https://cdn.example.com/other.m3u8'),
                     ('hevc', '葬送的芙莉莲', 'H.265/HEVC', 'https://cdn.example.com/hevc.mp4'),
                     ('wrong', '葬送的芙莉莲 第二季', 'H.264', 'https://cdn.example.com/wrong.mp4')]
        self.provider = AniChSource(transport=httpx.MockTransport(self.handle))
        self.addCleanup(self.provider.close)

    def handle(self, request):
        self.calls.append(request.url.path)
        if self.fail == 'timeout':
            raise httpx.ReadTimeout('test', request=request)
        if self.fail == 'limited':
            return httpx.Response(429)
        if self.fail == 'bad-wire':
            return httpx.Response(200, content=b'\x12\x05x')
        if self.fail == 'oversize':
            return httpx.Response(200, content=b'x' * (2 * 1024 * 1024 + 1))
        path = request.url.path
        if path.endswith('/search'):
            return httpx.Response(200, content=field(1, field(1, 32339) + field(2, '葬送的芙莉莲') + field(4, 28)))
        if '/detail/' in path:
            return httpx.Response(200, json={'id': int(path.split('/')[-1]), 'title': '葬送的芙莉莲',
                'titles': ['葬送のフリーレン'], 'airdate': 1695996000000,
                'sites': [{'site': 'bangumi', 'id': self.bgm}] if self.bgm else []})
        if '/episodes/' in path:
            return httpx.Response(200, content=b''.join(field(1, field(1, 1) + field(2, n)) for n in [1, 2]))
        ep = int(path.split('/')[-1])
        payload = b''
        for label, title, codec, url in self.rows:
            if self.episode2_missing and ep == 2 and label == 'main':
                continue
            # Same group ID across episodes and renewed URL on every resolve.
            url += f'?ep={ep}&issue={len(self.calls)}'
            payload += field(1, field(1, encoded(url)) + field(2, ep) + field(4, f'第{ep}集') + field(5, label)
                             + field(6, f'{title} · 1920x1080 · {codec}'))
        return httpx.Response(200, json=list(payload))

    def client(self):
        return TestClient(create_app(database_path=self.path, playback_source=self.provider))

    def test_discovery_prefers_verified_bangumi_link_and_filters_mixed_season(self):
        with self.client() as client:
            data = client.get('/api/playback/bgm-400602').json()
            self.assertEqual((data['provider'], data['source_anime_id'], data['match_kind']), ('anich', 32339, 'automatic'))
            self.assertEqual(data['filtered_candidates'], 1)
            self.assertEqual(len(data['lines']), 3)
            self.assertEqual(data['line_name'], 'main · 1080P · H.264')
            self.assertNotIn('wrong', str(data))

    def test_different_bangumi_link_never_auto_selected_or_manually_saved(self):
        self.bgm = '999'
        with self.client() as client:
            self.assertEqual(client.get('/api/playback/bgm-400602').json()['status'], 'unmatched')
            client.get('/api/collection')
            self.assertEqual(client.put('/api/sources/anich/bindings/bgm-400602', json={'source_anime_id': 32339}).status_code, 409)
            self.assertFalse(any('/vod/' in path for path in self.calls))

    def test_legacy_db_and_url_ids_do_not_become_anich_ids(self):
        store = Database(self.path)
        store.initialize()
        store.save_source_binding('bgm-400602', 26)
        with self.client() as client:
            data = client.get('/api/playback/bgm-400602?source_anime_id=26&line_id=5').json()
            self.assertEqual(data['source_anime_id'], 32339)
            self.assertNotIn('/bangumi/detail/26', self.calls)
            self.assertEqual(store.source_binding('bgm-400602')[0], 26)
            self.assertEqual(store.source_binding('anich:bgm-400602')[0], 32339)

    def test_line_id_stable_and_signed_url_refreshed_on_next_episode(self):
        first = self.provider.resolve(32339, 1)
        second = self.provider.resolve(32339, 2, first['line_id'])
        self.assertEqual(first['line_id'], second['line_id'])
        self.assertNotEqual(first['url'], second['url'])
        self.assertEqual(sum('/vod/' in path for path in self.calls), 2)
        self.assertEqual(sum('/detail/' in path for path in self.calls), 1)

    def test_unavailable_line_returns_current_choices_instead_of_silently_switching(self):
        first = self.provider.resolve(32339, 1)
        self.episode2_missing = True
        data = self.provider.resolve(32339, 2, first['line_id'])
        self.assertEqual(data['status'], 'unavailable')
        self.assertEqual(len(data['lines']), 2)
        self.assertNotIn('url', data)

    def test_invalid_media_urls_skipped_and_known_codec_ranked_first(self):
        self.rows += [('bad', '葬送的芙莉莲', 'H.264', 'http://localhost/video.mp4')]
        data = self.provider.resolve(32339, 1)
        self.assertEqual(data['filtered_candidates'], 2)
        self.assertIn('H.264', data['line_name'])
        self.assertEqual(data['lines'][-1]['name'], 'hevc · 1080P · HEVC')

    def test_missing_episode_does_not_fetch_vod(self):
        self.assertEqual(self.provider.resolve(32339, 3)['status'], 'unavailable')
        self.assertFalse(any('/vod/' in path for path in self.calls))

    def test_source_errors_are_actionable_and_not_cached(self):
        for failure, code in [('timeout', 504), ('limited', 503), ('bad-wire', 502), ('oversize', 502)]:
            self.fail = failure
            with self.assertRaises(SourceError) as error:
                self.provider.search('new-' + failure)
            self.assertEqual(error.exception.status_code, code)
        self.fail = None
        self.assertEqual(self.provider.search('new-timeout')[0]['id'], 32339)

    def test_manual_binding_survives_restart_isolated_from_other_browser(self):
        with self.client() as first, self.client() as second:
            first.get('/api/collection'); second.get('/api/collection')
            first.put('/api/sources/anich/bindings/bgm-400602', json={'source_anime_id': 32339})
            cookies = dict(first.cookies)
            self.assertEqual(first.get('/api/playback/bgm-400602').json()['match_kind'], 'saved')
            self.assertEqual(second.get('/api/playback/bgm-400602').json()['match_kind'], 'automatic')
        with self.client() as restarted:
            restarted.cookies.update(cookies)
            self.assertEqual(restarted.get('/api/playback/bgm-400602').json()['match_kind'], 'saved')

    def test_bad_origin_and_unsigned_session_rejected(self):
        with self.client() as client:
            self.assertEqual(client.put('/api/sources/anich/bindings/bgm-400602', json={'source_anime_id': 32339}).status_code, 401)
            client.get('/api/collection')
            self.assertEqual(client.put('/api/sources/anich/bindings/bgm-400602', json={'source_anime_id': 32339}, headers={'Origin':'https://other.example'}).status_code, 403)
            self.assertEqual(client.put('/api/sources/anich/bindings/bgm-400602', json={'source_anime_id': 0}).status_code, 422)

    def test_default_prefers_verified_mp4_cdn_then_higher_resolution(self):
        self.rows = [('low', '葬送的芙莉莲', 'H.264', 'https://v1.adkwai.com/low.mp4'),
                     ('high', '葬送的芙莉莲', 'H.264', 'https://v1.adkwai.com/high.mp4')]
        # Alter the fixture description only, leaving the URL and group IDs independent.
        original = self.handle
        def handle(request):
            response = original(request)
            if '/vod/' in request.url.path:
                raw = bytes(response.json()).replace(b'1920x1080', b'0854x0480', 1)
                return httpx.Response(200, json=list(raw))
            return response
        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        result = provider.resolve(32339, 1)
        self.assertEqual(result['line_name'], 'high · 1080P · H.264')

    def test_current_search_endpoint_and_retired_endpoint_removed(self):
        with self.client() as client:
            data = client.get('/api/sources/anich/search', params={'q': '芙莉莲'}).json()
            self.assertEqual(data['items'][0]['id'], 32339)
            self.assertEqual(client.get('/api/sources/anich/search', params={'q': ' '}).status_code, 400)
            paths = client.get('/openapi.json').json()['paths']
            self.assertTrue(all('/sources/anich/' in path for path in paths if '/sources/' in path))

    def test_invalid_playback_parameters_rejected_before_provider_call(self):
        with self.client() as client:
            for url, status in [('/api/playback/unknown', 404),
                                ('/api/playback/bgm-400602?episode=29', 404),
                                ('/api/playback/bgm-400602?episode=0', 422),
                                ('/api/playback/bgm-400602?source_anime_id=-1', 422)]:
                self.assertEqual(client.get(url).status_code, status)
            self.assertEqual(self.calls, [])

    def test_explicit_choice_does_not_overwrite_saved_binding_and_response_not_cached(self):
        with self.client() as client:
            client.get('/api/collection')
            client.put('/api/sources/anich/bindings/bgm-400602', json={'source_anime_id':32339})
            response = client.get('/api/playback/bgm-400602?source_provider=anich&source_anime_id=32340')
            self.assertEqual(response.json()['source_anime_id'], 32340)
            self.assertEqual(response.headers['cache-control'], 'no-store')
            self.assertTrue(all('url' in line for line in response.json()['lines']))
            self.assertEqual(client.get('/api/playback/bgm-400602').json()['source_anime_id'], 32339)

    def test_stale_auto_binding_cleared_so_retry_discovers_again(self):
        store = Database(self.path);store.initialize()
        store.save_source_binding('anich:bgm-400602', 999)
        original = self.handle
        def handle(request):
            return httpx.Response(404) if request.url.path.endswith('/detail/999') else original(request)
        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        with TestClient(create_app(database_path=self.path, playback_source=provider)) as client:
            self.assertEqual(client.get('/api/playback/bgm-400602').status_code, 404)
            self.assertEqual(store.source_binding('anich:bgm-400602')[0], None)
            self.assertEqual(client.get('/api/playback/bgm-400602').json()['source_anime_id'], 32339)

    def test_wire_truncation_unknown_fields_and_url_rule(self):
        self.assertEqual(list(fields(field(99, 'unknown') + field(1, 2))), [(99,b'unknown'),(1,2)])
        for payload in [b'\0', b'\x08\x80', b'\x12\x05x', b'\xff'*11]:
            with self.assertRaises(ValueError): list(fields(payload))
        self.assertEqual(decode_url(encoded('https://cdn.example.com/test.mp4')), 'https://cdn.example.com/test.mp4')
        for url in ['http://cdn.example.com/a', 'https://127.0.0.1/a', 'https://user:pass@cdn.example.com/a', 'https://cdn.example.com:8080/a', 'https://[::1]/a']:
            self.assertFalse(public_media_url(url))