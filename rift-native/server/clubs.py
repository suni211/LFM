"""Online club ownership and real-team onboarding. No local career authority."""
import hashlib
import json
import catalog
import academy_clubs

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS club_profiles(
        career_id INTEGER PRIMARY KEY REFERENCES careers(id), mode TEXT NOT NULL,
        league TEXT NOT NULL, team_key TEXT UNIQUE, source TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS club_roster(
        career_id INTEGER NOT NULL REFERENCES careers(id),person_id TEXT NOT NULL,
        payload TEXT NOT NULL,assignment TEXT NOT NULL,role TEXT NOT NULL,
        PRIMARY KEY(career_id,person_id));''')

def key(league,team):
    return hashlib.sha256(json.dumps([league,team],ensure_ascii=False).encode()).hexdigest()[:24]

def available(db):
    import promotion
    claimed={row[0] for row in db.execute('SELECT team_key FROM club_profiles WHERE team_key IS NOT NULL')}
    year=db.execute("SELECT season FROM online_clock WHERE id=1").fetchone() if db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='online_clock'").fetchone() else None
    season=year[0] if year else 1
    return [dict(team,team_key=key(team['league'],team['team']),
                 claimed=key(team['league'],team['team']) in claimed)
            for team in catalog.teams()
            if promotion.active(db,team['league'],team['team'],season)]

def human_owner(db,career):
    row=db.execute('''SELECT u.name FROM members m JOIN users u ON u.id=m.user_id
        WHERE m.career_id=? AND m.role='admin'
        AND u.id NOT IN (SELECT user_id FROM league_operators)
        ORDER BY u.id LIMIT 1''',(career,)).fetchone()
    return row[0] if row else None

def directory(db):
    owned={};created=[]
    for cid,name,league,team_key in db.execute('SELECT c.id,c.name,p.league,p.team_key FROM careers c JOIN club_profiles p ON p.career_id=c.id'):
        owner=human_owner(db,cid)
        item=dict(career_id=cid,league=league or '',team=name or '',team_key=team_key or 'career:'+str(cid),claimed=True,
                  kind='user' if owner else 'ai',owner=owner or '')
        if team_key: owned[team_key]=item
        else: created.append(item)
    board=[]
    for team in available(db):
        current=owned.get(team['team_key'])
        board.append(current or dict(team,league=team.get('league') or '',team=team.get('team') or '',career_id=None,kind='ai',owner=''))
    board.extend(created)
    # Keep renamed/relegated owned careers in directory even if their historic
    # immutable team_key does not match the new competition's catalog.
    seen={row['career_id'] for row in board if row.get('career_id') is not None}
    board.extend(item for item in owned.values() if item['career_id'] not in seen)
    board.sort(key=lambda row:(row['league'],row['team']))
    return board

def grant(db,user,career):
    role='viewer' if human_owner(db,career) else 'admin'
    current=db.execute('SELECT role FROM members WHERE career_id=? AND user_id=?',(career,user)).fetchone()
    if current:
        if current[0]=='admin' or role=='viewer': return current[0]
        db.execute("UPDATE members SET role='admin' WHERE career_id=? AND user_id=?",(career,user))
        return 'admin'
    db.execute('INSERT INTO members VALUES(?,?,?)',(career,user,role))
    return role

def create(db,career,mode,team_key=None,league='LCK CL'):
    if mode=='create':
        db.execute('INSERT INTO club_profiles VALUES(?,?,?,?,?)',(career,mode,league,None,'game-created'))
        return
    if mode!='takeover' or not isinstance(team_key,str): raise ValueError('invalid club mode')
    team=next((row for row in available(db) if row['team_key']==team_key),None)
    if not team: raise ValueError('unknown real club')
    if team['claimed']: raise ValueError('club already managed')
    db.execute('INSERT INTO club_profiles VALUES(?,?,?,?,?)',(career,mode,team['league'],team_key,catalog.load().get('source','GCD')))
    occupied=set()
    academy_players=0
    academy_division=team['league'] in ('LCK CL','LDL')
    for raw_person in catalog.load()['people']:
        person=catalog.display_academy_affiliation(raw_person)
        if (person.get('league'),person.get('team'))!=(team['league'],team['team']): continue
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='person_ownership'").fetchone():
            moved=db.execute('SELECT career_id FROM person_ownership WHERE person_id=?',(person['id'],)).fetchone()
            if moved and moved[0] is not None and moved[0]!=career: continue
        role=person.get('role') or ''
        assignment='unclassified'
        if person.get('kind') in ('coach','staff'): assignment='staff'
        elif person.get('kind')=='player':
            if person.get('squad')=='academy' and not academy_division:
                assignment='academy'
                academy_players+=1
            else:
                # 2nd-division starters *are* the academy roster's starters.
                assignment='first' if role in ('TOP','JUNGLE','MID','ADC','SUPPORT') and role not in occupied else 'reserve'
                if assignment=='first': occupied.add(role)
        db.execute('INSERT INTO club_roster VALUES(?,?,?,?,?)',
                   (career,person['id'],json.dumps(person,ensure_ascii=False),assignment,role))
    import recruitment
    if academy_division and len(occupied)<5:
        # A real team with an incomplete imported roster must recruit the
        # remaining roles; candidates are explicitly generated, not fake clubs.
        recruitment.generate(db,career,team['team'])
    else:
        db.execute('INSERT INTO recruitment_state VALUES(?,?)',
                   (career,int(len(occupied)==5 or (academy_players>0 and not occupied))))
    import solo
    solo.claim_club(db,career,team['team'])

def profile(db,career):
    row=db.execute('SELECT mode,league,team_key,source FROM club_profiles WHERE career_id=?',(career,)).fetchone()
    return dict(zip(('mode','league','team_key','source'),row)) if row else dict(mode='create',league='LCK CL',team_key=None,source='legacy-online')

def roster(db,career):
    people=[]
    latest={p['id']:p for p in catalog.load()['people']}
    for raw,assignment,role in db.execute("SELECT payload,assignment,role FROM club_roster WHERE career_id=? AND assignment!='departed' ORDER BY person_id",(career,)):
        saved=json.loads(raw)
        source=dict(saved,**latest.get(saved['id'],{}))
        p=dict(source,assignment=assignment,role=role,game_role_override=role!=(source.get('role') or ''))
        if role=='COACH' and p.get('kind')!='staff': p['kind']='coach'
        elif role in ('TOP','JUNGLE','MID','ADC','SUPPORT'): p['kind']='player'
        people.append(p)
    return people

def refresh_catalog(db):
    """Repair imported empty roles once; retain transfers and user lineup decisions."""
    db.execute('CREATE TABLE IF NOT EXISTS roster_import_revisions(revision TEXT PRIMARY KEY)')
    revision='verified-staff-roster-classification-20261108-v3'
    if db.execute('SELECT 1 FROM roster_import_revisions WHERE revision=?',(revision,)).fetchone(): return
    latest={p['id']:p for p in catalog.load()['people']}
    for cid,pid,raw,assignment,role in db.execute('SELECT career_id,person_id,payload,assignment,role FROM club_roster').fetchall():
        p=latest.get(pid)
        if not p: continue
        if assignment=='unclassified' and not role and p.get('kind')=='player' and p.get('role'):
            role=p['role']
            occupied=db.execute("SELECT 1 FROM club_roster WHERE career_id=? AND role=? AND assignment='first'",(cid,role)).fetchone()
            assignment='academy' if p.get('squad')=='academy' else 'reserve' if p.get('squad')=='reserve' or occupied else 'first'
        if assignment=='unclassified' and p.get('kind') in ('coach','staff'):
            # All verified front-office personnel belong to staff, never first team.
            assignment,role='staff','COACH'
        if assignment=='unclassified' and p.get('kind')=='player' and p.get('squad') in ('reserve','academy'):
            # Imported "Sub" people with unknown roles are still reserve players.
            assignment=p['squad']
        if assignment=='staff' and p.get('kind') in ('coach','staff') and role=='':
            role='COACH'
        db.execute('UPDATE club_roster SET payload=?,assignment=?,role=? WHERE career_id=? AND person_id=?',
                   (json.dumps(dict(json.loads(raw),**p),ensure_ascii=False),assignment,role,cid,pid))
    for cid, in db.execute("SELECT career_id FROM club_profiles WHERE mode='takeover'").fetchall():
        roles=[r[0] for r in db.execute("SELECT role FROM club_roster WHERE career_id=? AND assignment='first'",(cid,))]
        if len(roles)==5 and set(roles)=={'TOP','JUNGLE','MID','ADC','SUPPORT'}:
            db.execute('UPDATE recruitment_state SET complete=1 WHERE career_id=?',(cid,))
    db.execute('INSERT INTO roster_import_revisions VALUES(?)',(revision,))

def assign(db,career,person_id,assignment,role):
    if assignment not in ('first','reserve','academy','staff','unclassified') or role not in ('TOP','JUNGLE','MID','ADC','SUPPORT','COACH',''):
        raise ValueError('invalid lineup assignment')
    if assignment=='first' and role not in ('TOP','JUNGLE','MID','ADC','SUPPORT'): raise ValueError('invalid player role')
    if assignment=='staff' and role!='COACH': raise ValueError('invalid coach role')
    row=db.execute("SELECT 1 FROM club_roster WHERE career_id=? AND person_id=? AND assignment!='departed'",(career,person_id)).fetchone()
    generated=db.execute("SELECT 1 FROM generated_people WHERE career_id=? AND id=? AND assignment NOT IN ('candidate','departed')",(career,person_id)).fetchone()
    if row is None and generated is None: raise ValueError('person is not registered to this club')
    if assignment=='staff':
        import staffing,recruitment
        state=recruitment.view(db,career)
        person=next(p for p in state['people'] if p['id']==person_id)
        staffing.enforce(state['staff'],staffing.role(person),person_id)
    if assignment in ('first','reserve') and role in ('TOP','JUNGLE','MID','ADC','SUPPORT'):
        import solo
        solo.require_pro(db,person_id)
    if assignment=='first':
        db.execute("UPDATE club_roster SET assignment='reserve' WHERE career_id=? AND role=? AND assignment='first' AND person_id!=?",(career,role,person_id))
        for pid,raw in db.execute("SELECT id,payload FROM generated_people WHERE career_id=? AND assignment='first' AND id!=?",(career,person_id)).fetchall():
            if json.loads(raw)['role']==role: db.execute("UPDATE generated_people SET assignment='reserve' WHERE id=?",(pid,))
    if row: db.execute('UPDATE club_roster SET assignment=?,role=? WHERE career_id=? AND person_id=?',(assignment,role,career,person_id))
    if generated:
        raw=json.loads(db.execute('SELECT payload FROM generated_people WHERE id=?',(person_id,)).fetchone()[0]);raw['role']=role
        db.execute('UPDATE generated_people SET assignment=?,payload=? WHERE id=?',(assignment,json.dumps(raw,ensure_ascii=False),person_id))
