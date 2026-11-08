"""User-defined staff positions and quotas, applied to selection and recruitment."""
ROLES={
    'GM':dict(name='단장',limit=1),
    'HEAD_COACH':dict(name='수석 코치',limit=1),
    'COACH':dict(name='코치',limit=2),
    'COMMUNITY':dict(name='커뮤니티 담당',limit=3),
    'ANALYST':dict(name='데이터분석',limit=3),
    'DOCTOR':dict(name='팀 닥터',limit=5),
}

def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS staff_positions(
        career_id INTEGER NOT NULL REFERENCES careers(id),person_id TEXT NOT NULL,
        role TEXT NOT NULL,PRIMARY KEY(career_id,person_id))''')
    db.execute('CREATE TABLE IF NOT EXISTS staff_candidate_batches(career_id INTEGER PRIMARY KEY REFERENCES careers(id))')

def role(person):
    assigned=person.get('staff_role')
    if assigned in ROLES:return assigned
    raw=str(person.get('raw_role') or '').casefold()
    if 'general manager' in raw or '단장' in raw:return 'GM'
    if 'head coach' in raw or '수석' in raw:return 'HEAD_COACH'
    if 'analyst' in raw or '분석' in raw:return 'ANALYST'
    if 'doctor' in raw or 'physio' in raw or '닥터' in raw:return 'DOCTOR'
    if 'community' in raw or 'social' in raw or '커뮤니티' in raw:return 'COMMUNITY'
    return 'COACH'

def annotate(db,career,people):
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='staff_positions'").fetchone():
        overrides=dict(db.execute('SELECT person_id,role FROM staff_positions WHERE career_id=?',(career,)))
    else:overrides={}
    for person in people:
        if person.get('kind') in ('coach','staff') or person.get('assignment')=='staff':
            person['staff_role']=overrides.get(person['id'],role(person))
            person['staff_role_name']=ROLES[person['staff_role']]['name']
    return people

def enforce(staff,new_role,person_id=None):
    if new_role not in ROLES:raise ValueError('invalid staff position')
    count=sum(p['id']!=person_id and role(p)==new_role for p in staff)
    if count>=ROLES[new_role]['limit']:raise ValueError('staff position quota exceeded')

def assign(db,career,person_id,new_role):
    import recruitment
    state=recruitment.view(db,career)
    person=next((p for p in state['staff'] if p['id']==person_id),None)
    if person is None:raise ValueError('staff member not found')
    enforce(state['staff'],new_role,person_id)
    db.execute('INSERT INTO staff_positions VALUES(?,?,?) ON CONFLICT(career_id,person_id) DO UPDATE SET role=excluded.role',(career,person_id,new_role))

def summary(people):
    return [dict(role=key,name=value['name'],limit=value['limit'],count=sum(role(p)==key for p in people)) for key,value in ROLES.items()]

def active(db,career,at_turn=None):
    import recruitment
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='club_contracts'").fetchone():return []
    if at_turn is None:
        season,week=db.execute('SELECT season,week FROM careers WHERE id=?',(career,)).fetchone();at_turn=(season-1)*104+week
    ids={row[0] for row in db.execute('SELECT person_id FROM club_contracts WHERE career_id=? AND active=1 AND end_turn>=?',(career,at_turn))}
    return [p for p in recruitment.view(db,career)['staff'] if p['id'] in ids]

def generate_candidates(db,career):
    import secrets,json,uuid,itertools
    import catalog,recruitment,handles
    if db.execute('SELECT 1 FROM staff_candidate_batches WHERE career_id=?',(career,)).fetchone():return
    used_names={p.get('display_name_ko') or p.get('real_name') for p in catalog.load()['people']}
    used_nicks={str(p.get('nickname') or '').casefold() for p in catalog.load()['people']}|recruitment.RETIRED
    for name,nick in db.execute('SELECT real_name,nickname_key FROM generated_people'):used_names.add(name);used_nicks.add(nick)
    names=[''.join(p) for p in itertools.product(('고','남','류','문','백','성','심','양','원','전','차','표','김','이','박','최','정','강','조','윤'),
        ('민','서','도','시','지','예','준','현','하','태','수','건','진','성','재','우','승','정','찬','영'),
        ('준','윤','우','호','빈','혁','성','현','훈','원','민','진','환','겸','찬','율','영','재','수','석')) if ''.join(p) not in used_names]
    if len(names)<40:raise ValueError('unique staff identities exhausted')
    rng=secrets.SystemRandom();names=rng.sample(names,40)
    nicks=[]
    for idx,name in enumerate(names):
        nick=handles.choose('front:'+str(career)+':'+name+':'+str(idx),used_nicks)
        used_nicks.add(nick.casefold())
        nicks.append(nick)
    club,season=db.execute('SELECT name,season FROM careers WHERE id=?',(career,)).fetchone()
    selected_league=db.execute('SELECT league FROM club_profiles WHERE career_id=?',(career,)).fetchone()[0]
    for i in range(40):
        position=('GM','COMMUNITY','ANALYST','DOCTOR')[i//10];pid='generated-'+uuid.uuid4().hex
        salary=rng.randrange(12,31)*100000
        person=dict(id=pid,real_name=names[i],display_name_ko=names[i],display_name=names[i],nickname=nicks[i],
            team=club,league=selected_league,kind='staff',role='STAFF',raw_role=ROLES[position]['name'],staff_role=position,staff_role_name=ROLES[position]['name'],
            real_person=False,nickname_scheme='distinct-en-v1',source='game-generated',source_updated='게임 생성',contract_end='시즌 '+str(season)+' 종료',contract_estimated=True,
            salary=salary,salary_estimated=True,nationality_name_ko='대한민국',game_evaluation=None)
        db.execute('INSERT INTO generated_people(id,real_name,nickname_key,career_id,payload) VALUES(?,?,?,?,?)',(pid,names[i],nicks[i].casefold(),career,json.dumps(person,ensure_ascii=False)))
    db.execute('INSERT INTO staff_candidate_batches VALUES(?)',(career,))
