"""Game economy regression: match evidence, wages, merchandise and AI ROI."""
import sqlite3
import unittest
from unittest.mock import patch

import ai_front_office
import merchandise
import player_economy

def player(pid="p1",league="LCK",rating=65):
    return dict(id=pid,kind="player",role="MID",real_person=False,
       league=league,team="FA",nickname=pid,
       stats={name:rating for name in
              ('라인전','교전','운영','시야','협동','멘탈')})

class EconomyTest(unittest.TestCase):
    def test_fame_drives_merchandise_and_game_salary(self):
        low=player("L","Circuito Desafiante")
        star=player("S","LCK")
        base=player_economy.estimate(low)
        famous=player_economy.estimate(star)
        for key in ("rating","fame","annual_salary","market_value","merch_annual_sales",
                    "merch_annual_profit"):
            self.assertGreater(famous[key],0)
        self.assertGreater(famous["fame"],base["fame"])
        self.assertGreater(famous["merch_annual_profit"],base["merch_annual_profit"])
        self.assertGreater(famous["annual_salary"],base["annual_salary"])
        self.assertTrue(famous["criteria"]["salary"])

    def test_recorded_pro_performance_changes_rating_without_replacing_abilities(self):
        p=player()
        baseline=player_economy.estimate(p)
        with patch.object(player_economy,"performance_index",return_value={
            p['id']:dict(games=60,performance=93)}):
            rated=player_economy.estimate(p)
        self.assertGreater(rated["rating"],baseline["rating"])
        self.assertEqual(rated["ability"],baseline["ability"])
        self.assertGreater(rated["fame"],baseline["fame"])

    def test_ai_weighs_sport_and_merchandise_against_salary(self):
        p=player()
        high=ai_front_office.scoring(p,40,90)
        low=ai_front_office.scoring(p,78,20)
        self.assertGreater(high["projected_net_value"],low["projected_net_value"])
        self.assertGreater(high["predicted_merch_profit"],low["predicted_merch_profit"])
        self.assertEqual(high["annual_salary"],low["annual_salary"])

    def test_merchandise_and_cash_post_once_for_same_week(self):
        db=sqlite3.connect(':memory:')
        db.execute("""CREATE TABLE club_finances(career_id INTEGER PRIMARY KEY,
             cash INTEGER,transfer_budget INTEGER,wage_budget INTEGER)""")
        db.execute("""CREATE TABLE finance_ledger(id INTEGER PRIMARY KEY,
             career_id INTEGER,event_key TEXT UNIQUE,season INTEGER,week INTEGER,
             amount INTEGER,category TEXT,description TEXT)""")
        db.execute("CREATE TABLE careers(id INTEGER PRIMARY KEY,season INTEGER)")
        db.execute("INSERT INTO careers VALUES(1,1)")
        db.execute("INSERT INTO club_finances VALUES(1,500000000,300000000,300000000)")
        merchandise.init(db)
        p=player("first","LCK",75)
        item=dict(person=p,active=True,end_turn=208)
        merchandise.weekly(db,1,1,2,[item],100)
        first=merchandise.snapshot(db,1)
        self.assertGreater(first['units'],0)
        self.assertGreater(first['profit'],0)
        merchandise.weekly(db,1,1,2,[item],100)
        after=merchandise.snapshot(db,1)
        self.assertEqual(first,after)
        self.assertEqual(db.execute("""SELECT cash FROM club_finances
            WHERE career_id=1""").fetchone()[0],500000000+first['profit'])
        self.assertEqual(db.execute("SELECT COUNT(*) FROM finance_ledger").fetchone()[0],1)
        db.close()

    def test_ai_respects_attached_player_ownership(self):
        db=sqlite3.connect(':memory:')
        db.execute("CREATE TABLE person_ownership(person_id TEXT PRIMARY KEY,career_id INTEGER,club_key TEXT)")
        db.execute("CREATE TABLE club_roster(person_id TEXT,assignment TEXT)")
        db.execute("CREATE TABLE generated_people(id TEXT,assignment TEXT)")
        p=player()
        db.execute("INSERT INTO person_ownership VALUES('p1',22,NULL)")
        self.assertFalse(ai_front_office.is_unattached(db,p))
        db.execute("UPDATE person_ownership SET career_id=NULL,club_key='free-agent' WHERE person_id='p1'")
        self.assertTrue(ai_front_office.is_unattached(db,p))
        db.execute("INSERT INTO club_roster VALUES('p1','first')")
        self.assertFalse(ai_front_office.is_unattached(db,p))
        db.close()

if __name__=='__main__':
    unittest.main()
