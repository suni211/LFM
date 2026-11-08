"""2026 international allocations. Awards come exclusively from finished game fixtures."""
import json
import catalog
SOURCE='https://lolesports.com/en-US/lolesports/news/msi-and-worlds-updates'
HANDBOOK='https://lolesports.com/en-US/season/115547545029543948/handbook'
FST={'LCK':2,'LPL':2,'LEC':1,'LCS':1,'LCP':1,'CBLOL':1}
MSI={'LCK':2,'LPL':2,'LEC':2,'LCS':2,'LCP':2,'CBLOL':1}
WORLDS={'LCK':3,'LPL':3,'LEC':3,'LCS':3,'LCP':3,'CBLOL':2}

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS international_placements(season INTEGER NOT NULL,event TEXT NOT NULL,place INTEGER NOT NULL,team TEXT NOT NULL,league TEXT NOT NULL,fixture_id INTEGER NOT NULL REFERENCES fixtures(id),PRIMARY KEY(season,event,place));''')

def event_name(value):
    key=value.casefold().replace(' ','').replace('_','')
    return 'First Stand' if key in ('firststand','fst') else 'MSI' if key in ('msi','midseasoninvitational') else 'Worlds' if key in ('worlds','worldchampionship','월즈','롤드컵') else None

def team_league(db,name):
    row=db.execute('SELECT p.league FROM careers c JOIN club_profiles p ON p.career_id=c.id WHERE c.name=?',(name,)).fetchone()
    if row:return row[0]
    leagues={p['league'] for p in catalog.load()['people'] if p.get('team')==name and p.get('league') in WORLDS}
    return next(iter(leagues)) if len(leagues)==1 else None

def observe(db,fixture,result):
    row=db.execute("SELECT f.season,f.competition,f.stage,c.name,f.opponent,f.state FROM fixtures f JOIN careers c ON c.id=f.career_id WHERE f.id=?",(fixture,)).fetchone()
    if not row or row[5]!='finished':return
    season,competition,stage,home,away,_=row;event=event_name(competition)
    stage=stage.casefold().replace(' ','_').replace('-','_')
    final=stage in ('final','finals','grand_final','grand_finals','결승')
    lower_final=stage in ('lower_final','losers_final','패자조_결승')
    if not event or not (final or lower_final):return
    score=result.get('score',[]);winner=result.get('winner')
    if winner not in (0,1) or len(score)!=2 or max(score)<3:return
    won,lost=(home,away) if winner==0 else (away,home)
    placements=[(1,won),(2,lost)] if final else [(3,lost)]
    for rank,team in placements:
        league=team_league(db,team)
        if not league:continue
        existing=db.execute('SELECT fixture_id,team FROM international_placements WHERE season=? AND event=? AND place=?',(season,event,rank)).fetchone()
        # Conflicting duplicate finals must not silently overwrite the season champion.
        if existing and existing!=(fixture,team):continue
        db.execute('INSERT OR IGNORE INTO international_placements VALUES(?,?,?,?,?,?)',(season,event,rank,team,league,fixture))

def reconcile(db,season):
    for fid,raw in db.execute("SELECT id,result FROM fixtures WHERE season=? AND state='finished' AND result IS NOT NULL",(season,)).fetchall():
        observe(db,fid,json.loads(raw))

def playoff_eligibility(db,season,team,league):
    rows=db.execute("SELECT c.name,f.opponent,f.stage,f.state FROM fixtures f JOIN careers c ON c.id=f.career_id WHERE f.season=? AND f.competition=?",(season,league)).fetchall()
    stages={'playoff','playoffs','upper_final','lower_final','semifinal','quarterfinal','final','finals','grand_final'}
    field=[r for r in rows if r[2].casefold().replace(' ','_') in stages]
    if any(team in (r[0],r[1]) for r in field):return True
    if any(r[2] in ('final','finals','grand_final') and r[3]=='finished' for r in field):return False
    return None

def snapshot(db,season):
    reconcile(db,season)
    placements={}
    for event,place,team,league,fid in db.execute('SELECT event,place,team,league,fixture_id FROM international_placements WHERE season=?',(season,)):
        placements.setdefault(event,{})[place]=dict(team=team,league=league,fixture=fid)
    fst=placements.get('First Stand',{});msi=placements.get('MSI',{})
    bypass=next((fst[p]['league'] for p in (1,2) if p in fst and MSI.get(fst[p]['league'],0)>1),None)
    champion=msi.get(1);runner=msi.get(2);eligibility=None
    bonus=None
    if champion:
        eligibility=playoff_eligibility(db,season,champion['team'],champion['league'])
        if runner and runner['league']!=champion['league']:bonus=runner['league']
        elif runner and msi.get(3) and msi[3]['league']!=champion['league']:bonus=msi[3]['league']
    rows=[]
    for league,base in WORLDS.items():
        extra=int(bonus==league)
        champion_extra=int(bool(champion and champion['league']==league and eligibility is True))
        pending=bool(champion and champion['league']==league and eligibility is None)
        rows.append(dict(league=league,first_stand_slots=FST[league],msi_slots=MSI[league],msi_bracket_slots=2 if bypass==league else 1,msi_second_seed_pending=bypass is None and MSI[league]>1,worlds_base=base,worlds_confirmed_slots=base+extra+champion_extra,worlds_extra_seed=extra,worlds_champion_slot=champion_extra,worlds_champion_pending=pending))
    # Career events are scheduled by season/week, never by Gregorian dates.
    events=[
        dict(name='First Stand',start_week=28,end_week=35,entrants=8,format='4팀 더블 엘리미네이션 2개 조 → 4강·결승, 전 경기 BO5',source='https://lolesports.com/en-gb/news/fst-2026-primer'),
        dict(name='MSI',start_week=89,end_week=96,entrants=11,format='4팀 플레이인 → 8팀 더블 엘리미네이션',source=SOURCE),
        dict(name='Worlds',start_week=131,end_week=144,entrants=19,format='4팀 BO5 플레이인 → 16팀 스위스 → 8강 토너먼트',source=SOURCE)
    ]
    return dict(season=season,rules_year=2026,allocations=rows,events=events,first_stand_bye_region=bypass,msi_champion=champion,msi_champion_playoffs=eligibility,worlds_extra_region=bonus,results=placements,source=SOURCE)
