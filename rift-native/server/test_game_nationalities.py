"""Verify game-country coverage and preserve country evidence and person identities."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
import complete_game_nationalities as fill_game
import catalog

class GameNationalityTest(unittest.TestCase):
    def test_complete_game_country_without_overwriting_public_records(self):
        people=catalog.load()['people']
        existing={'people':{
            people[0]['id']:{'code':'ZZ','name':'fixture', 'source':'test-existing'}
        }}
        result,report=fill_game.fill(people,existing)
        self.assertEqual(report['missing_after'],[])
        self.assertEqual(report['with_country'],len(people))
        self.assertEqual(result['people'][people[0]['id']]['code'],'ZZ')
        self.assertEqual(report['reassigned_existing'],0)

    def test_duplicate_nicknames_do_not_inherit_another_leagues_country(self):
        people=[
            dict(id='korean-peter',nickname='Peter',league='LCK',real_person=True),
            dict(id='taiwan-peter',nickname='Peter',league='LCP',real_person=True),
        ]
        result,report=fill_game.fill(people,{'people':{}})
        self.assertEqual(report['with_country'],2)
        self.assertEqual(result['people']['korean-peter']['code'],'KR')
        self.assertEqual(result['people']['taiwan-peter']['code'],'TW')
        self.assertTrue(all(x['game_estimate'] for x in result['people'].values()))
if __name__=='__main__':
    unittest.main()
