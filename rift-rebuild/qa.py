"""Replay audits and screenshots of the application's own framebuffer."""
import os,time,json,statistics
os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
from pathlib import Path
from unittest.mock import patch
import pygame as pg
from app import App
from replay import load
from terrain import Terrain
ROOT=Path(__file__).parent
def main():
    data=load(ROOT/'runs/match-1.json.gz');terrain=Terrain();violations=[]
    for f in data['frames']:
        for uid,x,y,hp,_,_ in f['units']:
            if hp>0 and not terrain.legal((x,y)):violations.append((f['t'],uid,x,y))
    assert not violations,violations[:10]
    assert data['attack_audit']['violations']==0
    with patch.object(App,'start'):app=App(headless=True)
    try:
        app.loaded=data;app.poll();app.paused=True;app.time=60;app.update_frame();app.run(60,ROOT/'runs/overview.png')
        # End-to-end camera test: follow an upcoming kill through pre-roll.
        index=next((i for i,c in enumerate(data['clips']) if c['kills']),0);app.choose(index);app.phase='clip';app.paused=True
        kill=next((a for a in data['clips'][index]['anchors'] if a['kind']=='kill'),data['clips'][index]['anchors'][0]);app.time=kill['t']-.4;app.update_frame()
        app.run(90,ROOT/'runs/combat.png')
        for tab in ('gold','damage','items'):
            app.tab=tab;app.run(30,ROOT/'runs'/f'{tab}.png')
        # Verify wall-clock 1x without sleeping through the entire game.
        app.paused=False;before=app.time;app.update(.75);assert abs(app.time-before-.75)<.001
        app.paused=True;app.render_ms=[];start=time.perf_counter();app.run(300);elapsed=time.perf_counter()-start
        result=dict(fps=round(300/elapsed,2),mean_render_ms=round(statistics.mean(app.render_ms),2),p95_render_ms=round(sorted(app.render_ms)[284],2),
                    walk_violations=len(violations),attack_audit=data['attack_audit'],game=data['result'],clips=len(data['clips']),
                    regular_speed=1,watch_seconds=round(sum(c['end']-c['start'] for c in data['clips'])))
        (ROOT/'runs/validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in result.items() if k!='game'},indent=2))
    finally:app.close()
if __name__=='__main__':main()
