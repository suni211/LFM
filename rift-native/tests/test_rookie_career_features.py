"""Regression tests for rookie invitations, owner identities and country flags."""
import sqlite3
import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'server'))
import catalog
import career_rules
import clubs
import dossier
import leadership
import nationality
import rookie_offers

class CareerOnboardingTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript("""CREATE TABLE users(id INTEGER PRIMARY KEY,name TEXT NOT NULL);
        CREATE TABLE careers(id INTEGER PRIMARY KEY,name TEXT,season INT,week INT,version INT);
        CREATE TABLE members(career_id INTEGER,user_id INTEGER,role TEXT,PRIMARY KEY(career_id,user_id));
        CREATE TABLE league_operators(user_id INTEGER PRIMARY KEY);
        INSERT INTO users VALUES(1,'rookie');""")
        clubs.init(self.db)
        career_rules.init(self.db)
        rookie_offers.init(self.db)

    def tearDown(self):
        self.db.close()

    def test_five_stable_real_club_offers(self):
        first=rookie_offers.list_offers(self.db,1)
        self.assertEqual(5,len(first))
        self.assertEqual([x['team_key'] for x in first],
                         [x['team_key'] for x in rookie_offers.list_offers(self.db,1)])
        keys={c['team_key'] for c in clubs.available(self.db)}
        for offer in first:
            self.assertIn(offer['team_key'],keys)
            self.assertTrue(career_rules.takeover_allowed(offer['league'],offer['team']))
            self.assertTrue(offer['available'])
        self.assertEqual(len({x['team_key'] for x in first}),5)

    def test_accept_same_transaction_owner(self):
        offer=rookie_offers.list_offers(self.db,1)[0]
        self.db.execute('INSERT INTO careers VALUES(7,?,1,1,1)',(offer['team'],))
        self.db.execute('INSERT INTO club_profiles VALUES(?,?,?,?,?)',
                        (7,'takeover',offer['league'],offer['team_key'],'test'))
        self.db.execute("INSERT INTO members VALUES(7,1,'admin')")
        rookie_offers.accept(self.db,1,offer['team_key'])
        statuses=rookie_offers.list_offers(self.db,1)
        self.assertEqual('accepted',statuses[0]['status'])
        self.assertEqual(4,len([o for o in statuses if o['status']=='closed']))
        with self.assertRaises(ValueError):
            rookie_offers.accept(self.db,1,offer['team_key'])

    def test_invitation_rejects_unoffered_team(self):
        offers=rookie_offers.list_offers(self.db,1)
        accepted={x['team_key'] for x in offers}
        other=next(c['team_key'] for c in clubs.available(self.db)
                   if c['team_key'] not in accepted)
        self.assertFalse(rookie_offers.invited(self.db,1,other))
        with self.assertRaises(ValueError):rookie_offers.accept(self.db,1,other)

    def test_verified_country_is_id_matched_not_region(self):
        players={p['id']:p for p in catalog.load()['people']}
        p=players['f52ca9d56ad89085891d']
        self.assertEqual('TW',p['nationality_code'])
        self.assertEqual('대만',p['nationality_name_ko'])
        self.assertIsNone(nationality.enrich({'id':'totally-unknown','region':'KR'}).get('nationality_code'))

    def test_verified_club_operator_and_manager_separate(self):
        owner=leadership.owner_info('LCP','DetonatioN FocusMe')
        self.assertEqual('Takuya Imaizumi',owner['representative'])
        self.assertEqual('verified',owner['source'])
        manager=dict(name='Paz',person_id='paz',source='registered-coach')
        staff=[dict(id='paz',nickname='Paz',kind='coach',raw_role='Head Coach'),
               dict(id='assistant',nickname='TaNa',kind='coach',raw_role='Assistant Coach')]
        rows=dossier.front_office(staff,manager,owner)
        roles=[r['role_key'] for r in rows]
        self.assertIn('OWNER',roles)
        self.assertIn('EXECUTIVE',roles)
        self.assertIn('MANAGER',roles)
        self.assertNotIn('paz',[p.get('id') for p in rows])
        self.assertIn('COACH',roles)

if __name__=='__main__':
    unittest.main()
