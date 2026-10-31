"""Provider-independent name, alias and season evidence used by AniCh fallback."""
import unittest
from matching import exact_source


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
