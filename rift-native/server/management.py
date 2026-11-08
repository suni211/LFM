"""Authoritative club finances, contracts, training, recovery and board progression.

All monetary values and gameplay forecasts are game estimates, not real disclosures.
Mutations run inside the caller's BEGIN IMMEDIATE transaction.
"""
import hashlib
import json
import random
from datetime import date
import catalog
import club_messages
import recruitment
import clubs
import staffing
import club_vision
import season_structure

def init(db):
    club_vision.init(db)
    db.executescript('''CREATE TABLE IF NOT EXISTS club_finances(
        career_id INTEGER PRIMARY KEY REFERENCES careers(id),cash INTEGER NOT NULL,
        transfer_budget INTEGER NOT NULL,wage_budget INTEGER NOT NULL,
        board INTEGER NOT NULL DEFAULT 60,fans INTEGER NOT NULL DEFAULT 50);
        CREATE TABLE IF NOT EXISTS club_contracts(
        career_id INTEGER NOT NULL REFERENCES careers(id),person_id TEXT NOT NULL,
        annual_salary INTEGER NOT NULL CHECK(annual_salary>=0),end_turn INTEGER NOT NULL,
        active INTEGER NOT NULL DEFAULT 1,PRIMARY KEY(career_id,person_id));
        CREATE TABLE IF NOT EXISTS club_health(
        career_id INTEGER NOT NULL REFERENCES careers(id),person_id TEXT NOT NULL,
        fatigue INTEGER NOT NULL DEFAULT 0,injury_until INTEGER NOT NULL DEFAULT 0,
        treatment TEXT NOT NULL DEFAULT 'normal',morale INTEGER NOT NULL DEFAULT 60,
        growth TEXT NOT NULL DEFAULT '{}',PRIMARY KEY(career_id,person_id));
        CREATE TABLE IF NOT EXISTS finance_ledger(
        id INTEGER PRIMARY KEY,career_id INTEGER NOT NULL REFERENCES careers(id),
        event_key TEXT NOT NULL,season INTEGER NOT NULL,week INTEGER NOT NULL,
        amount INTEGER NOT NULL,category TEXT NOT NULL,description TEXT NOT NULL,
        UNIQUE(career_id,event_key));
        CREATE TABLE IF NOT EXISTS management_turns(
        career_id INTEGER NOT NULL REFERENCES careers(id),turn INTEGER NOT NULL,
        PRIMARY KEY(career_id,turn));
        CREATE TABLE IF NOT EXISTS manager_profiles(
        career_id INTEGER PRIMARY KEY REFERENCES careers(id),name TEXT NOT NULL,
        stats TEXT NOT NULL,vision TEXT NOT NULL DEFAULT 'development');
        CREATE TABLE IF NOT EXISTS club_relationships(
        career_id INTEGER NOT NULL REFERENCES careers(id),first_id TEXT NOT NULL,second_id TEXT NOT NULL,
        trust INTEGER NOT NULL DEFAULT 50,last_mediation INTEGER NOT NULL DEFAULT -1,
        PRIMARY KEY(career_id,first_id,second_id));''')
    db.execute('CREATE TABLE IF NOT EXISTS contract_signings(career_id INTEGER NOT NULL,person_id TEXT NOT NULL,start_turn INTEGER NOT NULL,PRIMARY KEY(career_id,person_id))')
    columns={row[1] for row in db.execute('PRAGMA table_info(club_health)')}
    if 'rehab_used' not in columns: db.execute('ALTER TABLE club_health ADD COLUMN rehab_used INTEGER NOT NULL DEFAULT 0')

def turn(db,career):
    season,week=db.execute('SELECT season,week FROM careers WHERE id=?',(career,)).fetchone()
    return season_structure.absolute_turn(season,week)

def renewal_eligible(season, week, end_turn, active=True, kind='player'):
    """Only an active player's expiring-season stove league permits renewal."""
    if not active or kind != 'player' or type(end_turn) is not int or end_turn < 1:
        return False
    expiry_season, _ = season_structure.decode_turn(end_turn)
    return (expiry_season == season and
            (1 <= week <= 10 or 145 <= week <= 150) and
            season_structure.absolute_turn(season, week) <= end_turn)


def ensure(db,career):
    actual=clubs.profile(db,career)['mode']=='takeover'
    db.execute('INSERT OR IGNORE INTO club_finances(career_id,cash,transfer_budget,wage_budget) VALUES(?,?,?,?)',
               (career,500000000 if actual else 30000000,50000000 if actual else 10000000,300000000 if actual else 24000000))
    manager=db.execute('''SELECT u.name FROM users u JOIN members m ON m.user_id=u.id
        WHERE m.career_id=? AND m.role='admin' ORDER BY u.id LIMIT 1''',(career,)).fetchone()
    db.execute('INSERT OR IGNORE INTO manager_profiles(career_id,name,stats) VALUES(?,?,?)',
               (career,manager[0] if manager else '감독',json.dumps(dict.fromkeys(('전술','훈련','협상','동기부여','선수관리','스카우팅'),10),ensure_ascii=False)))
    state=recruitment.view(db,career)
    if not state['complete']: return
    selected=[p for p in state['people'] if p['assignment'] not in ('candidate','unclassified')]
    now=turn(db,career)
    for p in selected:
        salary=p.get('salary')
        if type(salary) is not int or salary<1:
            import player_economy
            estimate=p.get('economics') or player_economy.estimate(p)
            salary=estimate['annual_salary'] if estimate else 18000000
        end=now+149
        if p.get('real_person') and not p.get('contract_estimated'):
            try: end=max(now,(date.fromisoformat(p['contract_end']).year-2026+1)*150)
            except (TypeError,ValueError,KeyError): pass
        added=db.execute('INSERT OR IGNORE INTO club_contracts VALUES(?,?,?,?,1)',(career,p['id'],salary,end))
        if added.rowcount: db.execute('INSERT OR IGNORE INTO contract_signings VALUES(?,?,?)',(career,p['id'],now))
        db.execute('INSERT OR IGNORE INTO club_health(career_id,person_id) VALUES(?,?)',(career,p['id']))
    # Existing signed salaries never change during a deployment. For newly
    # started careers, budget room reflects game-evaluated salaries.
    payroll=db.execute("""SELECT COALESCE(SUM(annual_salary),0) FROM club_contracts
        WHERE career_id=? AND active=1""",(career,)).fetchone()[0]
    db.execute("UPDATE club_finances SET wage_budget=MAX(wage_budget,?) WHERE career_id=?",
        (int(payroll*1.15)+1000000,career))
    ids=sorted(p['id'] for p in selected if p['assignment']=='first')
    for i,first in enumerate(ids):
        for second in ids[i+1:]: db.execute('INSERT OR IGNORE INTO club_relationships(career_id,first_id,second_id) VALUES(?,?,?)',(career,first,second))

def agent_demand(db,career,contract,manager=None):
    """Minimum game wage demand: permits raises and cuts after changing performance."""
    person=contract['person']
    import player_economy
    economy=player_economy.profile(db,person) or {}
    target=int(economy.get('annual_salary') or contract['annual_salary'])
    current=contract['annual_salary']
    morale=contract.get('morale',60)
    manager=manager or {'stats':{'협상':10}}
    trust_row=db.execute('SELECT trust FROM agent_relations WHERE career_id=? AND person_id=?',
                         (career,person['id'])).fetchone()
    trust=trust_row[0] if trust_row else 50
    negotiation=manager['stats'].get('협상',10)
    factor=max(.70,min(1.30,1+(morale-60)*.004+(50-trust)*.002
                         -(negotiation-10)*.005))
    return max(1000000,int(round((target*.70+current*.30)*factor/100000))*100000)

def snapshot(db,career):
    finance=db.execute('SELECT cash,transfer_budget,wage_budget,board,fans FROM club_finances WHERE career_id=?',(career,)).fetchone()
    if not finance: return dict(initialized=False)
    state=dict(zip(('cash','transfer_budget','wage_budget','board','fans'),finance),initialized=True,estimates=True)
    now=turn(db,career)
    season,week=season_structure.decode_turn(now)
    people={p['id']:p for p in recruitment.view(db,career)['people']}
    contracts=[]
    for pid,salary,end,active in db.execute('SELECT person_id,annual_salary,end_turn,active FROM club_contracts WHERE career_id=?',(career,)):
        p=people.get(pid)
        if not p: continue
        health=db.execute('SELECT fatigue,injury_until,treatment,morale,growth FROM club_health WHERE career_id=? AND person_id=?',(career,pid)).fetchone()
        fatigue,injury,treatment,morale,growth=health or (0,0,'normal',60,'{}')
        signed=db.execute('SELECT start_turn FROM contract_signings WHERE career_id=? AND person_id=?',(career,pid)).fetchone()
        contracts.append(dict(start_turn=signed[0] if signed else None,person=p,annual_salary=salary,end_turn=end,remaining_turns=max(0,end-now+1),active=bool(active),
                              renewal_eligible=renewal_eligible(season,week,end,bool(active),p.get('kind')),
                              expiry_season=season_structure.decode_turn(end)[0] if end > 0 else None,
                              fatigue=fatigue,injury_turns=max(0,injury-now),treatment=treatment,morale=morale,growth=json.loads(growth)))
    manager_row=db.execute('SELECT stats FROM manager_profiles WHERE career_id=?',(career,)).fetchone()
    manager_for_agent={'stats':json.loads(manager_row[0])} if manager_row else {'stats':{'협상':10}}
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='agent_relations'").fetchone():
        for contract in contracts:
            contract['agent_asking_salary']=agent_demand(db,career,contract,manager_for_agent)
    state['contracts']=contracts
    state['annual_payroll']=sum(p['annual_salary'] for p in contracts if p['active'])
    import merchandise
    state['merchandise']=merchandise.snapshot(db,career)
    state['ledger']=[dict(zip(('id','season','week','amount','category','description'),row)) for row in db.execute(
        'SELECT id,season,week,amount,category,description FROM finance_ledger WHERE career_id=? ORDER BY id DESC LIMIT 150',(career,))]
    row=db.execute('SELECT name,stats,vision FROM manager_profiles WHERE career_id=?',(career,)).fetchone()
    state['manager']=dict(name=row[0],stats=json.loads(row[1]),vision=row[2])
    state['relationships']=[dict(first=a,second=b,trust=trust,last_mediation=last) for a,b,trust,last in db.execute(
        'SELECT first_id,second_id,trust,last_mediation FROM club_relationships WHERE career_id=? ORDER BY trust,first_id',(career,))]
    state['vision']=club_vision.snapshot(db,career,state)
    state['turn']=now
    state['staff_limits']=staffing.summary(recruitment.view(db,career)['staff'])
    return state

def ledger(db,career,key,amount,category,description,season=None,week=None):
    if season is None: season,week=db.execute('SELECT season,week FROM careers WHERE id=?',(career,)).fetchone()
    result=db.execute('INSERT OR IGNORE INTO finance_ledger(career_id,event_key,season,week,amount,category,description) VALUES(?,?,?,?,?,?,?)',
                      (career,key,season,week,amount,category,description))
    if result.rowcount:
        db.execute('UPDATE club_finances SET cash=cash+?,transfer_budget=MIN(transfer_budget,MAX(0,cash+?)) WHERE career_id=?',(amount,amount,career))
    return bool(result.rowcount)

def action(db,career,data):
    ensure(db,career)
    op=data['action']; now=turn(db,career)
    state=snapshot(db,career)
    if op=='budget':
        transfer,wages=data['transfer_budget'],data['wage_budget']
        if any(type(v) is not int or not 0<=v<=10**12 for v in (transfer,wages)): raise ValueError('invalid budget')
        if transfer>max(0,state['cash']) or wages<state['annual_payroll']: raise ValueError('budget below commitments')
        db.execute('UPDATE club_finances SET transfer_budget=?,wage_budget=? WHERE career_id=?',(transfer,wages,career))
    elif op=='renew':
        pid=data['person']; salary,years=data['annual_salary'],data['years']
        contract=next((p for p in state['contracts'] if p['person']['id']==pid),None)
        if not contract: raise ValueError('contract not found')
        if not contract['renewal_eligible']:
            raise ValueError('계약 만료 시즌의 스토브리그에서만 재계약할 수 있습니다.')
        if type(salary) is not int or type(years) is not int or years not in (1,2,3) or not contract.get('agent_asking_salary',contract['annual_salary'])<=salary<=10**11:
            raise ValueError('salary offer below agent demand')
        if state['annual_payroll']-(contract['annual_salary'] if contract['active'] else 0)+salary>state['wage_budget']: raise ValueError('wage budget exceeded')
        db.execute('UPDATE club_contracts SET annual_salary=?,end_turn=?,active=1 WHERE career_id=? AND person_id=?',(salary,((now-1)//150+1+years)*150,career,pid))
        db.execute('INSERT INTO contract_signings VALUES(?,?,?) ON CONFLICT(career_id,person_id) DO UPDATE SET start_turn=excluded.start_turn',(career,pid,now))
        club_messages.publish(db,career,'renew:'+pid+':'+str(now)+':'+str(max(now,contract['end_turn']+1)),(now-1)//150+1,(now-1)%150+1,'계약 연장',contract['person'].get('display_name',catalog.display(contract['person']))+'의 계약을 '+str(years)+'시즌 연장했습니다.')
    elif op=='treatment':
        pid=data['person']; mode=data['treatment']
        if mode not in ('normal','rest','rehab'): raise ValueError('invalid treatment')
        row=db.execute('SELECT injury_until,treatment,rehab_used FROM club_health WHERE career_id=? AND person_id=?',(career,pid)).fetchone()
        if not row: raise ValueError('person is not registered to this club')
        if mode=='rehab' and row[0]>now and not row[2]:
            doctors=sum(staffing.role(p)=='DOCTOR' for p in staffing.active(db,career))
            cost=250000-25000*doctors
            if state['cash']<cost: raise ValueError('insufficient club cash')
            injury=row[0]
            if ledger(db,career,'rehab:'+pid+':'+str(injury),-cost,'medical','재활 치료 · 게임용 비용'):
                db.execute('UPDATE club_health SET injury_until=MAX(?,injury_until-1),rehab_used=1 WHERE career_id=? AND person_id=?',(now+1,career,pid))
        db.execute('UPDATE club_health SET treatment=? WHERE career_id=? AND person_id=?',(mode,career,pid))
    elif op=='mediate':
        a,b=sorted((data['first'],data['second']))
        row=db.execute('SELECT last_mediation FROM club_relationships WHERE career_id=? AND first_id=? AND second_id=?',(career,a,b)).fetchone()
        if not row: raise ValueError('relationship not found')
        if row[0]==now: raise ValueError('already mediated this turn')
        approach=data['approach']
        if approach not in ('listen','roles','demand'): raise ValueError('invalid mediation')
        change={'listen':6,'roles':4,'demand':-3}[approach]
        db.execute('UPDATE club_relationships SET trust=MIN(100,MAX(0,trust+?)),last_mediation=? WHERE career_id=? AND first_id=? AND second_id=?',(change,now,career,a,b))
        db.execute('UPDATE club_health SET morale=MIN(100,MAX(0,morale+?)) WHERE career_id=? AND person_id IN (?,?)',(2 if approach!='demand' else -2,career,a,b))
    elif op=='manager':
        name,stats=data['name'],data['stats']
        keys={'전술','훈련','협상','동기부여','선수관리','스카우팅'}
        if not isinstance(name,str) or not 1<=len(name.strip())<=30 or not isinstance(stats,dict) or set(stats)!=keys or any(type(v) is not int or not 1<=v<=20 for v in stats.values()) or sum(stats.values())!=60:
            raise ValueError('invalid manager profile')
        db.execute('UPDATE manager_profiles SET name=?,stats=? WHERE career_id=?',(name.strip(),json.dumps(stats,ensure_ascii=False),career))
    elif op=='vision':
        vision=data['vision']
        if vision not in ('development','promotion','stability'): raise ValueError('invalid vision')
        db.execute('UPDATE manager_profiles SET vision=? WHERE career_id=?',(vision,career))
    else: raise ValueError('unknown management action')
    return snapshot(db,career)

def advance(db,career,season,week):
    ensure(db,career)
    now=(season-1)*150+week
    if not db.execute('INSERT OR IGNORE INTO management_turns VALUES(?,?)',(career,now)).rowcount: return
    state=snapshot(db,career)
    training=dict(db.execute('SELECT key,value FROM settings WHERE career_id=?',(career,))).get('training','기본기')
    active_staff=staffing.active(db,career,now)
    staff=sum(staffing.role(p) in ('HEAD_COACH','COACH') for p in active_staff)
    doctors=sum(staffing.role(p)=='DOCTOR' for p in active_staff)
    analysts=sum(staffing.role(p)=='ANALYST' for p in active_staff)
    manager_training=state['manager']['stats'].get('훈련',10)
    payroll=0
    import training as personal
    coach_bonus=staff
    for contract in state['contracts']:
        if not contract['active']: continue
        pid=contract['person']['id']; name=catalog.display(contract['person'])
        if contract['end_turn']<now:
            db.execute('UPDATE club_contracts SET active=0 WHERE career_id=? AND person_id=?',(career,pid))
            club_messages.publish(db,career,'expired:'+pid+':'+str(now),season,week,'계약 만료',name+'의 계약이 만료됐습니다. 재계약 또는 선수단 교체가 필요합니다.')
            continue
        salary=contract['annual_salary'];payroll+=(salary*now)//150-(salary*(now-1))//150
        if contract['person'].get('kind') in ('coach','staff'): continue
        personal.apply_week(db,career,contract['person'],week,coach_bonus)
        fatigue=contract['fatigue']; injured=contract['injury_turns']>1
        recovering=training=='휴식' or contract['treatment'] in ('rest','rehab') or injured
        fatigue=max(0,fatigue-22-staff*2-doctors*2) if recovering else min(100,fatigue+8)
        growth=contract['growth']
        if not recovering and fatigue<80:
            targets={'기본기':('라인전','교전'),'라인 관리':('라인전','운영'),'시야와 합류':('시야','협동')}.get(training,('멘탈',))
            for attribute in targets: growth[attribute]=min(1500,growth.get(attribute,0)+8+staff*2+(analysts*2 if attribute in ('시야','운영') else 0)+(manager_training-10)//3)
        seed=hashlib.sha256(repr((career,now,pid)).encode()).digest()
        rng=random.Random(seed)
        if not injured and fatigue>=70 and rng.random()<(.01+(fatigue-70)*.001):
            until=now+rng.randint(2,4)
            db.execute("UPDATE club_health SET injury_until=?,treatment='normal',rehab_used=0 WHERE career_id=? AND person_id=?",(until,career,pid))
            club_messages.publish(db,career,'injury:'+pid+':'+str(now),season,week,'의료 보고',name+'에게 게임 내 손목 과사용 부상이 발생했습니다. 의료센터에서 회복 계획을 선택하세요.')
        db.execute('UPDATE club_health SET fatigue=?,growth=?,morale=MIN(100,morale+?) WHERE career_id=? AND person_id=?',
                   (fatigue,json.dumps(growth,ensure_ascii=False),1 if recovering else 0,career,pid))
    if payroll:
        ledger(db,career,'payroll:'+str(now),-payroll,'salary','선수·스탭 주간 급여 · 연봉 150턴 분할',season,week)
        club_messages.publish(db,career,'payroll:'+str(now),season,week,'급여 지급',format(payroll,',')+'원을 지급했습니다. 재정 원장에서 확인할 수 있습니다.')
    import merchandise
    merchandise.weekly(db,career,season,week,state['contracts'],state['fans'])
    import player_departures
    player_departures.weekly(db,career,season,week)
    if db.execute('SELECT cash FROM club_finances WHERE career_id=?',(career,)).fetchone()[0]<0:
        club_vision.change(db,career,'negative-cash:'+str(now),-2,0,'현금 잔액 적자로 구단주 신임 하락')

def readiness_details(db,career,at_turn):
    """Diagnose lineup errors without falsely approving missing starters."""
    state=recruitment.view(db,career)
    failures=[]
    if not state['complete']:
        failures.append(dict(person=None,role=None,reason='선수단 등록을 먼저 완료하세요.'))
        return failures
    players=[p for p in state['roster'] if p.get('kind')=='player' and p.get('assignment')=='first']
    for role in recruitment.ROLES:
        occupants=[p for p in players if p.get('role')==role]
        if len(occupants)!=1:
            failures.append(dict(person=None,role=role,reason='주전 '+role+' 포지션에 선수가 '+('없습니다.' if not occupants else '중복 등록되어 있습니다.')))
            continue
        p=occupants[0]
        row=db.execute('''SELECT c.active,c.end_turn,h.injury_until
            FROM club_contracts c LEFT JOIN club_health h
            ON h.career_id=c.career_id AND h.person_id=c.person_id
            WHERE c.career_id=? AND c.person_id=?''',(career,p['id'])).fetchone()
        if not row:
            reason='활성 계약이 없습니다.'
        elif not row[0]:
            reason='계약이 비활성 상태입니다.'
        elif row[1]<at_turn:
            reason='계약이 만료됐습니다.'
        elif row[2] is not None and row[2]>at_turn:
            reason='부상 치료 중입니다.'
        else:
            continue
        failures.append(dict(person=p['id'],nickname=catalog.display(p),role=role,reason=reason))
    return failures


def readiness(db,career,at_turn):
    return [item.get('person') or item.get('role') or 'lineup' for item in
            readiness_details(db,career,at_turn)]


def record_match(db,career,fixture,result):
    ensure(db,career)
    won=result.get('winner')==0
    change=2 if won else -2
    community_staff=sum(staffing.role(p)=='COMMUNITY' for p in staffing.active(db,career))
    fan_change=change*2+community_staff
    club_vision.change(db,career,'match:'+str(fixture),change,fan_change,'경기 '+('승리' if won else '패배')+(' · 커뮤니티 담당 활동 반영' if community_staff else ''))
    db.execute('UPDATE club_health SET fatigue=MIN(100,fatigue+10),morale=MIN(100,MAX(0,morale+?)) WHERE career_id=?',(4 if won else -4,career))
    db.execute('UPDATE club_relationships SET trust=MIN(100,MAX(0,trust+?)) WHERE career_id=?',(1 if won else -1,career))
    season,week,opponent=db.execute('SELECT season,week,opponent FROM fixtures WHERE id=?',(fixture,)).fetchone()
    club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    score=result.get('score',[])
    score_text=':'.join(str(n) for n in score)
    title=club+' '+('승리' if won else '패배')+' · '+opponent+'전 '+score_text
    club_messages.publish(db,career,'result:'+str(fixture),season,week,'경기 결과',title+' · 경기 후 피로, 사기, 관계, 구단주 신임과 팬 지지를 반영했습니다.')
    import fan_community
    fan_community.match(db,career,fixture,result)
    import news
    news.publish(db,career,'result:'+str(fixture),season,week,title,
                 ('게임 속 팬들은 감독의 준비와 선수단의 집중력을 호평했다.' if won else '게임 속 팬들은 경기 운영과 감독의 선수단 관리에 아쉬움을 드러냈다.')+' 이 기사는 게임 내 가상 경기와 반응을 다룹니다.',
                 [dict(kind='team',entity=club),dict(kind='team',entity=opponent)],clubs.profile(db,career)['league'])

