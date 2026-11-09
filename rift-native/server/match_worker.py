"""Run a single match worker beside the API on the game-server."""
import argparse
import json
from contextlib import closing
from pathlib import Path
import sys
import time
import threading
import fixtures
import series_state
import manual_draft
import match_people
from series import auto_draft,Draft
from worker_lock import exclusive
from highlight_recording import Recorder
from spectator_recording import SpectatorRecorder
from server import connect, init

def team_styles(db,fixture,blue):
    import tactics
    career,opponent=db.execute('SELECT career_id,opponent FROM fixtures WHERE id=?',(fixture,)).fetchone()
    def plan(cid):
        return tactics.load(db,cid) if cid else tactics._playbook().default_plan()
    other=db.execute('SELECT id FROM careers WHERE name=?',(opponent,)).fetchone()
    own,opp=plan(career),plan(other[0] if other else None)
    plans=(own,opp) if blue==0 else (opp,own)
    styles=tuple(item['mid']['order'] if item['mid']['order'] in ('오브젝트 중심','한타 중심','사이드 압박') else '균형' for item in plans)
    return styles,plans

def maintain_deadlines(stop):
    """Keep response deadlines running while another fixture is being simulated."""
    while not stop.wait(1):
        try:
            with closing(connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                for fixture,seed,raw in db.execute("""SELECT f.id,f.seed,s.state FROM fixtures f
                    JOIN match_series s ON s.fixture_id=f.id WHERE f.state='queued'""").fetchall():
                    state=json.loads(raw)
                    changed=series_state.tick(state,seed,time.time())
                    changed=series_state.finish_swap(state,time.time()) or changed
                    if changed:series_state.put(db,fixture,state)
                db.execute('COMMIT')
        except Exception:
            import traceback
            traceback.print_exc()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--engine', type=Path, required=True)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0,str(args.engine.resolve()))
    from engine import Match
    from data import KITS, ROLES
    from replay import clips
    from server import DB
    init()
    with exclusive(DB.with_suffix('.worker.lock')):
        stop=threading.Event()
        threading.Thread(target=maintain_deadlines,args=(stop,),daemon=True).start()
        while True:
            with closing(connect()) as db:
                db.execute('BEGIN IMMEDIATE')
                jobs = db.execute("""SELECT f.id,f.seed,s.state FROM fixtures f
                    LEFT JOIN match_series s ON s.fixture_id=f.id
                    WHERE f.state='queued' ORDER BY f.id""").fetchall()
                job = None
                for fixture,seed,raw in jobs:
                    try:
                        state = json.loads(raw) if raw else None
                        if state and series_state.tick(state,seed,time.time()):
                            series_state.put(db,fixture,state)
                        if state and state['phase']=='draft_pending':
                            if state.get('manual_draft'):manual_draft.start(state)
                            else:series_state.prepare_draft(state,seed,KITS,ROLES,time.time())
                            series_state.put(db,fixture,state)
                        if state and state['phase']=='draft':
                            import training
                            state['pools']=training.pools_for_fixture(db,fixture)
                            manual_draft.bot(state,seed,KITS,ROLES,time.time())
                            series_state.put(db,fixture,state)
                        if state and series_state.finish_swap(state,time.time()):series_state.put(db,fixture,state)
                        if job is None and (state is None or state['phase']=='ready'):
                            job = fixture,seed,state
                    except Exception:
                        import traceback
                        traceback.print_exc()
                        db.execute("UPDATE fixtures SET state='failed' WHERE id=? AND state='queued'",(fixture,))
                db.execute('COMMIT')
            if job:
                fixture,seed,state = job
                try:
                    draft = None
                    pools={'0':{},'1':{}}
                    if state:
                        seed += len(state['sets'])
                        with closing(connect()) as db:
                            import training
                            pools=training.pools_for_fixture(db,fixture)
                        state['pools']=pools
                        if state.get('roster'):
                            draft=Draft(state['first'],state['blue'],tuple(state['draft']),tuple(tuple(team) for team in state['roster']))
                        else:draft = auto_draft(seed,KITS,ROLES,state['first'],state['blue'],preferred={0:pools.get('0',{}),1:pools.get('1',{})})
                        state['draft'] = list(draft.actions)
                        with closing(connect()) as db:
                            series_state.put(db,fixture,state)
                    styles,plans=('균형','균형'),None
                    if state is not None:
                        with closing(connect()) as db:
                            styles,plans=team_styles(db,fixture,state.get('blue',0))
                    match = Match(seed,draft.roster,styles,plans) if draft else Match(seed,styles=styles,plans=plans)
                    with closing(connect()) as db:
                        match_people.apply(db,fixture,match,draft.blue if draft else 0)
                    spectator=SpectatorRecorder(DB.parent/'spectator',fixture,len(state['sets']) if state else 0,draft.blue if draft else 0)
                    recorder = Recorder(clips)
                    recorder.record(match)
                    spectator.record(match)
                    while match.winner is None:
                        match.step()
                        recorder.record(match)
                        spectator.record(match)
                    spectator.record(match,final=True)
                    result = match.result()
                    result['replay_set']=len(state['sets']) if state else 0
                    offset = sum(len(game['highlights']) for game in state['sets']) if state else 0
                    result['highlights'] = recorder.finish(match,DB.parent / 'highlights',fixture,offset)
                    with closing(connect()) as db:
                        db.execute('BEGIN IMMEDIATE')
                        if state:
                            result = series_state.set_complete(state,result,draft,time.time())
                            series_state.put(db,fixture,state)
                        if result is not None:
                            fixtures.complete(db,fixture,result)
                        db.execute('COMMIT')
                except Exception:
                    import traceback
                    traceback.print_exc()
                    with closing(connect()) as db:
                        db.execute("UPDATE fixtures SET state='failed' WHERE id=? AND state='queued'",(fixture,))
            if args.once:
                stop.set()
                break
            if not job:
                time.sleep(2)

if __name__ == '__main__':
    main()
