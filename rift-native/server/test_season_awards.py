"""Awards are based on saved match telemetry and never invented for empty seasons."""
import json
import sqlite3
import unittest
from unittest.mock import patch

import catalog
import clubs
import fixtures
import season_awards
import academy_clubs
import league


ROLES=('TOP','JUNGLE','MID','ADC','SUPPORT')


def played(team, side, victory=True):
    roster=[]
    for role in ROLES:
        roster.append(dict(team=side,role=role,name='Ahri',player_id=f'{team}-{role}',
                           player_name=f'{team}-{role}',kda=[4 if victory else 1,1,5],
                           cs=200,gold=15000,damage=20000))
    return roster


class AwardsTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        db=self.db
        db.execute("CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT)")
        db.execute("""CREATE TABLE careers(
            id INTEGER PRIMARY KEY,name TEXT,season INTEGER,week INTEGER,version INTEGER)""")
        db.execute("CREATE TABLE members(career_id INTEGER,user_id INTEGER,role TEXT)")
        db.execute("CREATE TABLE manager_profiles(career_id INTEGER PRIMARY KEY,name TEXT)")
        db.execute("CREATE TABLE online_clock(id INTEGER PRIMARY KEY,season INTEGER,week INTEGER,version INTEGER)")
        db.execute("INSERT INTO online_clock VALUES(1,1,3,3)")
        db.execute("CREATE TABLE generated_people(id TEXT,payload TEXT)")
        clubs.init(db)
        fixtures.init(db)
        league.init(db)
        season_awards.init(db)
        for cid,club in enumerate(('Alpha','Beta','Gamma'),1):
            db.execute("INSERT INTO careers VALUES(?,?,1,3,3)",(cid,club))
            db.execute("INSERT INTO club_profiles VALUES(?,?,?,?,?)",(cid,'takeover','LCK',club,'game'))
            db.execute("INSERT INTO manager_profiles VALUES(?,?)",(cid,club+' 감독'))
        self.people=[]
        for club in ('Alpha','Beta','Gamma'):
            for role in ROLES:
                self.people.append(dict(id=f'{0 if club=="Alpha" else 1 if club=="Beta" else 2}-{role}',
                    real_person=True,nickname=f'{club}-{role}',league='LCK',team=club,role=role))
        self.mock=patch.object(catalog,'load',return_value={'people':self.people})
        self.mock.start()
        self.team_mock=patch.object(catalog,'teams',return_value=[
            dict(team=club,league='LCK') for club in ('Alpha','Beta','Gamma')])
        self.team_mock.start()

    def tearDown(self):
        self.mock.stop()
        self.team_mock.stop()
        self.db.close()

    def result(self,home,away,blue=0,final=False):
        a=('Alpha','Beta','Gamma').index(home)
        b=('Alpha','Beta','Gamma').index(away)
        sets=[dict(blue=blue,winner=0,players=played(a,0,True)+played(b,1,False))]
        return {'winner':0,'score':[3,0] if final else [2,0],'sets':sets}

    def insert(self,cid,opponent,week=2,competition='LCK',stage='regular',final=False):
        home=('Alpha','Beta','Gamma')[cid-1]
        payload=self.result(home,opponent,final=final)
        self.db.execute("""INSERT INTO fixtures(
            career_id,season,week,opponent,seed,best_of,competition,stage,state,result)
            VALUES(?,1,?,?,1,3,?,?,'finished',?)""",
            (cid,week,opponent,competition,stage,json.dumps(payload)))

    def test_no_match_never_creates_undocumented_winners(self):
        response=season_awards.history(self.db,1,'LCK')
        self.assertEqual(response['awards'],[])
        self.assertFalse(response['finalized'])
        self.assertIn('LCK CL',season_awards.history(self.db)['leagues'])
        self.assertIn('LDL',season_awards.history(self.db)['leagues'])

    def test_all_pro_three_rows_per_role_and_coach_from_real_games(self):
        self.insert(1,'Beta',2)
        self.insert(1,'Gamma',3)
        self.insert(2,'Gamma',4)
        honors=season_awards.calculate(self.db,1,'LCK')
        for role in ROLES:
            eligible=[a for a in honors if a['category']=='all_pro' and a['role']==role]
            self.assertEqual([x['award_rank'] for x in eligible],[1,2,3])
            self.assertEqual(len({a['person_id'] for a in eligible}),3)
        coach=[a for a in honors if a['category']=='coach']
        self.assertEqual(len(coach),1)
        self.assertEqual(coach[0]['person_name'],'Alpha 감독')
        self.assertFalse([a for a in honors if a['category']=='rookie'])

    def test_rookie_requires_explicit_generated_debut(self):
        self.insert(1,'Beta',2)
        p={'id':'0-MID','source':'solo-queue','real_person':False}
        self.db.execute("INSERT INTO generated_people VALUES(?,?)",('0-MID',json.dumps(p)))
        names=[a for a in season_awards.calculate(self.db,1,'LCK') if a['category']=='rookie']
        self.assertEqual(len(names),1)
        self.assertEqual(names[0]['person_id'],'0-MID')

    def test_worlds_mvp_requires_completed_final_and_winning_player(self):
        self.assertIsNone(season_awards._worlds_honor(self.db,1))
        self.insert(1,'Beta',2,'Worlds','final',True)
        season_awards.record_worlds_final(self.db,1)
        record=self.db.execute("SELECT league,category,club FROM season_honors").fetchone()
        self.assertEqual(record,('Worlds','worlds_mvp','Alpha'))
        season_awards.record_worlds_final(self.db,1)
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM season_honors").fetchone()[0],1)

    def test_finalized_history_is_permanent_and_idempotent(self):
        self.insert(1,'Beta',2)
        self.assertTrue(season_awards.finalize(self.db,1))
        self.assertFalse(season_awards.finalize(self.db,1))
        saved=self.db.execute("SELECT COUNT(*) FROM season_honors").fetchone()[0]
        self.db.execute("DELETE FROM fixtures")
        self.assertEqual(season_awards.history(self.db,1,'LCK')['awards'].__len__(),saved)
        self.assertTrue(season_awards.history(self.db,1,'LCK')['finalized'])

    def test_tier_two_clubs_have_distinct_canonical_names(self):
        self.assertEqual(len(academy_clubs.teams('LCK CL')),10)
        self.assertEqual(len(academy_clubs.teams('LDL')),10)
        self.assertFalse(set(academy_clubs.teams('LCK CL'))&set(academy_clubs.teams('LDL')))
        self.assertNotIn('LCK 2군',academy_clubs.teams('LCK CL'))
        self.assertNotIn('LDL 2군',academy_clubs.teams('LDL'))


if __name__=='__main__':
    unittest.main()
