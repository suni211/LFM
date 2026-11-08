"""Online transfer offers with agent demands, seller consent and atomic settlement."""
import json
import catalog
import clubs
import recruitment
import management
import club_messages
import staffing

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS person_ownership(
        person_id TEXT PRIMARY KEY,career_id INTEGER REFERENCES careers(id),club_key TEXT);
        CREATE TABLE IF NOT EXISTS transfer_offers(
        id INTEGER PRIMARY KEY,buyer INTEGER NOT NULL REFERENCES careers(id),seller INTEGER REFERENCES careers(id),
        person_id TEXT NOT NULL,annual_salary INTEGER NOT NULL,fee INTEGER NOT NULL,years INTEGER NOT NULL,
        asking_salary INTEGER NOT NULL,asking_fee INTEGER NOT NULL,state TEXT NOT NULL,
        seller_approved INTEGER NOT NULL DEFAULT 0,pitch TEXT NOT NULL,created_turn INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS transfer_events(
        id INTEGER PRIMARY KEY,offer_id INTEGER UNIQUE REFERENCES transfer_offers(id),
        buyer INTEGER NOT NULL,seller INTEGER,person_id TEXT NOT NULL,fee INTEGER NOT NULL,
        season INTEGER NOT NULL,week INTEGER NOT NULL,kind TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS agent_relations(
        career_id INTEGER NOT NULL REFERENCES careers(id),person_id TEXT NOT NULL,trust INTEGER NOT NULL,
        PRIMARY KEY(career_id,person_id));''')

def owner(db,p):
    row=db.execute('SELECT career_id,club_key FROM person_ownership WHERE person_id=?',(p['id'],)).fetchone()
    if row: return (None,None) if row==(None,'free-agent') else row
    roster=db.execute("SELECT career_id FROM club_roster WHERE person_id=? AND assignment!='departed'",(p['id'],)).fetchone()
    generated=db.execute('SELECT career_id,assignment FROM generated_people WHERE id=?',(p['id'],)).fetchone()
    if roster: result=(roster[0],None)
    elif generated: result=(generated[0],None) if generated[1] not in ('candidate','departed') else (None,None)
    else:
        club_key=clubs.key(p.get('league',''),p.get('team',''))
        club=db.execute('SELECT career_id FROM club_profiles WHERE team_key=?',(club_key,)).fetchone()
        result=(club[0] if club else None,club_key)
    db.execute('INSERT INTO person_ownership VALUES(?,?,?)',(p['id'],*result))
    return result

def can_manage(db,user,career):
    import online_world
    if online_world.operator(db,user):return False
    return bool(db.execute("SELECT 1 FROM members WHERE user_id=? AND career_id=? AND role='admin'",(user,career)).fetchone())

def quote(db,buyer,person_id,salary,fee,years,pitch):
    if (not isinstance(person_id,str) or type(salary) is not int or type(fee) is not int or
        not 0<=salary<=10**11 or not 0<=fee<=10**12 or type(years) is not int or years not in (1,2,3) or
        pitch not in ('development','starting','salary')): raise ValueError('invalid transfer offer')
    if not recruitment.view(db,buyer)['complete']: raise ValueError('finalize the five-player lineup before advancing')
    management.ensure(db,buyer)
    person=catalog.detail(db,buyer,person_id)
    prospect=db.execute('SELECT career_id,assignment FROM generated_people WHERE id=?',(person_id,)).fetchone()
    if prospect and prospect[0]!=buyer and not recruitment.view(db,prospect[0])['complete']:
        raise ValueError('prospect is reserved for initial recruitment')
    if person.get('kind') not in ('player','coach','staff') or (person.get('kind')=='player' and person.get('role') not in recruitment.ROLES):
        raise ValueError('classify the registered role before negotiating')
    if person.get('kind')=='player':
        import solo
        solo.require_pro(db,person_id)
    seller,source=owner(db,person)
    if seller==buyer: raise ValueError('person already belongs to this club')
    economics=person.get('economics')
    if not economics:
        import player_economy
        economics=player_economy.profile(db,person)
    base=person.get('salary')
    if type(base) is not int or base<1:
        base=economics['annual_salary'] if economics else (24000000 if person['kind']=='player' else 18000000)
    if seller:
        old=db.execute('SELECT annual_salary FROM club_contracts WHERE career_id=? AND person_id=? AND active=1',(seller,person_id)).fetchone()
        if old: base=old[0]
    profile=management.snapshot(db,buyer)['manager']
    trust_row=db.execute('SELECT trust FROM agent_relations WHERE career_id=? AND person_id=?',(buyer,person_id)).fetchone()
    trust=trust_row[0] if trust_row else 50
    discount=(profile['stats']['협상']-10)*.003+(trust-50)*.001
    ask=max(1,round(base*(1.08-discount-(.03 if pitch=='development' else 0))))
    # Valuations follow the same performance/reputation model used by the
    # player dossier. A genuine unattached FA has no transfer fee.
    asking_fee=max(0,int(economics['market_value'])) if economics and (source or seller) else (
        max(0,base//2) if source or seller else 0)
    if db.execute("SELECT 1 FROM transfer_offers WHERE buyer=? AND person_id=? AND state IN ('quoted','seller_pending','ready')",(buyer,person_id)).fetchone():
        raise ValueError('an offer is already open for this person')
    offer=db.execute('''INSERT INTO transfer_offers(buyer,seller,person_id,annual_salary,fee,years,asking_salary,asking_fee,state,pitch,created_turn)
        VALUES(?,?,?,?,?,?,?,?,?,?,?)''',(buyer,seller,person_id,salary,fee,years,ask,asking_fee,'quoted',pitch,management.turn(db,buyer))).lastrowid
    import rumors
    rumors.contact(db,buyer,person)
    return offer

def offers(db,career):
    names=('id','buyer','seller','person_id','annual_salary','fee','years','asking_salary','asking_fee','state','seller_approved','pitch','created_turn')
    items=[]
    for row in db.execute('SELECT * FROM transfer_offers WHERE buyer=? OR seller=? ORDER BY id DESC LIMIT 150',(career,career)):
        item=dict(zip(names,row));item['person']=catalog.detail(db,career,item['person_id'])
        item['direction']='outgoing' if item['seller']==career else 'incoming'
        items.append(item)
    return items

def respond(db,user,career,offer_id,choice,counter_fee=None):
    if type(offer_id) is not int or not 1<=offer_id<=2**63-1: raise ValueError('invalid offer')
    row=db.execute('SELECT buyer,seller,person_id,annual_salary,fee,years,asking_salary,asking_fee,state,seller_approved,pitch FROM transfer_offers WHERE id=?',(offer_id,)).fetchone()
    if not row: raise ValueError('offer not found')
    buyer,seller,pid,salary,fee,years,ask,asking_fee,state,seller_approved,pitch=row
    if career not in (buyer,seller) or not can_manage(db,user,career): raise PermissionError()
    if state in ('completed','declined','cancelled'): raise ValueError('offer is closed')
    person=catalog.detail(db,buyer,pid)
    import rumors
    if choice=='cancel' and career==buyer:
        db.execute("UPDATE transfer_offers SET state='cancelled' WHERE id=?",(offer_id,))
        rumors.step(db,career,offer_id,choice,person);return
    if choice in ('approve','decline','counter') and career==seller:
        if state!='seller_pending': raise ValueError('seller response is not available')
        if choice=='decline':
            db.execute("UPDATE transfer_offers SET state='declined' WHERE id=?",(offer_id,))
            rumors.step(db,career,offer_id,choice,person);return
        if choice=='counter':
            if type(counter_fee) is not int or not 0<=counter_fee<=10**12: raise ValueError('invalid transfer fee')
            db.execute("UPDATE transfer_offers SET asking_fee=?,seller_approved=1,state='quoted' WHERE id=?",(counter_fee,offer_id))
            rumors.step(db,career,offer_id,choice,person);return
        db.execute("UPDATE transfer_offers SET seller_approved=1,state='ready' WHERE id=?",(offer_id,))
        rumors.step(db,career,offer_id,choice,person);return
    if choice!='accept' or career!=buyer or state not in ('quoted','ready'): raise ValueError('offer acceptance is not available')
    current_owner,_=owner(db,person)
    if current_owner!=seller: raise ValueError('player ownership changed')
    salary=max(salary,ask);fee=max(fee,asking_fee)
    if seller is not None and not seller_approved:
        db.execute("UPDATE transfer_offers SET annual_salary=?,fee=?,state='seller_pending' WHERE id=?",(salary,fee,offer_id))
        now=management.turn(db,buyer)
        club_messages.publish(db,seller,'offer:'+str(offer_id),(now-1)//104+1,(now-1)%104+1,'이적 제안 도착',catalog.display(person)+' 영입 제안이 도착했습니다. 이적 활동에서 수락·거절·역제안을 선택하세요.')
        rumors.step(db,buyer,offer_id,'forward',person)
        return
    state=management.snapshot(db,buyer)
    if fee>state['transfer_budget'] or fee>state['cash']: raise ValueError('insufficient transfer budget')
    if state['annual_payroll']+salary>state['wage_budget']: raise ValueError('wage budget exceeded')
    squad='staff' if person['kind'] in ('coach','staff') else 'reserve'
    if squad=='staff':staffing.enforce(recruitment.view(db,buyer)['staff'],staffing.role(person))
    if seller:
        busy=db.execute("SELECT 1 FROM fixtures WHERE career_id=? AND state='queued'",(seller,)).fetchone()
        if busy: raise ValueError('finish the current series before changing lineup')
        db.execute("UPDATE club_roster SET assignment='departed' WHERE career_id=? AND person_id=?",(seller,pid))
        db.execute("UPDATE generated_people SET assignment='departed' WHERE career_id=? AND id=?",(seller,pid))
        db.execute('UPDATE club_contracts SET active=0 WHERE career_id=? AND person_id=?',(seller,pid))
        management.ensure(db,seller)
        management.ledger(db,seller,'transfer-sale:'+str(offer_id),fee,'transfer','선수·스탭 이적 수입')
    club_name=db.execute('SELECT name FROM careers WHERE id=?',(buyer,)).fetchone()[0]
    game_person=dict(person,team=club_name,assignment=squad)
    own_generated=db.execute('SELECT 1 FROM generated_people WHERE id=? AND career_id=?',(pid,buyer)).fetchone()
    if own_generated and clubs.profile(db,buyer)['mode']!='takeover':
        db.execute('UPDATE generated_people SET assignment=? WHERE id=?',(squad,pid))
    else:
        db.execute("UPDATE generated_people SET assignment='departed' WHERE id=?",(pid,))
        db.execute('''INSERT INTO club_roster VALUES(?,?,?,?,?) ON CONFLICT(career_id,person_id)
            DO UPDATE SET payload=excluded.payload,assignment=excluded.assignment,role=excluded.role''',
            (buyer,pid,json.dumps(game_person,ensure_ascii=False),squad,person.get('role') or 'COACH'))
    db.execute('UPDATE person_ownership SET career_id=?,club_key=NULL WHERE person_id=?',(buyer,pid))
    now=management.turn(db,buyer)
    db.execute('''INSERT INTO club_contracts VALUES(?,?,?,?,1) ON CONFLICT(career_id,person_id)
        DO UPDATE SET annual_salary=excluded.annual_salary,end_turn=excluded.end_turn,active=1''',(buyer,pid,salary,now+years*104-1))
    db.execute('INSERT INTO contract_signings VALUES(?,?,?) ON CONFLICT(career_id,person_id) DO UPDATE SET start_turn=excluded.start_turn',(buyer,pid,now))
    db.execute('INSERT OR IGNORE INTO club_health(career_id,person_id) VALUES(?,?)',(buyer,pid))
    management.ledger(db,buyer,'transfer-buy:'+str(offer_id),-fee,'transfer','선수·스탭 영입 이적료')
    db.execute('UPDATE club_finances SET transfer_budget=MAX(0,MIN(?,cash)) WHERE career_id=?',(state['transfer_budget']-fee,buyer))
    db.execute("UPDATE transfer_offers SET state='completed',annual_salary=?,fee=? WHERE id=?",(salary,fee,offer_id))
    db.execute('INSERT INTO transfer_events(offer_id,buyer,seller,person_id,fee,season,week,kind) VALUES(?,?,?,?,?,?,?,?)',
               (offer_id,buyer,seller,pid,fee,(now-1)//104+1,(now-1)%104+1,person['kind']))
    db.execute('''INSERT INTO agent_relations VALUES(?,?,55) ON CONFLICT(career_id,person_id) DO UPDATE SET trust=MIN(100,trust+5)''',(buyer,pid))
    import fan_community
    fan_community.transfer(db,buyer,offer_id,person)
    rumors.step(db,buyer,offer_id,'accept',person)
    club_messages.publish(db,buyer,'signed:'+str(offer_id),(now-1)//104+1,(now-1)%104+1,'영입 완료',catalog.display(person)+' 영입과 게임용 계약이 확정됐습니다. 선수단 배치에서 선발·후보·유소년을 지정하세요.')

def activity(db,kind=''):
    if kind not in ('','player','coach','staff'): raise ValueError('invalid transfer kind')
    rows=db.execute('''SELECT e.id,e.buyer,e.seller,e.person_id,e.fee,e.season,e.week,e.kind,b.name,s.name
        FROM transfer_events e JOIN careers b ON b.id=e.buyer LEFT JOIN careers s ON s.id=e.seller
        WHERE (?='' OR e.kind=? OR ?='staff' AND e.kind='coach') ORDER BY e.id DESC LIMIT 150''',(kind,kind,kind))
    return [dict(zip(('id','buyer','seller','person_id','fee','season','week','kind','buyer_name','seller_name'),row)) for row in rows]
