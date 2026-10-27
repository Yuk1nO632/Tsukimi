"""Automatic matching must reduce clicks without guessing another season."""
import json
from pathlib import Path
import tempfile
import unittest

import httpx
from fastapi.testclient import TestClient
from main import create_app
from matching import exact_source
from xifan import XifanSource

ANIME = "bgm-183878"
TITLE = "紫罗兰永恒花园"


class AutoSourceTests(unittest.TestCase):
    def setUp(self):
        root = self.enterContext(tempfile.TemporaryDirectory())
        self.database = Path(root) / "test.db"
        self.calls = []
        self.items = [{"id":100,"title":TITLE,"release_year":2018,"total_episodes":13}]
        self.missing = False
        self.timeout = False

    def handle(self, request):
        body = json.loads(request.content)
        self.calls.append((request.url.path, body))
        if self.timeout:
            raise httpx.ReadTimeout("test timeout",request=request)
        if request.url.path.endswith('search_animes'):
            return httpx.Response(200,json=self.items)
        if request.url.path.endswith('get_anime_detail'):
            if self.missing:
                return httpx.Response(404)
            return httpx.Response(200,json={"anime":{"id":body['p_id'],"title":TITLE},"sources":[
                {"id":10,"name":"主线","episodes":[{"id":1,"kind":"main","episode_number":1}]},
                {"id":20,"name":"备用","episodes":[{"id":1,"kind":"main","episode_number":1},{"id":2,"kind":"main","episode_number":2}]}]})
        return httpx.Response(200,json={"ok":True,"url":"https://play.xfvod.pro/test.mp4?sign=test-only"})

    def client(self):
        return TestClient(create_app(database_path=self.database,playback_source=XifanSource(transport=httpx.MockTransport(self.handle))))

    def searches(self):
        return sum(path.endswith('search_animes') for path,_ in self.calls)

    def test_auto_loads_and_reuses_match_across_episodes_and_selects_available_line(self):
        with self.client() as client:
            response=client.get(f'/api/playback/{ANIME}?episode=2')
            self.assertEqual(response.status_code,200)
            self.assertEqual(response.json()['match_kind'],'automatic')
            self.assertEqual(response.json()['source_anime_id'],100)
            self.assertEqual(response.json()['line_id'],20)
            self.assertEqual(self.searches(),1)
            client.get(f'/api/playback/{ANIME}?episode=1')
            self.assertEqual(self.searches(),1)
            self.assertEqual(sum(path.endswith('issue-web-playback') for path,_ in self.calls),2)

    def test_ambiguous_candidates_require_one_confirmation_and_do_not_resolve_video(self):
        self.items.append({**self.items[0],'id':101})
        with self.client() as client:
            data=client.get(f'/api/playback/{ANIME}').json()
            self.assertEqual(data['status'],'unmatched')
            self.assertEqual(len(data['candidates']),2)
            self.assertFalse(any(path.endswith('issue-web-playback') for path,_ in self.calls))

    def test_another_season_or_conflicting_year_is_never_automatically_selected(self):
        self.items=[{**self.items[0],'title':TITLE+' 第二季'},{**self.items[0],'id':101,'release_year':2020}]
        with self.client() as client:
            self.assertEqual(client.get(f'/api/playback/{ANIME}').json()['status'],'unmatched')
            self.assertFalse(any(path.endswith('get_anime_detail') for path,_ in self.calls))

    def test_manual_choice_survives_restart_and_is_scoped_to_browser(self):
        self.items.append({**self.items[0],'id':101})
        with self.client() as first, self.client() as second:
            first.get('/api/collection');second.get('/api/collection')
            self.assertEqual(first.put(f'/api/sources/xifan/bindings/{ANIME}',json={'source_anime_id':101}).status_code,200)
            self.assertEqual(first.get(f'/api/playback/{ANIME}').json()['source_anime_id'],101)
            self.assertEqual(second.get(f'/api/playback/{ANIME}').json()['status'],'unmatched')
            cookies=dict(first.cookies)
        before=self.searches()
        with self.client() as restarted:
            restarted.cookies.update(cookies)
            data=restarted.get(f'/api/playback/{ANIME}').json()
            self.assertEqual((data['source_anime_id'],data['match_kind']),(101,'saved'))
            self.assertEqual(self.searches(),before)

    def test_explicit_url_does_not_overwrite_saved_preference(self):
        with self.client() as client:
            client.get('/api/collection')
            client.put(f'/api/sources/xifan/bindings/{ANIME}',json={'source_anime_id':101})
            self.assertEqual(client.get(f'/api/playback/{ANIME}?source_anime_id=100').json()['match_kind'],'explicit')
            self.assertEqual(client.get(f'/api/playback/{ANIME}').json()['source_anime_id'],101)

    def test_binding_validation_and_origin_and_session_guards(self):
        with self.client() as client:
            endpoint=f'/api/sources/xifan/bindings/{ANIME}'
            self.assertEqual(client.put(endpoint,json={'source_anime_id':100}).status_code,401)
            client.get('/api/collection')
            self.assertEqual(client.put(endpoint,json={'source_anime_id':0}).status_code,422)
            self.assertEqual(client.put(endpoint,json={'source_anime_id':100},headers={'Origin':'https://other.example'}).status_code,403)

    def test_invalid_cached_auto_match_is_forgotten_and_retry_can_discover_new_id(self):
        with self.client() as client:
            client.get(f'/api/playback/{ANIME}')
        self.missing=True
        with self.client() as client:
            self.assertEqual(client.get(f'/api/playback/{ANIME}').status_code,404)
        self.missing=False
        self.items=[{**self.items[0],'id':102}]
        with self.client() as client:
            self.assertEqual(client.get(f'/api/playback/{ANIME}').json()['source_anime_id'],102)

    def test_timeout_returns_recoverable_error_instead_of_guessing(self):
        self.timeout=True
        with self.client() as client:
            self.assertEqual(client.get(f'/api/playback/{ANIME}').status_code,504)
        self.timeout=False
        with self.client() as client:
            self.assertEqual(client.get(f'/api/playback/{ANIME}').json()['status'],'ready')

    def test_generic_alias_does_not_hide_an_explicit_second_season(self):
        anime={'title':'测试番 第二季','originalTitle':'Test Season 2','aliases':'测试番','year':'2020','episodes':12}
        self.assertIsNone(exact_source(anime,[{'id':1,'title':'测试番','year':'2020','episodes':12}]))
        self.assertEqual(exact_source(anime,[{'id':2,'title':'测试番 第二季','year':'2020','episodes':12}]),2)
    def test_normalized_names_and_aliases_work_but_missing_year_needs_episode_evidence(self):
        anime={'title':'Re: Zero!','originalTitle':'','aliases':'从零开始 / Re：Zero','year':'2016','episodes':25}
        self.assertEqual(exact_source(anime,[{'id':1,'title':'Ｒｅ：Ｚｅｒｏ','year':'2016','episodes':12}]),1)
        self.assertEqual(exact_source(anime,[{'id':2,'title':'从零开始','year':'2016','episodes':25}]),2)
        self.assertIsNone(exact_source(anime,[{'id':3,'title':'Re: Zero!','year':'','episodes':12}]))
        self.assertEqual(exact_source(anime,[{'id':4,'title':'Re: Zero!','year':'','episodes':25}]),4)


if __name__=='__main__':unittest.main()
