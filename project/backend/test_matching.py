"""Provider-independent name, alias and season evidence used by AniCh fallback."""
import unittest
from matching import exact_source, special_search_title, fallback_search_title, discovery_queries, season_number, part_number, search_keyword


class MatchingTests(unittest.TestCase):
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

    def test_special_query_simplification_preserves_season_numbers_and_regular_titles(self):
        self.assertEqual(special_search_title('伪恋 OAD'),'伪恋')
        self.assertEqual(special_search_title('伪恋OAD'),'伪恋')
        self.assertEqual(special_search_title('伪恋 特别篇'),'伪恋')
        self.assertEqual(special_search_title('测试 第二季 OVA'),'测试 第二季')
        self.assertEqual(special_search_title('ROAD'),'ROAD')

    def test_latin_subtitle_search_does_not_change_regular_english_names(self):
        self.assertEqual(fallback_search_title('路人女主的养成方法 Fine'),'路人女主的养成方法')
        self.assertEqual(fallback_search_title('冴えない彼女の育てかた Fine'),'冴えない彼女の育てかた')
        self.assertEqual(fallback_search_title('Fate/stay night'),'Fate/stay night')
        self.assertEqual(fallback_search_title("BanG Dream! It's MyGO"),"BanG Dream! It's MyGO")
        self.assertEqual(fallback_search_title('伪恋 OAD'),'伪恋')

    def test_long_title_queries_drop_decorations_and_season_for_search_only(self):
        cases={
            '无职转生 第三季 ～到了异世界就拿出真本事～':'无职转生',
            '無職転生Ⅲ ～異世界行ったら本気だす～':'無職転生',
            '无职转生Ⅱ ～到了异世界就拿出真本事～ 第2部分':'无职转生',
            '作品名称：一个很长的副标题':'作品名称',
            '作品名称（第三季）':'作品名称',
            '测试作品 Season 3':'测试作品',
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(fallback_search_title(title), expected)
        queries=discovery_queries({'title':'主标题','originalTitle':'原始标题','aliases':'另一个译名 / 另一个译名 / Useful Alias'})
        self.assertIn('Useful Alias',queries)
        self.assertEqual(len(queries),len(set(queries)))
        self.assertLessEqual(len(queries),6)

    def test_roman_season_and_cour_are_distinct(self):
        self.assertEqual(season_number('無職転生Ⅲ ～異世界行ったら本気だす～'),3)
        self.assertEqual(season_number('无职转生Ⅱ 第2部分'),2)
        self.assertIsNone(season_number('无职转生 第2部分'))
        self.assertEqual(part_number('无职转生Ⅱ 第2部分'),2)
        self.assertEqual(part_number('无职转生Ⅱ Part.2'),2)

    def test_symbol_fallback_keeps_meaningful_title_and_unwraps_full_name(self):
        cases = {
            'Re：从零开始的异世界生活': '从零开始的异世界生活',
            'Re:ゼロから始める異世界生活': 'ゼロから始める異世界生活',
            '【我推的孩子】': '我推的孩子',
            '【我推的孩子】 第二季': '我推的孩子',
            '中二病也要谈恋爱！恋': '中二病也要谈恋爱',
            '无头骑士异闻录×2 承': '无头骑士异闻录',
            'デート・ア・ライブII': 'デート',
            '作品名称（特别版）': '作品名称',
            "剧场版 BanG Dream! It's MyGO!!!!! 前篇": 'BanG Dream',
        }
        for title, expected in cases.items():
            with self.subTest(title=title):
                self.assertEqual(fallback_search_title(title), expected)
        self.assertNotIn('Re', discovery_queries({'title': 'Re：从零开始的异世界生活'}))

    def test_query_deduplication_uses_actual_lookup_keywords(self):
        queries = discovery_queries({
            'title': '测试作品！', 'originalTitle': '测试作品!',
            'aliases': '测试作品！！ / 测试作品 / Another title',
        })
        self.assertEqual(queries, ['测试作品', 'Another title'])

    def test_wrapped_lookup_titles_keep_identity_and_internal_punctuation(self):
        anime = {'title': '【我推的孩子】', 'originalTitle': '', 'aliases': ''}
        self.assertEqual(discovery_queries(anime)[0], '我推的孩子')
        self.assertEqual(anime['title'], '【我推的孩子】')
        for value in ('【作品名称】', '《作品名称》', '「作品名称」', '『作品名称』'):
            self.assertEqual(search_keyword(value), '作品名称')
        self.assertEqual(search_keyword('作品【副标题】'), '作品【副标题】')
        self.assertEqual(search_keyword('Fate/stay night'), 'Fate/stay night')
