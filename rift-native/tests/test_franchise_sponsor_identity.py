"""Smoke tests for operator club names, manager logos, sponsor offers and
hidden franchise reviews. Run:
 python3 -m unittest discover -s rift-native/tests -p 'test_franchise_sponsor_identity.py' -v
"""
import base64
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import club_history
import sponsorship
import promotion

class BrandAndLeagueTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript("""CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT);
        CREATE TABLE careers(id INTEGER PRIMARY KEY,name TEXT,season INTEGER,week INTEGER);
        CREATE TABLE club_profiles(career_id INTEGER PRIMARY KEY,mode TEXT,
             league TEXT,team_key TEXT,source TEXT);
        CREATE TABLE club_finances(career_id INTEGER PRIMARY KEY,
             cash INTEGER,transfer_budget INTEGER,wage_budget INTEGER,board INTEGER,fans INTEGER);
        CREATE TABLE finance_ledger(id INTEGER PRIMARY KEY,career_id INTEGER,
             event_key TEXT,season INTEGER,week INTEGER,amount INTEGER,category TEXT,
             description TEXT,UNIQUE(career_id,event_key));
        INSERT INTO users VALUES(1,'manager');
        INSERT INTO careers VALUES(1,'Rising Phoenix',4,1);
        INSERT INTO club_profiles VALUES(1,'create','LCK CL',NULL,'game-created');
        INSERT INTO club_finances VALUES(1,50000000,12000000,30000000,65,70);""")
        club_history.init(self.db)
        sponsorship.init(self.db)
        promotion.init(self.db)

    def tearDown(self):
        self.db.close()

    def test_operator_rename_preserves_canonical_team_and_history(self):
        result=club_history.rename(self.db,'LCK CL','Rising Phoenix','Rising Falcons',4,8)
        self.assertTrue(result['changed'])
        self.assertEqual('Rising Falcons',
                         club_history.display(self.db,'LCK CL','Rising Phoenix'))
        self.assertEqual('Rising Phoenix',self.db.execute(
            'SELECT name FROM careers WHERE id=1').fetchone()[0])
        events=club_history.history(self.db,'LCK CL','Rising Phoenix')
        self.assertEqual('club-renamed',events[0]['event'])

    def test_real_duplicate_club_name_is_rejected(self):
        with self.assertRaises(ValueError):
            club_history.rename(self.db,'LCK CL','Rising Phoenix','T1 Esports Academy',4,8)

    def test_user_logo_change_does_not_rename(self):
        png=base64.b64encode(bytes.fromhex('89504e470d0a1a0a')+b'example').decode('ascii')
        data='data:image/png;base64,'+png
        club_history.update_logo(self.db,'LCK CL','Rising Phoenix',data,4,1)
        self.assertEqual(data,club_history.visual(self.db,'LCK CL','Rising Phoenix')['logo_data'])
        self.assertEqual('Rising Phoenix',club_history.display(self.db,'LCK CL','Rising Phoenix'))
        with self.assertRaises(ValueError):
            club_history.validate_logo('data:image/svg+xml;base64,abc')

    def test_sponsorship_is_explicitly_fictional(self):
        offer=sponsorship.offer(self.db,1,4)
        self.assertEqual('fictional-game-contract',offer['source'])
        self.assertIn('실제 후원 관계가 아닙니다',sponsorship.DISCLAIMER)
        self.assertEqual(1,len(sponsorship.proposals(self.db,1)['offers']))

    def test_sponsor_accept_updates_finances_only_once(self):
        offer=sponsorship.offer(self.db,1,4)
        record=sponsorship.proposals(self.db,1)['offers'][0]
        from management import ledger
        with patch('management.ensure',lambda *args:None):
            before=self.db.execute('SELECT cash FROM club_finances WHERE career_id=1').fetchone()[0]
            result=sponsorship.accept(self.db,1,record['id'])
            after=self.db.execute('SELECT cash FROM club_finances WHERE career_id=1').fetchone()[0]
        self.assertEqual(record['amount'],after-before)
        self.assertEqual('fictional-game-contract',result['source'])
        self.assertEqual('sponsor-change',club_history.history(self.db,'LCK CL','Rising Phoenix')[0]['event'])
        with self.assertRaises(ValueError):
            sponsorship.accept(self.db,1,record['id'])

    def test_franchise_review_requires_three_seasons(self):
        for season in (1,2):
            self.db.execute("""INSERT INTO franchise_history
                (league,team,season,position,entrant_count,source)
                VALUES('LCK','T1',?,10,10,'internal-ai-estimate')""",(season,))
        self.assertFalse(promotion._under_review(self.db,'LCK',2))
        for season in (3,4,5):
            self.db.execute("""INSERT INTO franchise_history
                (league,team,season,position,entrant_count,source)
                VALUES('LCK','T1',?,10,10,'internal-ai-estimate')""",(season,))
        reviewed=set()
        for season in (3,4,5):
            reviewed.update(promotion._under_review(self.db,'LCK',season))
        self.assertIn('T1',reviewed)

    def test_new_season_promotion_preserves_team_name(self):
        self.db.execute("""INSERT INTO franchise_promotions
            (career_id,previous_league,new_league,season,status)
            VALUES(1,'LCK CL','LCK',5,'approved')""")
        with patch('career_rules.seed_league',return_value=3):
            self.assertEqual(1,promotion.apply_new_season(self.db,5))
        self.assertEqual('LCK',self.db.execute(
            'SELECT league FROM club_profiles WHERE career_id=1').fetchone()[0])
        self.assertEqual('Rising Phoenix',self.db.execute(
            'SELECT name FROM careers WHERE id=1').fetchone()[0])

if __name__=='__main__':
    unittest.main()
