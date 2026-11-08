"""Permanent in-game season honors from finished, attributable match records.

Never fabricate player statistics or infer an unverified person's identity.
First/second/third All-Pro selections are positional, coach awards use recorded
team performance and known manager identity, and Worlds MVP requires a completed
Worlds final with identifiable players on the winning side.
"""
import json
import math
import time
from collections import defaultdict, Counter
import catalog

ROLES=("TOP","JUNGLE","MID","ADC","SUPPORT")
CATEGORIES=("all_pro","coach","rookie","worlds_mvp")


def init(db):
    db.executescript("""CREATE TABLE IF NOT EXISTS season_honors(
        season INTEGER NOT NULL,league TEXT NOT NULL,category TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT '',award_rank INTEGER NOT NULL DEFAULT 1,
        person_id TEXT NOT NULL,person_name TEXT NOT NULL,club TEXT NOT NULL,
        score REAL NOT NULL,evidence TEXT NOT NULL,
        recorded_at INTEGER NOT NULL,
        PRIMARY KEY(season,league,category,role,award_rank));
        CREATE TABLE IF NOT EXISTS season_archives(
        season INTEGER PRIMARY KEY,locked_at INTEGER NOT NULL);""")


def _people(db):
    items={p['id']:p for p in catalog.load()['people']}
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='generated_people'").fetchone():
        for (raw,) in db.execute("SELECT payload FROM generated_people"):
            p=json.loads(raw)
            items[p['id']]=p
    return items


def _games(db,season,league=None):
    sql="""SELECT f.id,f.week,c.name,f.opponent,f.competition,f.stage,f.result
        FROM fixtures f JOIN careers c ON c.id=f.career_id
        JOIN club_profiles cp ON cp.career_id=c.id
        WHERE f.season=? AND f.state='finished' AND f.result IS NOT NULL"""
    params=[season]
    if league is not None:
        sql+=" AND cp.league=? AND f.competition=?"
        params.extend([league,league])
    sql+=" ORDER BY f.id"
    visited=set()
    for fid,week,home,away,competition,stage,raw in db.execute(sql,params):
        key=(week,competition,stage,tuple(sorted((home,away))))
        if key in visited:continue
        visited.add(key)
        try:result=json.loads(raw)
        except (ValueError,TypeError):continue
        if not isinstance(result,dict):continue
        yield dict(id=fid,week=week,home=home,away=away,
                   competition=competition,stage=stage,result=result)


def _individuals(events):
    """Return player aggregates, keyed by immutable person id."""
    people={}
    for event in events:
        for game in event['result'].get('sets',[event['result']]):
            if not isinstance(game,dict): continue
            players=game.get('players',[])
            if not isinstance(players,list):continue
            winner=game.get('winner')
            blue=game.get('blue',0)
            for index,p in enumerate(players):
                pid=p.get('player_id')
                role=p.get('role')
                if not pid or role not in ROLES:continue
                team=p.get('team',index//5)
                if team not in (0,1): continue
                club=event['home'] if team==blue else event['away']
                key=str(pid)
                row=people.setdefault(key,dict(id=key,name=p.get('player_name') or key,
                    role=role,games=0,wins=0,kills=0,deaths=0,assists=0,
                    damage=0,rating_sum=0,clubs=Counter()))
                kda=p.get('kda',[0,0,0])
                if not isinstance(kda,(list,tuple)) or len(kda)!=3: kda=[0,0,0]
                k,d,a=[int(x) if isinstance(x,(int,float)) else 0 for x in kda]
                damage=p.get('damage',0)
                damage=damage if isinstance(damage,(int,float)) else 0
                total=sum(q.get('damage',0) or 0 for j,q in enumerate(players)
                          if q.get('team',j//5)==team)
                share=damage/max(1,total)
                expected={'TOP':.2,'JUNGLE':.18,'MID':.25,'ADC':.25,'SUPPORT':.12}[role]
                won=(team==winner)
                rating=max(1,min(9.9,6+min(1.4,k*.18+a*.08)-min(3.5,d*.38)
                                 +(.5 if won else -.3)+(share-expected)*2))
                row['games']+=1
                row['wins']+=int(won)
                row['kills']+=k
                row['deaths']+=d
                row['assists']+=a
                row['damage']+=damage
                row['rating_sum']+=rating
                row['clubs'][club]+=1
    for p in people.values():
        p['rating']=round(p['rating_sum']/p['games'],3)
        p['win_rate']=round(p['wins']/p['games'],3)
        p['club']=p['clubs'].most_common(1)[0][0]
        p['score']=round(p['rating']*100+p['win_rate']*12+math.log1p(p['games'])*4,3)
    return people


def _honor(season,league,category,person,role='',award_rank=1):
    return dict(season=season,league=league,category=category,
                role=role,award_rank=award_rank,
                person_id=person['id'],person_name=person['name'],
                club=person.get('club',''),score=person['score'],
                evidence=dict(games=person.get('games',0),
                              wins=person.get('wins',0),rating=person.get('rating'),
                              win_rate=person.get('win_rate'),
                              calculation='in-game-match-results'))


def _rookie(db,person):
    if person.get('rookie') is True:return True
    return person.get('source')=='solo-queue' and not person.get('real_person')


def _league_honors(db,season,league,lookup):
    events=list(_games(db,season,league))
    players=_individuals(events)
    results=[]
    for role in ROLES:
        ranked=sorted((p for p in players.values() if p['role']==role),
                      key=lambda p:(-p['score'],-p['games'],p['id']))
        if not ranked:continue
        min_games=max(1,math.ceil(max(p['games'] for p in ranked)*.4))
        eligible=[p for p in ranked if p['games']>=min_games]
        for rank,p in enumerate(eligible[:3],1):
            results.append(_honor(season,league,'all_pro',p,role,rank))
    rookies=[p for p in players.values() if _rookie(db,lookup.get(p['id'],{}))]
    if rookies:
        eligible=sorted(rookies,key=lambda p:(-p['score'],-p['games'],p['id']))
        results.append(_honor(season,league,'rookie',eligible[0]))
    # A named manager can receive the coach award only when results exist.
    team_scores=defaultdict(lambda:[0,0])
    for game in events:
        score=game['result'].get('score')
        winner=game['result'].get('winner')
        if winner not in (0,1) or not isinstance(score,list) or len(score)!=2:continue
        for idx,club in enumerate((game['home'],game['away'])):
            team_scores[club][0]+=1
            team_scores[club][1]+=int(idx==winner)
    candidates=[]
    if team_scores and db.execute("SELECT 1 FROM sqlite_master WHERE name='manager_profiles'").fetchone():
        for cid,club,manager in db.execute("""SELECT c.id,c.name,m.name FROM careers c
            JOIN club_profiles p ON p.career_id=c.id
            JOIN manager_profiles m ON m.career_id=c.id WHERE p.league=?""",(league,)):
            if club not in team_scores or not manager or manager in ('AI 감독','감독'): continue
            played,wins=team_scores[club]
            candidates.append(dict(id='manager:'+str(cid),name=manager,club=club,
                                   games=played,wins=wins,rating=round(10*wins/played,3),
                                   win_rate=wins/played,
                                   score=round(wins/played*100+math.log1p(played)*4,3)))
    if candidates:
        winner=sorted(candidates,key=lambda x:(-x['score'],-x['games'],x['id']))[0]
        results.append(_honor(season,league,'coach',winner))
    return results


def _worlds_honor(db,season):
    """Winner-only MVP selected on the recorded final, never on a scheduled game."""
    finals=[g for g in _games(db,season) if g['competition'].casefold() in
            ('worlds','world championship','월즈','롤드컵')
            and g['stage'].casefold().replace(' ','_') in
            ('final','finals','grand_final','grand_finals','결승')]
    if not finals:return None
    final=finals[-1]
    result=final['result']
    if result.get('winner') not in (0,1):return None
    winner=final['home'] if result['winner']==0 else final['away']
    people=_individuals([final])
    best=sorted((p for p in people.values() if p['club']==winner),
                key=lambda p:(-p['score'],-p['games'],p['id']))
    return _honor(season,'Worlds','worlds_mvp',best[0]) if best else None


def calculate(db,season,league=None):
    if type(season) is not int or not 1<=season<=10000:raise ValueError('invalid season')
    import tier2_leagues
    leagues={c['league'] for c in catalog.teams() if c.get('league')}
    leagues.update(p[0] for p in db.execute('SELECT DISTINCT league FROM club_profiles'))
    if league is not None:
        if not isinstance(league,str) or len(league)>120:raise ValueError('invalid league')
        leagues={league}
    people=_people(db)
    awards=[]
    for item in sorted(leagues):
        if item in ('Worlds','MSI','First Stand'):continue
        awards.extend(_league_honors(db,season,item,people))
    if league in (None,'Worlds'):
        winner=_worlds_honor(db,season)
        if winner:awards.append(winner)
    return awards


def _persist(db,awards):
    for a in awards:
        db.execute("""INSERT OR IGNORE INTO season_honors
            (season,league,category,role,award_rank,person_id,person_name,club,score,evidence,recorded_at)
            VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
            (a['season'],a['league'],a['category'],a['role'],a['award_rank'],
             a['person_id'],a['person_name'],a['club'],a['score'],
             json.dumps(a['evidence'],ensure_ascii=False),int(time.time())))


def record_worlds_final(db,season):
    if db.execute("SELECT 1 FROM season_archives WHERE season=?",(season,)).fetchone():return
    mvp=_worlds_honor(db,season)
    if mvp:_persist(db,[mvp])


def finalize(db,season):
    if db.execute("SELECT 1 FROM season_archives WHERE season=?",(season,)).fetchone():return False
    _persist(db,calculate(db,season))
    db.execute("INSERT INTO season_archives VALUES(?,?)",(season,int(time.time())))
    return True


def history(db,season=None,league=None):
    if season is not None and (type(season) is not int or not 1<=season<=10000):
        raise ValueError('invalid season')
    if league is not None and (not isinstance(league,str) or len(league)>120):
        raise ValueError('invalid league')
    current=db.execute('SELECT season FROM online_clock WHERE id=1').fetchone()
    current=current[0] if current else 1
    year=season or current
    locked=bool(db.execute("SELECT 1 FROM season_archives WHERE season=?",(year,)).fetchone())
    where=["season=?"];params=[year]
    if league:
        where.append("league=?");params.append(league)
    rows=[]
    for item in db.execute("""SELECT season,league,category,role,award_rank,person_id,person_name,
        club,score,evidence FROM season_honors WHERE """+" AND ".join(where)+
        " ORDER BY league,category,award_rank,role",params):
        y,lg,cat,role,rank,pid,name,club,score,evidence=item
        rows.append(dict(season=y,league=lg,category=cat,role=role,award_rank=rank,
                         person_id=pid,person_name=name,club=club,score=score,
                         evidence=json.loads(evidence),status='final'))
    if not locked:
        saved={(x['league'],x['category'],x['role'],x['award_rank']) for x in rows}
        for award in calculate(db,year,league):
            key=(award['league'],award['category'],award['role'],award['award_rank'])
            if key not in saved:
                rows.append(dict(award,status='provisional'))
    seasons={current}
    seasons.update(s[0] for s in db.execute("SELECT DISTINCT season FROM fixtures"))
    seasons.update(s[0] for s in db.execute("SELECT season FROM season_archives"))
    import tier2_leagues
    league_names={r['league'] for r in catalog.teams() if r.get('league')}
    league_names.update(r[0] for r in db.execute("SELECT DISTINCT league FROM club_profiles"))
    return dict(season=year,current_season=current,
                finalized=locked,seasons=sorted(seasons,reverse=True),
                leagues=sorted(league_names),league=league or '',
                awards=sorted(rows,key=lambda x:(x['league'],x['category'],x['award_rank'],x['role'])),
                rules='게임 내 종료 경기 기록만 집계. 검증할 기록이나 실명 정보가 없으면 수상자 미선정.')
