import os
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
import unittest
from unittest.mock import patch
from app import App,W,H
from engine import Match
from replay import snapshot
class AppTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with patch.object(App,'start'):cls.app=App(headless=True)
        m=Match();f=snapshot(m)
        cls.app.loaded=dict(frames=[f,snapshot(m)],meta=[dict(id=u.id,name=u.name,team=u.team,kind=u.kind,minor=u.minor) for u in m.units],events=[],result=m.result(),clips=[],seed=1)
        cls.app.poll()
    @classmethod
    def tearDownClass(cls):cls.app.close()
    def test_lower_tab_exclusive(self):
        a=self.app
        for tab in ('items','gold','damage'):
            a.tab=tab;calls=[]
            with patch.object(a,'table',side_effect=lambda:calls.append('items')),patch.object(a,'goldgraph',side_effect=lambda:calls.append('gold')),patch.object(a,'damagegraph',side_effect=lambda:calls.append('damage')):a.lower()
            self.assertEqual(calls,[tab])
    def test_regular_speed(self):
        a=self.app;a.phase='clip';a.paused=False;a.time=2;a.clip_index=0;a.data['clips']=[dict(start=0,end=100,label='솔로 킬',ids=[0],anchors=[dict(t=20,p=(100,100),ids=[0])])]
        a.update(.5);self.assertEqual(a.time,2.5)
    def test_camera_tracks_next_kill_not_other_side(self):
        a=self.app;a.phase='clip';a.overview=False;a.time=10;a.clip_index=0
        a.data['clips']=[dict(start=0,end=100,label='한타',ids=[0,20],anchors=[dict(t=5,p=(20,490),ids=[0]),dict(t=20,p=(490,20),ids=[20])])]
        a.positions={0:(20,490),20:(490,20)};a.states={0:[0,20,490,100],20:[20,490,20,100]};a.players=[]
        x,y,zoom=a.focus();self.assertGreater(x,400);self.assertLess(y,100)
    def test_requested_fonts(self):
        a=self.app;self.assertIn((18,True),a.fonts);self.assertIn((14,False),a.fonts)
if __name__=='__main__':unittest.main()
