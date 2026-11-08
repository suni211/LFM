"""AI player acquisitions favor expected game sporting gains and merchandise.

Only AI-owned or unclaimed NPC sources can be transferred without an offer;
existing human-club player contracts are protected from unilateral transfers.
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

def source_club(db,person,buyer):
    """Transferable source: true FA or AI-managed/unclaimed NPC club only.

    Player contracts on human-managed clubs cannot be bought by AI silently.
    """
    row=db.execute("SELECT career_id,club_key FROM person_ownership WHERE person_id=?",
                   (person['id'],)).fetchone()
    if row:
        if row==(None,'free-agent'):return dict(kind='free-agent',seller=None)
        seller,club_key=row
        if seller is not None:
            if seller==buyer or clubs.human_owner(db,seller):return None
            return dict(kind='npc-club',seller=seller)
        if not club_key or club_key=='free-agent':return dict(kind='free-agent',seller=None)
        found=db.execute("SELECT career_id FROM club_profiles WHERE team_key=?",
                         (club_key,)).fetchone()
        if found:
            if found[0]==buyer or clubs.human_owner(db,found[0]):return None
            return dict(kind='npc-club',seller=found[0])
        return dict(kind='npc-club',seller=None)
    current=person.get('team') or ''
    if not current or current.casefold() in ('fa','free agent','무소속'):
        return dict(kind='free-agent',seller=None)
    source_key=clubs.key(person.get('league',''),current)
    owner=db.execute("SELECT career_id FROM club_profiles WHERE team_key=?",
                     (source_key,)).fetchone()
    if owner:
        if owner[0]==buyer or clubs.human_owner(db,owner[0]):return None
        return dict(kind='npc-club',seller=owner[0])
    return dict(kind='npc-club',seller=None)


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
    belonging={q['id'] for q in state}
    budget=db.execute("SELECT transfer_budget FROM club_finances WHERE career_id=?",(cid,)).fetchone()[0]
    for p in market:
        role=p.get('role')
        if role not in positions or not p.get('real_person'):continue
        if p.get('league') not in (league,'','FA','Free Agent'):continue
        if p['id'] in belonging:continue
        source=source_club(db,p,cid)
        scored=scoring(p,known[role],fans)
        if not scored or scored['playing_benefit']<=0:continue
        fee=0 if source and source['kind']=='free-agent' else int(
            (p.get('economics') or player_economy.estimate(p))['market_value']*.18)
        net=scored['projected_net_value']-fee//2
        affordable=bool(source and cash>=fee+scored['annual_salary']//104
            and budget>=fee and payroll+scored['annual_salary']<=wages)
        if not affordable: continue
        # Hard priority: on-field improvement, then financial headroom,
        # then commercial upside. Popularity cannot trump better performance.
        remaining_budget=budget-fee
        candidates.append((scored['playing_benefit'],remaining_budget,
                           scored['predicted_merch_profit']+scored['reputation']*350000,
                           p['id'],p,scored,source,fee))
    if not candidates:return
    candidates.sort(key=lambda item:(-item[0],-item[1],-item[2],item[3]))
    _,_,_,pid,p,score,source,fee=candidates[0]
    can_sign=True
    signed=False
    if can_sign:
        import solo
        try:
            solo.require_pro(db,pid)
        except (ValueError,KeyError):
            can_sign=0
        else:
            now=(season-1)*150+week
            signed=db.execute("""INSERT OR IGNORE INTO club_roster(
                career_id,person_id,payload,assignment,role) VALUES(?,?,?,?,?)""",
                (cid,pid,json.dumps(dict(p,team=team,league=league),ensure_ascii=False),
                 'reserve',p['role'])).rowcount>0
            if signed:
                seller=source['seller']
                if seller is not None:
                    db.execute("UPDATE club_roster SET assignment='departed' WHERE career_id=? AND person_id=?",
                               (seller,pid))
                    db.execute("UPDATE club_contracts SET active=0 WHERE career_id=? AND person_id=?",
                               (seller,pid))
                db.execute("""INSERT INTO person_ownership(person_id,career_id,club_key)
                    VALUES(?,?,NULL) ON CONFLICT(person_id)
                    DO UPDATE SET career_id=excluded.career_id,club_key=NULL""",(pid,cid))
                db.execute("""INSERT OR IGNORE INTO club_contracts
                    (career_id,person_id,annual_salary,end_turn,active)
                    VALUES(?,?,?,?,1)""",(cid,pid,score['annual_salary'],now+149))
                db.execute("""INSERT OR IGNORE INTO contract_signings VALUES(?,?,?)""",(cid,pid,now))
                db.execute("""INSERT OR IGNORE INTO club_health(career_id,person_id)
                    VALUES(?,?)""",(cid,pid))
                if fee:
                    import management
                    management.ledger(db,cid,'ai-transfer-buy:'+str(season)+':'+str(week)+':'+pid,
                        -fee,'transfer','AI 구단 선수 영입',season,week)
                    db.execute("UPDATE club_finances SET transfer_budget=MAX(0,transfer_budget-?) WHERE career_id=?",
                               (fee,cid))
                    if seller is not None:
                        management.ledger(db,seller,
                            'ai-transfer-sale:'+str(season)+':'+str(week)+':'+pid,
                            fee,'transfer','AI 구단 선수 판매',season,week)
    db.execute("""INSERT INTO ai_transfer_decisions VALUES(?,?,?,?,?,?,?,?,?,?,?,?)""",
        (cid,season,week,pid,p.get('nickname') or p.get('real_name') or pid,
         'signed-free-agent' if signed and source['kind']=='free-agent' else 'signed-ai-transfer' if signed else 'scouting-interest',
         score['predicted_merch_profit'],score['annual_salary'],
         score['player_rating'],score['reputation'],
         score['playing_benefit'],score['projected_net_value']))
    if signed:
        import club_messages
        club_messages.publish(db,cid,'ai-signed:'+pid+':'+str(season)+':'+str(week),
            season,week,'AI 구단 영입',team+'이 '+(p.get('nickname') or pid)+
            ' 선수를 연봉·경기력·굿즈 예상 수익을 비교해 영입했습니다.')

def weekly(db,season,week):
    # Decision-making is a durable monthly event, not repeated per GET.
    if week!=2 and week%4!=1:return
    # Support legacy database snapshots and clock-only integration tests.
    required={'club_finances','club_contracts','person_ownership',
              'ai_transfer_decisions','recruitment_state','club_roster'}
    existing={name for (name,) in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if not required.issubset(existing):return
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
