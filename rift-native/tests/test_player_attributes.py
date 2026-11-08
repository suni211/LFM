"""Operator-editable, per-player FM/LoL stats regression tests."""
import json
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import player_attributes

class PlayerAttributeTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        player_attributes.init(self.db)
        self.person={'id':'player-demo','nickname':'Kiro','role':'JUNGLE','kind':'player',
                     'game_evaluation':{'ratings':{'라인전':65,'교전':75,'운영':70,'시야':80,
                                                   '협동':60,'멘탈':55}}}

    def tearDown(self):
        self.db.close()

    def test_all_players_have_30_stable_individual_attributes(self):
        initial=player_attributes.read(self.db,self.person)
        self.assertEqual(30,len(initial['ratings']))
        self.assertEqual(5,len(initial['groups']))
        self.assertEqual(20,initial['scale'])
        self.assertEqual('game-estimated',initial['source'])
        self.assertTrue(all(type(v)==int and 1<=v<=20 for v in initial['ratings'].values()))
        self.assertEqual(initial,player_attributes.read(self.db,self.person))
        different=player_attributes.read(self.db,{**self.person,'id':'other-player'})
        self.assertNotEqual(initial['ratings'],different['ratings'])

    def test_operator_change_persists_across_readers_and_affects_gameplay_core(self):
        updated={key:14 for key in player_attributes.KEYS}
        updated.update({'라인전':19,'교전':18,'운영':17,'시야':16,'협동':15,'멘탈':14})
        result=player_attributes.save(self.db,self.person,updated,100)
        self.assertEqual(updated,result['ratings'])
        self.assertEqual('operator-edited',result['source'])
        self.assertEqual(1,result['revision'])
        self.assertEqual(result,player_attributes.read(self.db,self.person))
        after=player_attributes.apply_to_game_evaluation(self.db,self.person.copy())
        self.assertEqual(95,after['game_evaluation']['ratings']['라인전'])
        self.assertEqual(90,after['game_evaluation']['ratings']['교전'])
        self.assertEqual(85,after['game_evaluation']['ratings']['운영'])
        self.assertEqual(80,after['game_evaluation']['ratings']['시야'])
        self.assertEqual(75,after['game_evaluation']['ratings']['협동'])
        self.assertEqual(70,after['game_evaluation']['ratings']['멘탈'])
        # Same payload is idempotent. A later change is an auditable revision.
        self.assertEqual(1,player_attributes.save(self.db,self.person,updated,100)['revision'])
        updated['라인전']=20
        self.assertEqual(2,player_attributes.save(self.db,self.person,updated,100)['revision'])
        self.assertEqual(2,self.db.execute('SELECT COUNT(*) FROM player_attribute_history').fetchone()[0])

    def test_reject_malformed_or_foreign_attributes(self):
        valid={key:10 for key in player_attributes.KEYS}
        for sample in ({},{**valid,'unknown':10},{**valid,'멘탈':0},
                       {**valid,'멘탈':21},{**valid,'멘탈':10.5},
                       {**valid,'멘탈':True},{**valid,'멘탈':'10'}):
            with self.subTest(sample=sample):
                with self.assertRaises(ValueError):
                    player_attributes.save(self.db,self.person,sample,1)
        with self.assertRaises(ValueError):
            player_attributes.save(self.db,{**self.person,'kind':'coach'},valid,1)
        self.assertIsNone(player_attributes.read(self.db,{**self.person,'kind':'coach'}))

if __name__=='__main__':
    unittest.main()
