"""Board requirements and fan expectations, evaluated against recorded club results."""
import json
import math
import clubs

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS club_expectations(career_id INTEGER NOT NULL,season INTEGER NOT NULL,audience TEXT NOT NULL,goals TEXT NOT NULL,PRIMARY KEY(career_id,season,audience));
        CREATE TABLE IF NOT EXISTS sentiment_events(career_id INTEGER NOT NULL,event_key TEXT NOT NULL,season INTEGER NOT NULL,week INTEGER NOT NULL,board_delta INTEGER NOT NULL,fan_delta INTEGER NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(career_id,event_key));''')

def change(db,career,key,board,fans,reason):
    if db.execute('SELECT 1 FROM sentiment_events WHERE career_id=? AND event_key=?',(career,key)).fetchone():return
    before=db.execute('SELECT board,fans FROM club_finances WHERE career_id=?',(career,)).fetchone()
    db.execute('UPDATE club_finances SET board=MIN(100,MAX(0,board+?)),fans=MIN(100,MAX(0,fans+?)) WHERE career_id=?',(board,fans,career))
    after=db.execute('SELECT board,fans FROM club_finances WHERE career_id=?',(career,)).fetchone()
    season,week=db.execute('SELECT season,week FROM careers WHERE id=?',(career,)).fetchone()
    db.execute('INSERT INTO sentiment_events VALUES(?,?,?,?,?,?,?)',(career,key,season,week,after[0]-before[0],after[1]-before[1],reason))

def snapshot(db,career,state):
    import dashboard
    season,week=db.execute('SELECT season,week FROM careers WHERE id=?',(career,)).fetchone()
    league=clubs.profile(db,career)['league'];name=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    table=dashboard.league_table(db,league,season);own=next((t for t in table if t['team']==name),{})
    target=max(1,math.ceil(len(table)/2));played=own.get('played',0);rate=round(own.get('wins',0)*100/max(1,played),1)
    recent=dashboard.last_five(db,name);wins=sum(g['won'] for g in recent)
    definitions={'board':[dict(key='rank',title='리그 상위 절반 진입',target=target),dict(key='cash',title='현금 잔액 0원 이상 유지'),dict(key='wages',title='급여 예산 준수')],
                 'fans':[dict(key='winrate',title='시즌 승률 50% 이상',target=50),dict(key='form',title='최근 5경기에서 3승 이상',target=3)]}
    goals={}
    for audience,defaults in definitions.items():
        db.execute('INSERT OR IGNORE INTO club_expectations VALUES(?,?,?,?)',(career,season,audience,json.dumps(defaults,ensure_ascii=False)))
        rows=json.loads(db.execute('SELECT goals FROM club_expectations WHERE career_id=? AND season=? AND audience=?',(career,season,audience)).fetchone()[0]);out=[]
        for goal in rows:
            key=goal['key'];pending=False
            if key=='rank':pending=not played;met=bool(own.get('rank')) and own['rank']<=goal['target'];progress=(str(own.get('rank') or '미정')+'위 / 목표 '+str(goal['target'])+'위')
            elif key=='cash':met=state['cash']>=0;progress=format(state['cash'],',')+'원'
            elif key=='wages':met=state['annual_payroll']<=state['wage_budget'];progress=format(state['annual_payroll'],',')+' / '+format(state['wage_budget'],',')+'원'
            elif key=='winrate':pending=not played;met=rate>=goal['target'];progress=str(rate)+'% · '+str(played)+'경기'
            else:pending=len(recent)<5;met=wins>=goal['target'];progress=str(len(recent))+'경기 중 '+str(wins)+'승'
            out.append(dict(goal,status='경기 기록 대기' if pending else '현재 충족' if met else '개선 필요',progress=progress,met=met,deadline=str(season)+'시즌 종료'))
        goals[audience]=out
    history=[dict(zip(('season','week','board_delta','fan_delta','reason'),r)) for r in db.execute('SELECT season,week,board_delta,fan_delta,reason FROM sentiment_events WHERE career_id=? ORDER BY season DESC,week DESC,rowid DESC LIMIT 30',(career,))]
    def mood(value):return '매우 긍정적' if value>=80 else '지지' if value>=60 else '관망' if value>=40 else '불만' if value>=20 else '위기'
    return dict(goals=goals,board=state['board'],fans=state['fans'],board_mood=mood(state['board']),fan_mood=mood(state['fans']),history=history,season=season,week=week)
