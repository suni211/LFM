"""Regression tests for expiring-season renewal windows and operator news access."""
import sqlite3
import unittest
from unittest.mock import Mock, patch

import management
import news


class ContractRenewalRulesTest(unittest.TestCase):
    def test_only_expiry_season_stove_weeks(self):
        f = management.renewal_eligible
        self.assertTrue(f(1, 1, 150))
        self.assertTrue(f(1, 10, 150))
        self.assertTrue(f(1, 145, 150))
        self.assertTrue(f(1, 150, 150))
        self.assertFalse(f(1, 11, 150))
        self.assertFalse(f(1, 125, 150))
        self.assertFalse(f(1, 144, 150))
        self.assertFalse(f(1, 145, 300))
        self.assertTrue(f(2, 1, 300))
        self.assertFalse(f(2, 145, 200))  # Ended before the late stove.
        self.assertFalse(f(1, 145, 150, active=False))
        self.assertFalse(f(1, 145, 150, kind='coach'))

    def test_server_action_refuses_outside_window(self):
        contract = dict(person={'id': 'p1', 'kind': 'player'},
                        annual_salary=10000000, end_turn=300,
                        active=True, renewal_eligible=False,
                        agent_asking_salary=12000000)
        state = dict(contracts=[contract], annual_payroll=10000000,
                     wage_budget=50000000)
        db = Mock()
        with patch.object(management, 'ensure'), \
             patch.object(management, 'turn', return_value=145), \
             patch.object(management, 'snapshot', return_value=state):
            with self.assertRaisesRegex(ValueError, '계약 만료 시즌'):
                management.action(db, 7, dict(action='renew', person='p1',
                                              annual_salary=15000000, years=2))
        db.execute.assert_not_called()

    def test_renewal_extends_from_expiry_season_to_full_new_seasons(self):
        contract = dict(person={'id': 'p1', 'kind': 'player', 'nickname': 'P1'},
                        annual_salary=10000000, end_turn=150,
                        active=True, renewal_eligible=True,
                        agent_asking_salary=12000000)
        state = dict(contracts=[contract], annual_payroll=10000000,
                     wage_budget=50000000)
        db = Mock()
        with patch.object(management, 'ensure'), \
             patch.object(management, 'turn', return_value=145), \
             patch.object(management, 'snapshot', return_value=state), \
             patch.object(management.catalog, 'display', return_value='P1'), \
             patch.object(management.club_messages, 'publish'):
            management.action(db, 7, dict(action='renew', person='p1',
                                          annual_salary=15000000, years=2))
        statement = db.execute.call_args_list[0]
        self.assertIn('UPDATE club_contracts', statement.args[0])
        # Season 1 expires at 150; two added full seasons end at 450.
        self.assertEqual(statement.args[1][1], 450)


class OperatorNewsAccessTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(':memory:')
        self.db.execute('CREATE TABLE users(id INTEGER PRIMARY KEY, name TEXT)')
        self.db.execute('CREATE TABLE careers(id INTEGER PRIMARY KEY, name TEXT)')
        self.db.execute('CREATE TABLE league_operators(user_id INTEGER PRIMARY KEY)')
        self.db.executemany('INSERT INTO users VALUES(?,?)', [(1, 'operator'), (2, 'manager')])
        self.db.executemany('INSERT INTO careers VALUES(?,?)', [(11, 'Alpha'), (12, 'Beta')])
        self.db.execute('INSERT INTO league_operators VALUES(1)')
        news.init(self.db)
        news.publish(self.db, 11, 'news-a', 1, 4, 'LCK headline',
                     'LCK story', [{'kind': 'team', 'entity': 'Alpha'}], 'LCK')
        news.publish(self.db, 12, 'news-b', 1, 5, 'LEC headline',
                     'LEC story', [{'kind': 'team', 'entity': 'Beta'}], 'LEC')
        self.db.execute('''CREATE TABLE league_rumors(
            id INTEGER PRIMARY KEY,league TEXT,season INTEGER,week INTEGER,
            headline TEXT,body TEXT,subjects TEXT)''')
        self.db.execute('''INSERT INTO league_rumors
            (league,season,week,headline,body,subjects)
            VALUES('LPL',1,6,'Rumor headline','Rumor story','[]')''')

    def tearDown(self):
        self.db.close()

    def test_operator_sees_all_leagues_without_club_membership(self):
        items = news.operator_feed(self.db, 1)
        self.assertEqual({i['headline'] for i in items},
                         {'LCK headline', 'LEC headline', 'Rumor headline'})
        self.assertEqual(items[0]['headline'], 'Rumor headline')

    def test_operator_can_select_one_league(self):
        self.assertEqual([i['headline'] for i in news.operator_feed(self.db, 1, 'LEC')],
                         ['LEC headline'])

    def test_non_operator_cannot_access_global_feed(self):
        with self.assertRaises(PermissionError):
            news.operator_feed(self.db, 2)


if __name__ == '__main__':
    unittest.main()
