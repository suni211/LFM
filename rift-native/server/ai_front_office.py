"""AI club transfer decisions favor net playing value and merchandise income.

AI clubs may sign independently documented free agents, never hijack a
player under contract to a human or another club. Interest in a contracted
player is a scouting observation, not a completed transfer.
"""
import json
import math
import player_economy
import catalog
import clubs

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS ai_transfer_decisions(
        career_id INTEGER NOT NULL,season INTEGER NOT NULL,
        week INTEGER NOT NULL,player_id TEXT NOT NULL,
        player_name TEXT NOT NULL,decision TEXT NOT NULL,
        predicted_merch_profit INTEGER NOT NULL,
        annual_salary INTEGER NOT NULL,
        player_rating INTEGER NOT NULL,
        reputation INTEGER NOT NULL,
        playing_benefit INTEGER NOT NULL,
        projected_net_value INTEGER NOT NULL,
        PRIMARY KEY(career_id,season,week))""")

def scoring(person,current_ability,fan_interest=50):
    """Annual game KRW net benefit model; all terms are explicit."""
    ev=person.get('economics') or player_economy.estimate(person)
    if not ev or person.get('kind')!='player':return None
    # A role gap of at most 15 pts can improve simulated results.
    role_gain=max(-25,min(25,ev['rating']-current_ability))
    sporting=int(role_gain*1800000)
    merchandising=int(ev['merch_annual_profit']*max(.4,min(2,fan_interest/70)))
    brand=int(ev['fame']*350000)
    salary=ev['annual_salary']
    net=sporting+merchandising+brand-salary
    return dict(player_rating=ev['rating'],reputation=ev['fame'],
                annual_salary=salary,playing_benefit=sporting,
                predicted_merch_profit=merchandising,
                projected_net_value=net)

def is_unattached(db,person):
    """Only explicit free agents are directly signable by AI."""
    person_id=person['id']
    marked=db.execute("""SELECT career_id,club_key FROM person_ownership
       WHERE person_id=?""",(person_id,)).fetchone()
    if marked:
        if marked!=(None,'free-agent'):return False
    elif (person.get('team') or '').strip().casefold() not in ('','fa','free agent','무소속'):
        return False
    if db.execute("""SELECT 1 FROM club_roster WHERE person_id=? AND
        assignment NOT IN ('departed')""",(person_id,)).fetchone():return False
    if db.execute("""SELECT 1 FROM generated_people WHERE id=?
        AND assignment NOT IN ('departed')""",(person_id,)).fetchone():return False
    return True

def _choose(db,cid,season,week,market):
    if db.execute("SELECT 1 FROM ai_transfer_decisions WHERE career_id=? AND season=? AND week=?",
                  (cid,season,week)).fetchone():return
    club=db.execute("""SELECT c.name,p.league FROM careers c
       JOIN club_profiles p ON p.career_id=c.id WHERE c.id=?""",(cid,)).fetchone()
    if not club:return
    team,league=club
    import recruitment
    roster=recruitment.view(db,cid)
    state=roster.get('people',[])
    positions=('TOP','JUNGLE','MID','ADC','SUPPORT')
    known={}
    for role in positions:
        existing=[p for p in state if p.get('kind')=='player' and p.get('role')==role
                  and p.get('assignment') in ('first','reserve')]
        ratings=[player_economy.estimate(p)['rating'] for p in existing]
        known[role]=max(ratings) if ratings else 40
    finance=db.execute("""SELECT cash,wage_budget,fans FROM club_finances
       WHERE career_id=?""",(cid,)).fetchone()
    if not finance:return
    cash,wages,fans=finance
    payroll=db.execute("""SELECT COALESCE(SUM(annual_salary),0)
       FROM club_contracts WHERE career_id=? AND active=1""",(cid,)).fetchone()[0]
    candidates=[]
    for p in market:
        role=p.get('role')
        if role not in positions:continue
        if p.get('league') not in (league,'','FA','Free Agent'):
            continue
        # Players already in this squad are not external transfer targets.
        if any(q.get('id')==p['id'] for q in state):continue
        scored=scoring(p,known[role],fans)
        if not scored:continue
        if scored['projected_net_value']<=0:continue
        free=is_unattached(db,p)
        can_afford=free and cash>=scored['annual_salary']//104 and (
            payroll+scored['annual_salary']<=wages)
        candidates.append((scored['projected_net_value'],
                           int(can_afford),p['id'],p,scored))
    if not candidates:return
    candidates.sort(key=lambda item:(-item[1],-item[0],item[2]))
    _,can_sign,pid,p,score=candidates[0]
    signed=False
    if can_sign:
        # An ordinary AI career is allowed to hire a genuinely free player.
        import solo
        try:
            solo.require_pro(db,pid)
        except (ValueError,KeyError):
            can_sign=0
        else:
            now=(season-1)*104+week
            signed=db.execute("""INSERT OR IGNORE INTO club_roster(
                career_id,person_id,payload,assignment,role) VALUES(?,?,?,?,?)""",
                (cid,pid,json.dumps(dict(p,team=team,league=league),ensure_ascii=False),
                 'reserve',p['role'])).rowcount>0
            if signed:
                db.execute("""INSERT INTO person_ownership(person_id,career_id,club_key)
                    VALUES(?,?,NULL) ON CONFLICT(person_id)
                    DO UPDATE SET career_id=excluded.career_id,club_key=NULL""",(pid,cid))
                db.execute("""INSERT OR IGNORE INTO club_contracts
                    (career_id,person_id,annual_salary,end_turn,active)
                    VALUES(?,?,?,?,1)""",(cid,pid,score['annual_salary'],now+103))
                db.execute("""INSERT OR IGNORE INTO contract_signings VALUES(?,?,?)""",(cid,pid,now))
                db.execute("""INSERT OR IGNORE INTO club_health(career_id,person_id)
                    VALUES(?,?)""",(cid,pid))
    db.execute("""INSERT INTO ai_transfer_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (cid,season,week,pid,p.get('nickname') or p.get('real_name') or pid,
         'signed-free-agent' if signed else 'scouting-interest',
         score['predicted_merch_profit'],score['annual_salary'],
         score['player_rating'],score['reputation'],
         score['playing_benefit'],score['projected_net_value']))
    if signed:
        import club_messages
        club_messages.publish(db,cid,'ai-signed:'+pid+':'+str(season)+':'+str(week),
            season,week,'AI 구단 FA 영입',team+'이 '+(p.get('nickname') or pid)+
            ' 선수를 연봉·경기력·굿즈 예상 수익을 비교해 영입했습니다.')

def weekly(db,season,week):
    # Decision-making is a durable monthly event, not repeated per GET.
    if week!=2 and week%4!=1:return
    import management
    market=[p for p in catalog.load()['people'] if p.get('kind')=='player']
    for (cid,) in db.execute('SELECT id FROM careers ORDER BY id').fetchall():
        if clubs.human_owner(db,cid):continue
        management.ensure(db,cid)
        _choose(db,cid,season,week,market)

def report(db,league='',limit=80):
    sql="""SELECT d.season,d.week,c.name,p.league,d.player_id,d.player_name,
        d.decision,d.predicted_merch_profit,d.annual_salary,d.player_rating,
        d.reputation,d.playing_benefit,d.projected_net_value
        FROM ai_transfer_decisions d JOIN careers c ON c.id=d.career_id
        JOIN club_profiles p ON p.career_id=c.id"""
    if league:
        sql+=' WHERE p.league=?'
        args=(league,limit)
    else:args=(limit,)
    sql+=' ORDER BY d.season DESC,d.week DESC,d.projected_net_value DESC LIMIT ?'
    keys=('season','week','club','league','person_id','player',
          'decision','merch_profit','salary','rating','fame','sporting','net')
    return [dict(zip(keys,row)) for row in db.execute(sql,args)]
