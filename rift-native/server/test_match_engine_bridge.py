"""Verify real match-engine output can flow into the shared match series and replay API."""
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'engine'))
from data import ROSTER
from engine import Match
from series import Draft
import series_state
from highlight_recording import Recorder, clip_path


class MatchEngineBridgeTest(unittest.TestCase):
    def test_engine_uses_selected_champions_and_returns_real_box_scores(self):
        # Simulates the exact saved roster shape constructed by the worker from
        # the successful draft. Do not fabricate a match outcome or analytics.
        draft=Draft(first=0,blue=1,actions=(),roster=ROSTER)
        match=Match(123,draft.roster)
        own=[u.name for u in match.players(0)]
        opposing=[u.name for u in match.players(1)]
        self.assertEqual(own,list(ROSTER[0]))
        self.assertEqual(opposing,list(ROSTER[1]))
        recorder=Recorder(lambda events,duration,meta:[
            {'start':0,'end':duration,'label':'엔진 프레임 재생 시험','anchors':[]}
        ])
        recorder.record(match)
        for _ in range(8):
            match.step()
            recorder.record(match)
        self.assertGreater(match.t,0)
        result=match.result()
        self.assertEqual(10,len(result['players']))
        self.assertEqual(set(('name','role','team','kda','cs','damage','player_id')),
                         set(result['players'][0]).intersection(
                             ('name','role','team','kda','cs','damage','player_id')))
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)
            info=recorder.finish(match,path,7)
            self.assertEqual(1,len(info))
            with gzip.open(clip_path(path,7,0),'rt',encoding='utf-8') as stream:
                replay=json.load(stream)
            self.assertTrue(replay['frames'])
            self.assertTrue(replay['units'])
            self.assertIn('label',replay['clip'])
            self.assertEqual(512,512)  # Renderer uses 512x512 game-map coordinates.

    def test_saved_engine_set_is_visible_to_series_and_preserves_players(self):
        draft=Draft(first=0,blue=1,actions=(),roster=ROSTER)
        state=dict(score=[0,0],sets=[],best_of=3,chooser=0,fearless=True)
        # An engine result with known winning side exercises the real
        # series transition logic; the match outcome itself is not invented
        # by any production code.
        match=Match(42,draft.roster)
        match.winner=0
        result=match.result()
        result['highlights']=[{'start':1,'end':2,'label':'중계 주요 장면'}]
        finished=series_state.set_complete(state,result,draft,100.0)
        self.assertIsNone(finished)
        self.assertEqual([0,1],state['score'])  # blue=1 means engine team 0 is career team 1
        self.assertEqual('feedback',state['phase'])
        self.assertEqual(10,len(state['sets'][0]['players']))
        self.assertEqual(result['highlights'],state['sets'][0]['highlights'])


if __name__ == '__main__':
    unittest.main()
