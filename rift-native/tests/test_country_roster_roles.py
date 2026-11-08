"""Nation and profession regression tests for the 2026 game directory.

Run from repo root:
    python3 -m unittest discover -s rift-native/tests -p 'test_country_roster_roles.py' -v
"""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import catalog
import dossier
import leadership
import manager_identity
import nationality

class IdentityAndRosterTests(unittest.TestCase):
    def test_corporate_owners_and_executives_have_no_country(self):
        for league,team in [('LCP','DetonatioN FocusMe'),('LCK','T1'),('LCK','Gen.G'),
                            ('LCS','Cloud9'),('LPL','Unknown Real Club')]:
            owner=leadership.owner_info(league,team)
            self.assertNotIn('nationality_code',owner)
            self.assertNotIn('nationality_name_ko',owner)
            people=dossier.front_office([],None,owner)
            self.assertIn('OWNER',{p['role_key'] for p in people})
            for person in people:
                if person['role_key'] in ('OWNER','EXECUTIVE'):
                    self.assertFalse(person['show_nationality'])
                    self.assertNotIn('nationality_code',person)
                    self.assertNotIn('nationality_name_ko',person)

    def test_real_people_do_not_inherit_country_from_team(self):
        unknown=nationality.enrich({'id':'unverified-test','real_person':True,
                                    'region':'KR','team':'T1','league':'LCK'})
        self.assertFalse(unknown.get('nationality_code'))
        self.assertFalse(unknown.get('nationality_name_ko'))

    def test_verified_country_from_exact_person_id(self):
        people={p['id']:p for p in catalog.load()['people']}
        self.assertEqual('TW',people['f52ca9d56ad89085891d']['nationality_code'])
        self.assertEqual('대만',people['f52ca9d56ad89085891d']['nationality_name_ko'])

    def test_all_2026_lck_named_coaches_are_not_players(self):
        people=catalog.load()['people']
        by_club={(p['team'],p['nickname']):p for p in people if p.get('league')=='LCK'}
        for team,members in leadership.LCK_2026_STAFF.items():
            for name,expected_role in members.items():
                player=by_club.get((team,name))
                if not player:
                    continue
                self.assertIn(player['kind'],('coach','staff'))
                self.assertEqual(expected_role,player['staff_role'])
        self.assertEqual('HEAD_COACH',by_club[('LCK' if False else 'T1','Tom')]['staff_role'])
        self.assertEqual('coach',by_club[('Gen.G','Ryu')]['kind'])

    def test_substitute_is_never_classed_as_coach(self):
        target=next(p for p in catalog.load()['people'] if p['nickname']=='Nisqy'
                    and p['team']=='ZYB Esport')
        self.assertEqual('player',target['kind'])
        self.assertEqual('reserve',target['squad'])

    def test_new_manager_must_choose_country(self):
        db=sqlite3.connect(':memory:')
        try:
            db.executescript("""CREATE TABLE users(id INTEGER PRIMARY KEY);
            INSERT INTO users VALUES(1);
            CREATE TABLE members(career_id INTEGER,user_id INTEGER,role TEXT);
            CREATE TABLE manager_profiles(career_id INTEGER,name TEXT,stats TEXT);""")
            manager_identity.init(db)
            stats={key:10 for key in manager_identity.ATTRIBUTES}
            profile=dict(nickname='ManagerTest',name='Example Manager',nationality_code='KR',stats=stats)
            returned=manager_identity.save(db,1,profile)
            self.assertEqual('대한민국',returned['nationality_name_ko'])
            self.assertEqual('KR',returned['nationality_code'])
            with self.assertRaises(ValueError):
                manager_identity.save(db,1,dict(profile,nationality_code=''))
        finally:db.close()

if __name__=='__main__':unittest.main()
