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
        self.source_failure = None
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
        if self.source_failure == 'timeout':
            raise httpx.ReadTimeout('test', request=request)
        if self.source_failure == 'limited':
            return httpx.Response(429)
        if self.source_failure == 'bad-wire':
            return httpx.Response(200, content=b'\x12\x05x')
        if self.source_failure == 'oversize':
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
            self.source_failure = failure
            with self.assertRaises(SourceError) as error:
                self.provider.search('new-' + failure)
            self.assertEqual(error.exception.status_code, code)
        self.source_failure = None
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

    def test_bocchi_terminal_punctuation_lookup_matches_verified_first_episode(self):
        keywords = []
        def handle(request):
            path = request.url.path
            if path.endswith('/search'):
                keyword = request.url.params['keyword']
                keywords.append(keyword)
                if keyword != '孤独摇滚':
                    return httpx.Response(500)
                return httpx.Response(200, content=field(1, field(1, 31764) + field(2, '孤独摇滚！') + field(4, 12))
                    + field(1, field(1, 33380) + field(2, '剧场总集篇 孤独摇滚！ Re:') + field(4, 1)))
            if path == '/bangumi/detail/31764':
                return httpx.Response(200, json={'id': 31764, 'title': '孤独摇滚！', 'titles': ['ぼっち・ざ・ろっく！'],
                    'sites': [{'site': 'bangumi', 'id': '328609'}]})
            if path == '/bangumi/detail/33380':
                return httpx.Response(200, json={'id': 33380, 'title': '剧场总集篇 孤独摇滚！ Re:',
                    'sites': [{'site': 'bangumi', 'id': '400602'}]})
            if path == '/bangumi/episodes/31764':
                return httpx.Response(200, content=field(1, field(1, 1) + field(2, 1)))
            if path == '/vod/31764/1':
                payload = field(1, field(1, encoded('https://cdn.example.com/bocchi-01.mp4')) + field(2, 1)
                    + field(4, '第 1 集') + field(5, 'main') + field(6, '孤独摇滚！ · 1920x1080 · H.264'))
                return httpx.Response(200, json=list(payload))
            raise AssertionError('Unexpected source request: ' + path)
        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        with TestClient(create_app(database_path=self.path, playback_source=provider)) as client:
            response = client.get('/api/playback/bgm-328609')
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual((data['status'], data['source_anime_id'], data['source_title'], data['episode_title']),
                ('ready', 31764, '孤独摇滚！', '第 1 集'))
            self.assertEqual(data['format'], 'mp4')
            # Manual source lookup shares the normalized cache and returns original titles.
            items = client.get('/api/sources/anich/search', params={'q': '孤独摇滚！！'}).json()['items']
            self.assertEqual(items[0]['title'], '孤独摇滚！')
            self.assertEqual(keywords, ['孤独摇滚'])

    def test_search_keyword_cleanup_preserves_internal_symbols_and_rejects_empty(self):
        keywords = []
        def handle(request):
            keywords.append(request.url.params['keyword'])
            return self.handle(request)
        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        provider.search("  BanG Dream! It's MyGO!!!!!  ")
        provider.search("BanG Dream! It's MyGO")
        provider.search('Fate/stay night')
        provider.search('作品？')
        provider.search('摇曳露营△')
        self.assertEqual(keywords, ["BanG Dream! It's MyGO", 'Fate/stay night', '作品', '摇曳露营'])
        with self.assertRaises(SourceError) as caught:
            provider.search('  ！?！！  ')
        self.assertEqual(caught.exception.status_code, 400)
        self.assertEqual(len(keywords), 4)

    def test_current_search_endpoint_and_retired_endpoint_removed(self):
        with self.client() as client:
            data = client.get('/api/sources/anich/search', params={'q': '芙莉莲'}).json()
            self.assertEqual(data['items'][0]['id'], 32339)
            self.assertEqual(client.get('/api/sources/anich/search', params={'q': ' '}).status_code, 400)
            paths = client.get('/openapi.json').json()['paths']
            self.assertTrue(any('/sources/{source_provider}/' in path for path in paths))

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
    def test_special_search_recovers_from_full_title_500_and_checks_bangumi_id(self):
        keywords=[]
        def handle(request):
            path=request.url.path
            if path.endswith('/search'):
                keywords.append(request.url.params['keyword'])
                if request.url.params['keyword'] != '伪恋':
                    return httpx.Response(500)
                return httpx.Response(200,content=b''.join(field(1,field(1,i)+field(2,title)+field(4,count))
                    for i,title,count in [(24954,'伪恋',20),(24945,'伪恋 特别篇',5)]))
            if '/detail/' in path:
                identifier=int(path.split('/')[-1])
                return httpx.Response(200,json={'id':identifier,'title':'伪恋 特别篇' if identifier==24945 else '伪恋',
                    'titles':['伪恋OAD'] if identifier==24945 else [],'sites':[{'site':'bangumi','id':'104196' if identifier==24945 else '74628'}]})
            return httpx.Response(404)
        provider=AniChSource(transport=httpx.MockTransport(handle));self.addCleanup(provider.close)
        anime={'id':'bgm-104196','title':'伪恋 OAD','originalTitle':'ニセコイ OAD','aliases':'Nisekoi OAD','episodes':4,'year':'2014'}
        self.assertEqual(provider.discover(anime)[0],24945)
        self.assertEqual(provider.search('伪恋 OAD')[1]['id'],24945)
        # A separate manual lookup retries its full term, then reuses the broad-term cache.
        self.assertEqual(keywords,['伪恋 OAD','伪恋','伪恋 OAD'])
        anime['id']='bgm-999'
        self.assertIsNone(provider.discover(anime)[0])

    def test_special_episode_zero_type_uses_its_sort_without_losing_main_series(self):
        original=self.handle
        def handle(request):
            if '/episodes/' in request.url.path:
                return httpx.Response(200,content=field(1,field(1,0)+field(2,1))+field(1,field(2,2)))
            return original(request)
        provider=AniChSource(transport=httpx.MockTransport(handle));self.addCleanup(provider.close)
        self.assertEqual(provider.resolve(32339,2)['status'],'ready')
        self.assertTrue(any(path.endswith('/vod/32339/2') for path in self.calls))

    def test_mixed_series_does_not_treat_special_as_main_episode(self):
        original=self.handle
        def handle(request):
            if '/episodes/' in request.url.path:
                return httpx.Response(200,content=field(1,field(1,1)+field(2,1))+field(1,field(1,0)+field(2,2)))
            return original(request)
        provider=AniChSource(transport=httpx.MockTransport(handle));self.addCleanup(provider.close)
        result=provider.resolve(32339,2)
        self.assertEqual(result['reason'],'episode_missing')
        self.assertFalse(any('/vod/' in path for path in self.calls))

    def test_upstream_empty_candidates_is_distinct_from_filtered_or_missing_line(self):
        original=self.handle
        def handle(request):
            if '/vod/' in request.url.path:return httpx.Response(200,json=[])
            return original(request)
        provider=AniChSource(transport=httpx.MockTransport(handle));self.addCleanup(provider.close)
        result=provider.resolve(32339,2)
        self.assertEqual(result['reason'],'no_resources')
        self.assertEqual(result['source_anime_id'],32339)
        self.assertIn('没有返回',result['message'])
        self.assertNotIn('url',result)
        self.rows=[('wrong','无关作品','H.264','https://cdn.example.com/wrong.mp4')]
        self.assertEqual(self.provider.resolve(32339,1)['reason'],'unverified_resources')

    def test_fine_subtitle_search_and_zero_number_feature_keep_full_identity(self):
        keywords=[]
        def handle(request):
            path=request.url.path
            if path.endswith('/search'):
                keyword=request.url.params['keyword']; keywords.append(keyword)
                if keyword != '路人女主的养成方法':return httpx.Response(500)
                return httpx.Response(200,content=field(1,field(1,15261)+field(2,'路人女主的养成方法 Fine')+field(4,1)))
            if '/detail/' in path:
                return httpx.Response(200,json={'id':15261,'title':'路人女主的养成方法 Fine','titles':['路人女主的养成方法 剧场版'],
                    'episodes_total':1,'sites':[{'site':'bangumi','id':'231497'}]})
            if '/episodes/' in path:
                return httpx.Response(200,content=field(1,field(1,1)+field(2,1)))
            rows=[]
            for index,(title,label,episode) in enumerate([
                ('路人女主的养成方法 Fine','全集 · 1080P',0),
                ('路人女主的养成方法 Fine','正片 · 1080P',0),
                ('路人女主的养成方法 剧场版','路人女主的养成方法Fine · 1080P',0),
                ('路人女主的养成方法','正片 · 1080P',0),
                ('路人女主的养成方法 Fine','预告片',0),
                ('路人女主的养成方法 Fine','正片',2)]):
                rows.append(field(1,field(1,encoded('https://cdn.example.com/feature.mp4'))+(field(2,episode) if episode or index else b'')+
                    field(4,label)+field(5,'line-'+str(index))+field(6,title+' · H.264')))
            return httpx.Response(200,json=list(b''.join(rows)))
        provider=AniChSource(transport=httpx.MockTransport(handle));self.addCleanup(provider.close)
        anime={'id':'bgm-231497','title':'路人女主的养成方法 Fine','episodes':1,'year':'2019'}
        self.assertEqual(provider.discover(anime)[0],15261)
        result=provider.resolve(15261,1)
        self.assertEqual(result['status'],'ready')
        self.assertEqual(len(result['lines']),3)
        self.assertEqual(result['filtered_candidates'],3)
        self.assertEqual(keywords,['路人女主的养成方法 Fine','路人女主的养成方法'])

    def test_zero_sort_is_rejected_for_multiepisode_series(self):
        original=self.handle
        def handle(request):
            response=original(request)
            if '/detail/' in request.url.path:
                return httpx.Response(200,json={**response.json(),'episodes_total':28})
            if '/vod/' in request.url.path:
                return httpx.Response(200,json=list(field(1,field(1,encoded('https://cdn.example.com/main.mp4'))+
                    field(2,0)+field(4,'正片')+field(5,'line')+field(6,'葬送的芙莉莲 · H.264'))))
            return response
        provider=AniChSource(transport=httpx.MockTransport(handle));self.addCleanup(provider.close)
        result=provider.resolve(32339,1)
        self.assertEqual(result['status'],'unavailable')
        self.assertEqual(result['reason'],'unverified_resources')

    def test_series_recall_checks_official_ids_even_when_summary_name_differs(self):
        keywords = []
        titles = {2: '无职转生 第二季', 3: '無職転生Ⅲ', 4: '无职转生 特别篇'}

        def handle(request):
            if request.url.path.endswith('/search'):
                keyword = request.url.params['keyword']
                keywords.append(keyword)
                if keyword != '无职转生':
                    return httpx.Response(500)
                rows = b''.join(field(1, field(1, identifier) + field(2, title) + field(4, 14))
                                for identifier, title in titles.items())
                return httpx.Response(200, content=rows)
            identifier = int(request.url.path.split('/')[-1])
            return httpx.Response(200, json={
                'id': identifier, 'title': titles[identifier], 'titles': [],
                'sites': [{'site': 'bangumi', 'id': '501963' if identifier in (2, 3) else '999'}],
            })

        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        anime = {
            'id': 'bgm-501963', 'title': '无职转生 第三季 ～到了异世界就拿出真本事～',
            'originalTitle': '無職転生Ⅲ ～異世界行ったら本気だす～', 'year': '2026', 'episodes': 14,
        }
        self.assertEqual(provider.discover(anime)[0], 3)
        self.assertEqual(keywords, ['无职转生 第三季 ～到了异世界就拿出真本事～', '无职转生'])

    def test_conflicting_official_year_and_duplicate_verified_candidates_need_confirmation(self):
        def handle(request):
            if request.url.path.endswith('/search'):
                rows = b''.join(field(1, field(1, identifier) + field(2, '另一译名' + str(identifier)))
                                for identifier in (1, 2))
                return httpx.Response(200, content=rows)
            identifier = int(request.url.path.split('/')[-1])
            return httpx.Response(200, json={
                'id': identifier, 'title': '另一译名' + str(identifier),
                'sites': [{'site': 'bangumi', 'id': '501963'}],
            })

        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        anime = {'id': 'bgm-501963', 'title': '完全不同的显示名称', 'year': '2026', 'episodes': 14}
        self.assertIsNone(provider.discover(anime)[0])
        self.assertEqual(len(provider._cache), 3)

        def conflicting(request):
            response = handle(request)
            if '/detail/' in request.url.path:
                return httpx.Response(200, json={**response.json(), 'airdate': 1695996000000})
            return response

        other = AniChSource(transport=httpx.MockTransport(conflicting))
        self.addCleanup(other.close)
        self.assertIsNone(other.discover(anime)[0])

    def test_official_identity_with_conflicting_cour_needs_confirmation(self):
        def handle(request):
            if request.url.path.endswith('/search'):
                return httpx.Response(200, content=field(1, field(1, 9) + field(2, '测试作品Ⅱ 第1部分')))
            return httpx.Response(200, json={
                'id': 9, 'title': '测试作品Ⅱ 第1部分',
                'sites': [{'site': 'bangumi', 'id': '501963'}],
            })

        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        anime = {'id': 'bgm-501963', 'title': '测试作品Ⅱ 第2部分', 'year': '2026', 'episodes': 12}
        self.assertIsNone(provider.discover(anime)[0])

    def test_later_alias_can_recall_identity_after_unrelated_search_results(self):
        details = []

        def handle(request):
            if request.url.path.endswith('/search'):
                identifiers = [99] if request.url.params['keyword'] == '作品别名' else range(1, 9)
                rows = b''.join(field(1, field(1, identifier) + field(2, '其他名称' + str(identifier)))
                                for identifier in identifiers)
                return httpx.Response(200, content=rows)
            identifier = int(request.url.path.split('/')[-1])
            details.append(identifier)
            return httpx.Response(200, json={
                'id': identifier, 'title': '其他名称' + str(identifier),
                'sites': [{'site': 'bangumi', 'id': '501963' if identifier == 99 else '999'}],
            })

        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        anime = {'id': 'bgm-501963', 'title': '测试作品', 'aliases': '作品别名', 'year': '2026', 'episodes': 14}
        self.assertEqual(provider.discover(anime)[0], 99)
        self.assertEqual(len(details), 9)
        self.assertEqual(len(set(details)), 9)

    def test_symbol_queries_verify_main_series_when_special_shares_official_id(self):
        cases = [
            ('Re：从零开始的异世界生活', '从零开始的异世界生活'),
            ('【我推的孩子】', '我推的孩子'),
            ('中二病也要谈恋爱！恋', '中二病也要谈恋爱'),
            ('无头骑士异闻录×2 承', '无头骑士异闻录'),
        ]
        for title, keyword in cases:
            with self.subTest(title=title):
                def handle(request):
                    if request.url.path.endswith('/search'):
                        if request.url.params['keyword'] != keyword:
                            return httpx.Response(500)
                        return httpx.Response(200, content=
                            field(1, field(1, 10) + field(2, title + ' 特别篇')) +
                            field(1, field(1, 11) + field(2, title)))
                    identifier = int(request.url.path.split('/')[-1])
                    return httpx.Response(200, json={
                        'id': identifier, 'title': title + (' 特别篇' if identifier == 10 else ''),
                        'sites': [{'site': 'bangumi', 'id': '12345'}],
                    })

                provider = AniChSource(transport=httpx.MockTransport(handle))
                self.addCleanup(provider.close)
                anime = {'id': 'bgm-12345', 'title': title, 'year': '2023', 'platform': 'TV'}
                self.assertEqual(provider.discover(anime)[0], 11)

    def test_standalone_special_keeps_automatic_identity_verification(self):
        def handle(request):
            if request.url.path.endswith('/search'):
                return httpx.Response(200, content=field(1, field(1, 10) + field(2, '作品 特别篇')))
            return httpx.Response(200, json={
                'id': 10, 'title': '作品 特别篇',
                'sites': [{'site': 'bangumi', 'id': '12345'}],
            })

        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        for anime in [
            {'id': 'bgm-12345', 'title': '作品 OAD'},
            {'id': 'bgm-12345', 'title': '作品', 'platform': 'OVA'},
        ]:
            with self.subTest(anime=anime):
                self.assertEqual(provider.discover(anime)[0], 10)

    def test_access_denial_stops_discovery_without_trying_more_keywords(self):
        requests = []

        def handle(request):
            requests.append(request.url.params['keyword'])
            return httpx.Response(403)

        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        with self.assertRaises(SourceError) as raised:
            provider.discover({'id': 'bgm-12345', 'title': '测试作品 第二季', 'aliases': '另一个名字'})
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(requests, ['测试作品 第二季'])

    def test_detail_access_denial_stops_remaining_identity_probes(self):
        requests = []

        def handle(request):
            requests.append(request.url.path)
            if request.url.path.endswith('/search'):
                return httpx.Response(200, content=
                    field(1, field(1, 10) + field(2, '测试作品')) +
                    field(1, field(1, 11) + field(2, '测试作品 第二季')))
            return httpx.Response(403)

        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        with self.assertRaises(SourceError) as raised:
            provider.discover({'id': 'bgm-12345', 'title': '测试作品'})
        self.assertEqual(raised.exception.status_code, 503)
        self.assertEqual(len(requests), 2)

    def test_discovery_does_not_repeat_failed_fallback_keywords(self):
        keywords = []

        def handle(request):
            keywords.append(request.url.params['keyword'])
            return httpx.Response(500)

        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        with self.assertRaises(SourceError):
            provider.discover({
                'id': 'bgm-12345', 'title': '测试作品！恋',
                'originalTitle': '测试作品!恋', 'aliases': '测试作品 / 测试作品！',
            })
        self.assertEqual(keywords, ['测试作品！恋', '测试作品', '测试作品!恋'])

    def test_json_unauthorized_stops_discovery_even_when_upstream_status_is_500(self):
        for status in (200, 401, 500):
            with self.subTest(status=status):
                keywords = []

                def handle(request):
                    keywords.append(request.url.params['keyword'])
                    return httpx.Response(status, json={'error': True, 'message': 'unauthorized', 'body': {}})

                provider = AniChSource(transport=httpx.MockTransport(handle))
                self.addCleanup(provider.close)
                with self.assertRaises(SourceError) as raised:
                    provider.discover({'id': 'bgm-386809', 'title': '【我推的孩子】', 'aliases': 'Oshi no Ko'})
                self.assertEqual(raised.exception.status_code, 503)
                self.assertIn('未授权', str(raised.exception))
                self.assertEqual(keywords, ['我推的孩子'])

    def test_non_auth_server_errors_keep_title_fallback(self):
        keywords = []

        def handle(request):
            keyword = request.url.params['keyword']
            keywords.append(keyword)
            if keyword != '作品名称':
                return httpx.Response(500, json={'error': True, 'message': 'internal error'})
            return httpx.Response(200, content=field(1, field(1, 32094) + field(2, '作品名称：副标题')))

        provider = AniChSource(transport=httpx.MockTransport(handle))
        self.addCleanup(provider.close)
        self.assertEqual(provider.search('作品名称：副标题')[0]['id'], 32094)
        self.assertEqual(keywords, ['作品名称：副标题', '作品名称'])
