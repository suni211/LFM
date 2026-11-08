"""Prospect Master floor and existing database nickname migration regression."""
import json
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import solo
import solo_handles

class SoloProspectShortNamesTests(unittest.TestCase):
    def test_master_floor_and_saved_short_name_migration(self):
        db=sqlite3.connect(':memory:')
        fake={'people':[{'id':'real-pro-t1','nickname':'Faker','real_name':'Lee Sang-hyeok',
                         'kind':'player','real_person':True,'role':'MID','league':'LCK','team':'T1'}]}
        try:
            with patch('catalog.load',return_value=fake):
                solo.init(db)
                self.assertEqual(4160,db.execute(
                    "SELECT COUNT(*) FROM solo_people").fetchone()[0])
                seeded=db.execute("SELECT person_id,nickname FROM solo_ranks WHERE path='amateur' LIMIT 1").fetchone()
                pid,initial=seeded
                self.assertTrue(solo_handles.valid(initial))
                self.assertEqual('Faker',solo.fetch(db,'real-pro-t1')[8])
                # Simulate a saved database containing a long old template nickname
                # and a prospect who was previously allowed below Master.
                before=json.loads(db.execute('SELECT payload FROM solo_people WHERE person_id=?',(pid,)).fetchone()[0])
                before['nickname']='AmberMoonGrove'
                before['real_name']='AmberMoonGrove'
                db.execute("UPDATE solo_people SET payload=? WHERE person_id=?",
                           (json.dumps(before),pid))
                db.execute("""UPDATE solo_ranks SET nickname='AmberMoonGrove',
                    real_name='AmberMoonGrove',path='prospect',mmr=1500 WHERE person_id=?""",(pid,))
                db.execute("""CREATE TABLE generated_people(
                    id TEXT PRIMARY KEY,real_name TEXT,nickname_key TEXT UNIQUE,
                    career_id INTEGER,payload TEXT,assignment TEXT)""")
                db.execute("""INSERT INTO generated_people VALUES(?,?,?,?,?,?)""",
                           (pid,'AmberMoonGrove','ambermoongrove',1,json.dumps(before),'academy'))
                db.execute("DELETE FROM solo_seed WHERE key='compact-solo-handles-v3'")
                solo.init(db)
                row=solo.fetch(db,pid)
                self.assertGreaterEqual(row[1],solo.PRO_MIN_MMR)
                self.assertTrue(solo_handles.valid(row[8]))
                self.assertNotEqual('AmberMoonGrove',row[8])
                updated=json.loads(db.execute('SELECT payload FROM solo_people WHERE person_id=?',(pid,)).fetchone()[0])
                generated=db.execute('SELECT nickname_key,payload FROM generated_people WHERE id=?',(pid,)).fetchone()
                self.assertEqual(updated['nickname'],row[8])
                self.assertEqual(generated[0],row[8].casefold())
                self.assertEqual(json.loads(generated[1])['nickname'],row[8])
                self.assertEqual('Faker',solo.fetch(db,'real-pro-t1')[8])
                solo.weekly(db,1,1)
                self.assertGreaterEqual(solo.fetch(db,pid)[1],solo.PRO_MIN_MMR)
        finally:
            db.close()

    def test_new_prospects_master_and_amateurs_can_be_below_master(self):
        self.assertGreaterEqual(solo.start_mmr({'id':'solo-bot','kind':'player'},'prospect'),2800)
        self.assertEqual(solo.DEBUT_MMR,solo.PRO_MIN_MMR)
        self.assertGreaterEqual(solo.start_mmr({'id':'pro-player','league':'LDL'},'pro'),2800)

if __name__=='__main__':
    unittest.main()
