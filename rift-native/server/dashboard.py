"""FM-style dashboard assembled from authoritative online game records."""
import json
import catalog
import clubs
import recruitment
import management
import analytics
import club_messages
import news

def league_table(db,league,season):
    names={p['team'] for p in catalog.teams() if p['league']==league}
    names.update(row[0] for row in db.execute('SELECT c.name FROM careers c JOIN club_profiles p ON p.career_id=c.id WHERE p.league=?',(league,)))
    table={name:dict(team=name,played=0,wins=0,losses=0,sets_won=0,sets_lost=0) for name in names}
    seen=set()
    for week,home,away,raw in db.execute("SELECT f.week,c.name,f.opponent,f.result FROM fixtures f JOIN careers c ON c.id=f.career_id WHERE f.season=? AND f.competition=? AND f.state='finished' ORDER BY f.id",(season,league)):
        key=(week,*sorted((home,away)))
        if key in seen:continue
        seen.add(key);result=json.loads(raw);score=result.get('score')
        if not score:continue
        for team,sw,sl in ((home,score[0],score[1]),(away,score[1],score[0])):
            if team not in table:continue
            row=table[team];row['played']+=1;row['wins']+=int(sw>sl);row['losses']+=int(sw<sl);row['sets_won']+=sw;row['sets_lost']+=sl
    rows=sorted(table.values(),key=lambda p:(-p['wins'],p['sets_lost']-p['sets_won'],p['team']))
    rank=0;previous=None
    for i,row in enumerate(rows):
        record=(row['wins'],row['sets_won']-row['sets_lost'])
        if record!=previous:rank=i+1;previous=record
        row['rank']=rank if row['played'] else None
    return rows

def last_five(db,team):
    items=[];seen=set()
    for fid,season,week,home,away,raw in db.execute("SELECT f.id,f.season,f.week,c.name,f.opponent,f.result FROM fixtures f JOIN careers c ON c.id=f.career_id WHERE f.state='finished' AND (c.name=? OR f.opponent=?) ORDER BY f.season DESC,f.week DESC,f.id DESC",(team,team)):
        key=(season,week,*sorted((home,away)))
        if key in seen:continue
        seen.add(key);result=json.loads(raw);is_home=home==team;won=result['winner']==(0 if is_home else 1)
        score=result.get('score',[])
        items.append(dict(fixture=fid,season=season,week=week,opponent=away if is_home else home,won=won,score=score if is_home else list(reversed(score))))
        if len(items)==5:break
    return items

def cash_history(db,career):
    cash=db.execute('SELECT cash FROM club_finances WHERE career_id=?',(career,)).fetchone()[0]
    initial=cash-db.execute('SELECT COALESCE(SUM(amount),0) FROM finance_ledger WHERE career_id=?',(career,)).fetchone()[0]
    points=[dict(season=1,week=1,cash=initial)];balance=initial
    for season,week,amount in db.execute('SELECT season,week,SUM(amount) FROM finance_ledger WHERE career_id=? GROUP BY season,week ORDER BY season,week',(career,)):
        balance+=amount;points.append(dict(season=season,week=week,cash=balance))
    return points[-24:]

def snapshot(db,career,user):
    management.ensure(db,career)
    name,season,week=db.execute('SELECT name,season,week FROM careers WHERE id=?',(career,)).fetchone()
    profile=clubs.profile(db,career);league=profile['league']
    stats=analytics.hub(db,career,season);by_id={p['id']:p for p in stats['players']}
    lineup=[]
    for p in recruitment.view(db,career)['roster']:
        record=by_id.get(p['id'])
        lineup.append(dict(person=p,games=record['games'] if record else 0,rating=record['rating'] if record else None,
                           kills=record['kills'] if record else 0,deaths=record['deaths'] if record else 0,assists=record['assists'] if record else 0,cs=record['cs'] if record else 0))
    next_game=db.execute("SELECT id,season,week,opponent,competition,stage,best_of,state FROM fixtures WHERE career_id=? AND state IN ('scheduled','queued') ORDER BY season,week,id LIMIT 1",(career,)).fetchone()
    next_fixture=dict(zip(('id','season','week','opponent','competition','stage','best_of','state'),next_game)) if next_game else None
    table=league_table(db,league,season)
    finances=management.snapshot(db,career)
    spent=-db.execute("SELECT COALESCE(SUM(amount),0) FROM finance_ledger WHERE career_id=? AND season=? AND category='transfer' AND amount<0",(career,season)).fetchone()[0]
    return dict(club=name,league=league,season=season,week=week,inbox=club_messages.inbox(db,career,user)[:8],
                news=news.feed(db,user,career)[:4],standings=table,rank=next((r['rank'] for r in table if r['team']==name),None),
                lineup=lineup,next_fixture=next_fixture,opponent_form=last_five(db,next_fixture['opponent']) if next_fixture else [],
                transfer_budget=finances['transfer_budget'],transfer_spent=spent,cash=finances['cash'],cash_history=cash_history(db,career),
                annual_payroll=finances['annual_payroll'],wage_budget=finances['wage_budget'],source='online-game-records')
