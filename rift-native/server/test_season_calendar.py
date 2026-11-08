"""Generated season matchups and safe operator observation contracts."""
import sqlite3
import unittest
from unittest.mock import patch

import catalog
import clubs
import fixtures
import season_calendar


class CalendarAndOperatorTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT)")
        self.db.execute("CREATE TABLE league_operators(user_id INTEGER PRIMARY KEY)")
        self.db.execute("CREATE TABLE careers(id INTEGER PRIMARY KEY,name TEXT,season INTEGER,week INTEGER,version INTEGER)")
        self.db.execute("CREATE TABLE members(career_id INTEGER,user_id INTEGER,role TEXT,PRIMARY KEY(career_id,user_id))")
        clubs.init(self.db)
        fixtures.init(self.db)
        self.db.execute("INSERT INTO users VALUES(1,'operator')")
        self.db.execute("INSERT INTO users VALUES(2,'manager')")
        self.db.execute("INSERT INTO league_operators VALUES(1)")
        self.db.execute("INSERT INTO careers VALUES(10,'Alpha',1,1,1)")
        self.db.execute("INSERT INTO club_profiles VALUES(10,'takeover','LCK','alpha','test')")
        self.mock=patch.object(catalog,'teams',return_value=[
            {'team':name,'league':'LCK'} for name in ('Alpha','Beta','Gamma','Delta')])
        self.mock.start()

    def tearDown(self):
        self.mock.stop()
        self.db.close()

    def test_world_schedule_exists_without_any_played_match(self):
        matches=season_calendar.build(self.db,1,'LCK')
        self.assertEqual(len(matches),12)
        self.assertEqual({g['week'] for g in matches},set(range(2,8)))
        for week in range(2,8):
            teams=[name for g in matches if g['week']==week for name in (g['home'],g['away'])]
            self.assertCountEqual(teams,['Alpha','Beta','Gamma','Delta'])
        self.assertTrue(all(g['source']=='game-generated' and g['best_of']==3 for g in matches))

    def test_career_fixtures_populate_on_first_visit_without_duplicates(self):
        created=season_calendar.ensure_career(self.db,10)
        self.assertEqual(created,6)
        self.assertEqual(season_calendar.ensure_career(self.db,10),0)
        rows=self.db.execute("SELECT season,week FROM fixtures WHERE career_id=10 ORDER BY week").fetchall()
        self.assertEqual(rows,[(1,week) for week in range(2,8)])

    def test_manual_fixture_is_not_overwritten(self):
        self.db.execute("""INSERT INTO fixtures(career_id,season,week,opponent,seed,best_of,competition,stage)
            VALUES(10,1,2,'Manual Rival',1,5,'Worlds','final')""")
        self.assertEqual(season_calendar.ensure_career(self.db,10),5)
        row=self.db.execute("SELECT opponent,best_of,competition,stage FROM fixtures WHERE career_id=10 AND week=2").fetchone()
        self.assertEqual(row,('Manual Rival',5,'Worlds','final'))

    def test_next_season_is_generated_immediately(self):
        season_calendar.ensure_career(self.db,10)
        self.db.execute("UPDATE careers SET season=2,week=1 WHERE id=10")
        self.assertEqual(season_calendar.ensure_career(self.db,10),6)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM fixtures WHERE season=2").fetchone()[0],6)

    def test_operator_can_observe_but_never_becomes_club_admin(self):
        self.assertEqual(clubs.grant(self.db,1,10,read_only=True),'viewer')
        self.assertEqual(clubs.grant(self.db,1,10,read_only=True),'viewer')
        self.assertEqual(self.db.execute("SELECT role FROM members WHERE career_id=10 AND user_id=1").fetchone()[0],'viewer')
        self.assertEqual(clubs.grant(self.db,2,10),'admin')
        self.assertEqual(clubs.grant(self.db,1,10,read_only=True),'viewer')


if __name__=='__main__':
    unittest.main()
