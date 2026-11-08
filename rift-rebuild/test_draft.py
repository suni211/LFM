import unittest
from draft import Draft
from data import KITS, ROLES
from engine import Match


class DraftTests(unittest.TestCase):
    def test_auto_fills_unique_role_roster(self):
        draft = Draft()
        draft.auto()
        roster = draft.roster()
        names = [champion for team in roster for champion in team]
        self.assertEqual(len(set(names)), 10)
        self.assertEqual(len(draft.banned), 6)
        for team in roster:
            for role, champion in zip(ROLES, team):
                self.assertIn(role, KITS[champion].roles)
        Match(seed=2, roster=roster)

    def test_marksman_pool_cannot_be_banned_out(self):
        draft = Draft()
        self.assertTrue(draft.choose('Ashe'))
        self.assertFalse(draft.choose('Sivir'))
        self.assertTrue(draft.choose('Jax'))

    def test_pick_must_match_the_open_role(self):
        draft = Draft()
        for _ in range(6):
            self.assertTrue(draft.choose(draft.suggest()))
        self.assertEqual(draft.turn(), ('pick', 0, 'TOP'))
        self.assertFalse(draft.choose('Ashe'))
        legal = [champion for champion in KITS if draft.legal(champion)]
        self.assertTrue(legal)
        self.assertTrue(all('TOP' in KITS[champion].roles for champion in legal))

    def test_player_pool_is_preferred(self):
        pools = ([{}, {}, {'TwistedFate': 99}, {}, {}], [{} for _ in range(5)])
        draft = Draft(pools)
        while draft.turn() != ('pick', 0, 'MID'):
            champion = draft.suggest()
            if champion == 'TwistedFate':
                champion = next(name for name in KITS if name != 'TwistedFate' and draft.legal(name))
            draft.choose(champion)
        self.assertEqual(draft.suggest(), 'TwistedFate')


class DraftAppTests(unittest.TestCase):
    def test_match_only_opens_draft(self):
        import os
        os.environ['SDL_VIDEODRIVER'] = 'dummy'
        os.environ['SDL_AUDIODRIVER'] = 'dummy'
        from app import App
        application = App(headless=True, match_only=True)
        try:
            application.run(frames=2)
            self.assertEqual(application.flow, 'draft')
            self.assertIsNone(application.manager)
            self.assertIn('draft_auto', application.buttons)
            application.draft.auto()
            self.assertTrue(application.draft.done)
        finally:
            application.close()


if __name__ == '__main__':
    unittest.main()
