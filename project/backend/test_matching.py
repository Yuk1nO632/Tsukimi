"""Provider-independent name, alias and season evidence used by AniCh fallback."""
import unittest
from matching import exact_source, special_search_title


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
