"""Regression tests for 150-week seasons, old saves and negotiation limits."""
import sqlite3
import unittest
import season_structure

class Season150Test(unittest.TestCase):
    def test_phases_and_wrap(self):
        points={1:'preseason-transfer',10:'preseason-transfer',
            11:'regional',28:'international',56:'international',
            89:'international',125:'regional',126:'worlds-break',
            130:'worlds-break',131:'worlds-swiss',136:'worlds-swiss',
            137:'worlds-playoffs',144:'worlds-playoffs',
            145:'postseason-transfer',150:'postseason-transfer'}
        for week,kind in points.items():
            self.assertEqual(season_structure.phase(week),kind)
        self.assertEqual(season_structure.following(1,149),(1,150))
        self.assertEqual(season_structure.following(1,150),(2,1))
        self.assertEqual(season_structure.absolute_turn(2,1),151)
        self.assertEqual(season_structure.decode_turn(151),(2,1))

    def test_windows_leave_stove_and_worlds_untouched(self):
        for league in ('LCK','LCK CL','LPL','LDL','LEC'):
            weeks=[w for w,_ in season_structure.round_slots(league)]
            self.assertTrue(weeks)
            self.assertEqual(len(weeks),len(set(weeks)))
            self.assertTrue(all(season_structure.phase(w)=='regional' for w in weeks))

    def test_legacy_contract_turns_and_fixture_check_are_upgraded_once(self):
        db=sqlite3.connect(':memory:',isolation_level=None)
        db.execute('PRAGMA foreign_keys=OFF')
        db.execute('CREATE TABLE careers(id INTEGER PRIMARY KEY)')
        db.execute('INSERT INTO careers VALUES(1)')
        db.execute("""CREATE TABLE fixtures(
            id INTEGER PRIMARY KEY,career_id INTEGER NOT NULL REFERENCES careers(id),
            season INTEGER NOT NULL,week INTEGER NOT NULL CHECK(week BETWEEN 1 AND 104),
            opponent TEXT,UNIQUE(career_id,season,week))""")
        db.execute("INSERT INTO fixtures VALUES(3,1,1,77,'Beta')")
        db.execute("""CREATE TABLE league_games(
            career_id INTEGER,season INTEGER,week INTEGER CHECK(week BETWEEN 1 AND 104),
            home TEXT,away TEXT,fixture_id INTEGER REFERENCES fixtures(id),
            UNIQUE(career_id,season,week,home,away))""")
        db.execute("INSERT INTO league_games VALUES(1,1,77,'Alpha','Beta',3)")
        db.execute("CREATE TABLE club_contracts(career_id INTEGER,person_id TEXT,end_turn INTEGER)")
        db.execute("INSERT INTO club_contracts VALUES(1,'p1',105)")
        self.assertTrue(season_structure.migrate_legacy_schema(db))
        self.assertFalse(season_structure.migrate_legacy_schema(db))
        self.assertEqual(db.execute("SELECT end_turn FROM club_contracts").fetchone()[0],151)
        self.assertEqual(db.execute("SELECT id FROM fixtures").fetchone()[0],3)
        db.execute("INSERT INTO fixtures VALUES(4,1,1,136,'Gamma')")
        db.execute("INSERT INTO league_games VALUES(1,1,136,'Alpha','Gamma',4)")
        self.assertEqual(db.execute("PRAGMA foreign_key_check").fetchall(),[])
        db.close()

if __name__=='__main__':
    unittest.main()
