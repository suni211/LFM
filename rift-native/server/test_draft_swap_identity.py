"""Player-visible swap identities and authoritative Python series swap rules."""
import sqlite3
import unittest
from unittest.mock import patch

import draft_identity
import series_state


class DraftSwapTest(unittest.TestCase):
    def setUp(self):
        self.state={
            'phase':'swap','blue':0,
            'swap_version':0,'swap_until':100.0,
            'roster':[
                ['Kayle','Nunu','Ryze','Ashe','Alistar'],
                ['Sion','Warwick','Annie','Sivir','Soraka']],
            'role_options':{
                'Kayle':['TOP','MID'],'Ryze':['MID','TOP'],
                'Nunu':['JUNGLE'],'Ashe':['ADC'],'Alistar':['SUPPORT']
            }
        }

    def test_compatible_champion_swap_moves_to_correct_player_role(self):
        series_state.swap(self.state,'TOP','MID',0,10)
        self.assertEqual(['Ryze','Nunu','Kayle','Ashe','Alistar'],self.state['roster'][0])
        self.assertEqual(1,self.state['swap_version'])
        self.assertEqual('swap',self.state['phase'])

    def test_incompatible_swaps_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'포지션'):
            series_state.swap(self.state,'TOP','JUNGLE',0,10)
        self.assertEqual(0,self.state['swap_version'])

    def test_early_ready_starts_match_worker_phase(self):
        series_state.complete_swap(self.state,20)
        self.assertEqual('ready',self.state['phase'])
        self.assertEqual(20,self.state['swap_until'])

    def test_early_ready_cannot_run_outside_swap(self):
        self.state['phase']='ready'
        with self.assertRaisesRegex(ValueError,'종료'):
            series_state.complete_swap(self.state,20)


class LineupIdentityTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript("""
        CREATE TABLE careers(id INTEGER PRIMARY KEY,name TEXT);
        CREATE TABLE club_profiles(career_id INTEGER PRIMARY KEY,league TEXT);
        CREATE TABLE members(career_id INTEGER,user_id INTEGER,role TEXT);
        CREATE TABLE fixtures(id INTEGER PRIMARY KEY,career_id INTEGER,opponent TEXT);
        INSERT INTO careers VALUES(11,'My Team'),(12,'Other Team'),(13,'Other Team');
        INSERT INTO club_profiles VALUES(11,'LCK'),(12,'LCK'),(13,'LEC');
        INSERT INTO members VALUES(11,21,'admin');
        INSERT INTO fixtures VALUES(999,11,'Other Team');
        """)
        self.views={
            11:{'roster':[{'role':'TOP','kind':'player','assignment':'first','nickname':'Me'}]},
            12:{'roster':[{'role':'MID','kind':'player','assignment':'first','nickname':'Them'}]},
        }

    def tearDown(self):
        self.db.close()

    def test_only_fixture_member_can_read_and_players_match_league(self):
        with patch.object(draft_identity.recruitment,'view',side_effect=lambda db,c:self.views[c]), \
             patch.object(draft_identity.catalog,'display',side_effect=lambda p:p['nickname']):
            self.assertIsNone(draft_identity.lineup(self.db,999,99))
            result=draft_identity.lineup(self.db,999,21)
        self.assertEqual('Me',result['teams'][0]['players']['TOP'])
        self.assertEqual('Them',result['teams'][1]['players']['MID'])
        self.assertIsNone(result['teams'][0]['players']['MID'])
        self.assertEqual(['TOP','JUNGLE','MID','ADC','SUPPORT'],result['roles'])


if __name__=='__main__':
    unittest.main()
