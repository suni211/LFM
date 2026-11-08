"""Squad swap and draft-readiness regression tests."""
import sqlite3
import unittest
from unittest.mock import patch
import clubs
import management


class LineupReadinessTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript("""
            CREATE TABLE club_contracts(
                career_id INTEGER,person_id TEXT,active INTEGER,end_turn INTEGER);
            CREATE TABLE club_health(
                career_id INTEGER,person_id TEXT,injury_until INTEGER);
        """)
        self.roster=[dict(id=role.lower(),nickname=role,kind='player',assignment='first',role=role)
                     for role in ('TOP','JUNGLE','MID','ADC','SUPPORT')]
        self.patched=patch.object(management.recruitment,'view',side_effect=lambda db,c:
            dict(complete=True,roster=list(self.roster)))
        self.patched.start()

    def tearDown(self):
        self.patched.stop()
        self.db.close()

    def test_missing_starting_role_is_not_accepted(self):
        self.roster.pop()
        errors=management.readiness_details(self.db,7,20)
        self.assertEqual(1,len(errors)+sum(i['role']!='SUPPORT' for i in errors))
        self.assertEqual('SUPPORT',errors[0]['role'])
        self.assertTrue(management.readiness(self.db,7,20))

    def test_missing_or_inactive_contract_blocks_draft(self):
        issues=management.readiness_details(self.db,7,20)
        self.assertEqual(5,len(issues))
        self.assertTrue(all('계약' in issue['reason'] for issue in issues))
        for p in self.roster:
            self.db.execute('INSERT INTO club_contracts VALUES(?,?,?,?)',(7,p['id'],1,150))
            self.db.execute('INSERT INTO club_health VALUES(?,?,?)',(7,p['id'],0))
        self.assertFalse(management.readiness(self.db,7,20))
        self.db.execute("UPDATE club_health SET injury_until=22 WHERE person_id='mid'")
        bad=management.readiness_details(self.db,7,20)
        self.assertEqual('mid',bad[0]['person'])
        self.assertIn('부상',bad[0]['reason'])
        self.db.execute("UPDATE club_health SET injury_until=0")
        self.db.execute("UPDATE club_contracts SET end_turn=19 WHERE person_id='adc'")
        self.assertIn('만료',management.readiness_details(self.db,7,20)[0]['reason'])


class TeamSwitchTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.executescript("""
            CREATE TABLE club_roster(
                career_id INTEGER,person_id TEXT,payload TEXT,assignment TEXT,role TEXT);
            CREATE TABLE generated_people(
                career_id INTEGER,id TEXT,payload TEXT,assignment TEXT);
        """)
        self.db.execute('INSERT INTO club_roster VALUES(7,?,?,?,?)',
                        ('starter','{}','first','TOP'))
        self.db.execute('INSERT INTO club_roster VALUES(7,?,?,?,?)',
                        ('junior','{}','academy','TOP'))

    def tearDown(self):
        self.db.close()

    def test_academy_player_promotes_and_starter_drops_to_academy(self):
        with patch('solo.require_pro'):
            clubs.assign(self.db,7,'junior','first','TOP')
        self.assertEqual(
            self.db.execute('SELECT assignment FROM club_roster WHERE person_id=?',
                            ('junior',)).fetchone()[0],'first')
        self.assertEqual(
            self.db.execute('SELECT assignment FROM club_roster WHERE person_id=?',
                            ('starter',)).fetchone()[0],'academy')

    def test_current_starter_may_move_down_to_academy(self):
        clubs.assign(self.db,7,'starter','academy','TOP')
        self.assertEqual(
            self.db.execute('SELECT assignment FROM club_roster WHERE person_id=?',
                            ('starter',)).fetchone()[0],'academy')


if __name__ == '__main__':
    unittest.main()
