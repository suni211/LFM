"""Authenticated, read-only match discovery; spectator accounts need no club membership."""
import json

def listing(db,fixture=None,page=0,league=''):
    if fixture is not None and (type(fixture) is not int or not 1<=fixture<=2**63-1):raise ValueError('invalid match')
    if type(page) is not int or not 0<=page<=100000 or not isinstance(league,str) or len(league)>120:raise ValueError('invalid filter')
    where="f.state IN ('queued','finished')";args=[]
    if fixture is not None:where+=' AND f.id=?';args.append(fixture)
    if league:where+=' AND p.league=?';args.append(league)
    total=db.execute('SELECT COUNT(*) FROM fixtures f JOIN club_profiles p ON p.career_id=f.career_id WHERE '+where,args).fetchone()[0]
    rows=db.execute('''SELECT f.id,f.career_id,c.name,f.opponent,p.league,f.season,f.week,f.state,f.best_of,f.competition,f.stage,f.result,s.state
        FROM fixtures f JOIN careers c ON c.id=f.career_id JOIN club_profiles p ON p.career_id=f.career_id
        LEFT JOIN match_series s ON s.fixture_id=f.id WHERE '''+where+' ORDER BY f.season DESC,f.week DESC,f.id DESC LIMIT 50 OFFSET ?',(*args,page*50)).fetchall()
    games=[]
    for fid,cid,home,away,region,season,week,state,best_of,competition,stage,result,raw in rows:
        item=dict(id=fid,career_id=cid,home=home,opponent=away,league=region,season=season,week=week,state=state,best_of=best_of,competition=competition,stage=stage,can_control=False)
        if fixture is not None:
            source=json.loads(raw) if raw else {};saved=json.loads(result) if result else None
            # Do not publish draft choices, pools, readiness, feedback notes or tactics.
            sets=source.get('sets') or (saved or {}).get('sets',[])
            allowed=('players','time','blue','club_winner','highlights','replay_set')
            public_sets=[{k:g[k] for k in allowed if k in g} for g in sets]
            item['series']=dict(phase=source.get('phase','finished' if saved else 'ready'),sets=public_sets)
            item['result']=dict(sets=public_sets,score=saved.get('score',[]),winner=saved.get('winner'),highlights=saved.get('highlights',[])) if saved else None
        games.append(item)
    return dict(fixtures=games,total=total,page=page,page_size=50,leagues=[r[0] for r in db.execute("SELECT DISTINCT p.league FROM fixtures f JOIN club_profiles p ON p.career_id=f.career_id WHERE f.state IN ('queued','finished') ORDER BY p.league")])
