"""Persistent initial recruitment: 10 prospects per role, 10 coaches, unique identities."""
import itertools
import json
import secrets
import uuid
import catalog
import staffing
import handles

ROLES=('TOP','JUNGLE','MID','ADC','SUPPORT')
RETIRED={'ambition','score','bengi','marin','bang','wolf','mata','madlife','pray','gorilla',
         'uzi','clearlove','mlxg','dandy','dade','imp','pawn','deft','rookie','theshy',
         'faker','doublelift','bjergsen','sneaky','rekkles','xpeke','soaz','yellowstar',
         'diamondprox','alex ich','froggen','toyz','stanley','looper','insec','dyrus','hai'}

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS generated_people(
        id TEXT PRIMARY KEY, real_name TEXT NOT NULL UNIQUE, nickname_key TEXT NOT NULL UNIQUE,
        career_id INTEGER NOT NULL REFERENCES careers(id), payload TEXT NOT NULL,
        assignment TEXT NOT NULL DEFAULT 'candidate');
        CREATE TABLE IF NOT EXISTS recruitment_state(
        career_id INTEGER PRIMARY KEY REFERENCES careers(id), complete INTEGER NOT NULL DEFAULT 0);''')

def generate(db,career,club):
    if db.execute('SELECT 1 FROM recruitment_state WHERE career_id=?',(career,)).fetchone(): return
    rng=secrets.SystemRandom()
    imported=catalog.load()['people']
    used_names={p.get('display_name_ko') or p.get('real_name') for p in imported}
    used_nicks={str(p.get('nickname') or '').casefold() for p in imported}|RETIRED
    for name,nick in db.execute('SELECT real_name,nickname_key FROM generated_people'):
        used_names.add(name);used_nicks.add(nick)
    names=[''.join(parts) for parts in itertools.product(
        ('김','이','박','최','정','강','조','윤','장','임','한','오','서','신','권','황','안','송','유','홍'),
        ('민','서','도','시','지','예','준','현','하','태','수','건','진','성','재','우','승','정','찬','영'),
        ('준','윤','우','호','빈','혁','성','현','훈','원','민','진','환','겸','찬','율','영','재','수','석')) if ''.join(parts) not in used_names]
    if len(names)<60: raise ValueError('unique prospect identities exhausted')
    names=rng.sample(names,60)
    nicks=[]
    for i,name in enumerate(names):
        nick=handles.choose(f'{career}:{name}:{i}', used_nicks)
        used_nicks.add(nick.casefold())
        nicks.append(nick)
    season=db.execute('SELECT season FROM careers WHERE id=?',(career,)).fetchone()[0]
    selected_league=db.execute('SELECT league FROM club_profiles WHERE career_id=?',(career,)).fetchone()[0]
    for index in range(60):
        # Lower-league expansion teams receive mostly raw prospects, with rare gems.
        gem=index<50 and rng.random()<.045
        ratings={key:rng.randint(52,79) if gem else rng.randint(32,66) for key in catalog.ATTRIBUTES}
        overall=round(sum(ratings.values())/len(ratings))
        potential_ovr=min(99,overall+rng.randint(4,18)+(rng.randint(14,25) if rng.random()<.08 else 0))
        salary=round((sum(ratings.values())/6)*24000/10000)*10000
        person_id='generated-'+uuid.uuid4().hex
        coach=index>=50
        person=dict(id=person_id,real_name=names[index],display_name_ko=names[index],display_name=names[index],nickname=nicks[index],nickname_scheme='distinct-en-v1',
                    team=club,league=selected_league,region='KR',nationality_name_ko='대한민국',
                    kind='coach' if coach else 'player',role='COACH' if coach else ROLES[index//10],
                    raw_role='코치' if coach else ROLES[index//10],real_person=False,
                    contract_end='시즌 '+str(season)+' 종료',contract_estimated=True,salary=salary,salary_estimated=True,
                    stats=ratings,potential_ovr=potential_ovr,rare_prospect=gem,form=None,source='solo-queue',source_updated='솔로랭크',
                    game_evaluation=dict(ratings=ratings,form=50,note='솔로랭크를 도는 일반인',origin='solo-queue',year=2026))
        if coach:
            person['staff_role']='HEAD_COACH' if index<54 else 'COACH'
            person['staff_role_name']=staffing.ROLES[person['staff_role']]['name']
        db.execute('INSERT INTO generated_people(id,real_name,nickname_key,career_id,payload) VALUES(?,?,?,?,?)',
                   (person_id,names[index],nicks[index].casefold(),career,json.dumps(person,ensure_ascii=False)))
        if not coach:
            import solo
            solo.ensure(db,person,'pro' if index%10<3 else 'amateur',career,club)
    db.execute('INSERT INTO recruitment_state VALUES(?,0)',(career,))

def view(db,career):
    row=db.execute('SELECT complete FROM recruitment_state WHERE career_id=?',(career,)).fetchone()
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='club_profiles'").fetchone():
        import clubs
        profile=clubs.profile(db,career)
        if profile['mode']=='takeover':
            people=staffing.annotate(db,career,clubs.roster(db,career))
            import solo
            for person in people: solo.attach(db,person)
            return dict(complete=bool(row and row[0]),people=people,mode='takeover',league=profile['league'],
                        roster=[p for p in people if p['assignment']=='first'],staff=[p for p in people if p['assignment']=='staff'],staff_limits=staffing.summary([p for p in people if p['assignment']=='staff']))
    people=[dict(json.loads(raw),assignment=assignment) for raw,assignment in db.execute(
        "SELECT payload,assignment FROM generated_people WHERE career_id=? AND assignment!='departed' ORDER BY real_name",(career,))]
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='club_profiles'").fetchone():
        people+=clubs.roster(db,career)
    people=staffing.annotate(db,career,people)
    import solo
    for person in people: solo.attach(db,person)
    return dict(complete=bool(row and row[0]),people=people,mode='create',league=clubs.profile(db,career)['league'],
                roster=[p for p in people if p['assignment']=='first'],staff=[p for p in people if p['assignment']=='staff'],staff_limits=staffing.summary([p for p in people if p['assignment']=='staff']))

def select(db,career,person_id,enabled):
    if type(enabled) is not bool or not isinstance(person_id,str): raise ValueError('invalid selection')
    state=view(db,career)
    if state['complete']: raise ValueError('initial recruitment already finalized')
    person=next((p for p in state['people'] if p['id']==person_id),None)
    if person is None: raise KeyError(person_id)
    if enabled and person['assignment']=='candidate':
        if person['kind'] in ('coach','staff'):
            staffing.enforce(state['staff'],staffing.role(person))
        elif person['kind']=='player':
            import solo
            if not solo.is_pro(db,person['id']): raise ValueError('debut the prospect before the pro roster')
            if len(state['roster'])>=5 or any(p['role']==person['role'] for p in state['roster']):
                raise ValueError('select exactly one player per role')
    assignment=('staff' if person['kind'] in ('coach','staff') else 'first') if enabled else 'candidate'
    db.execute('UPDATE generated_people SET assignment=? WHERE id=? AND career_id=?',(assignment,person_id,career))

def finalize(db,career):
    state=view(db,career)
    if {p['role'] for p in state['roster']}!=set(ROLES) or len(state['roster'])!=5:
        raise ValueError('five players, one per role, required')
    for position in staffing.summary(state['staff']):
        if position['count']>position['limit']:raise ValueError('staff position quota exceeded')
    db.execute('UPDATE recruitment_state SET complete=1 WHERE career_id=?',(career,))


def repair_generated_handles(db):
    """Migrate in-game generated handles once, without touching real players or IDs."""
    rows=db.execute('SELECT id,payload FROM generated_people ORDER BY id').fetchall()
    generated=[(pid,json.loads(raw)) for pid,raw in rows]
    used={str(p.get('nickname') or '').casefold() for p in catalog.load()['people']}
    # Keep already migrated names, but discard old template names from the collision pool.
    for _,p in generated:
        if p.get('nickname_scheme')=='distinct-en-v1':
            used.add(str(p.get('nickname') or '').casefold())
    for pid,p in generated:
        if p.get('real_person') or p.get('nickname_scheme')=='distinct-en-v1':
            continue
        old=str(p.get('nickname') or '')
        nick=handles.choose(pid,used)
        used.add(nick.casefold())
        p.setdefault('original_nickname',old)
        p.update(nickname=nick,nickname_scheme='distinct-en-v1')
        p.pop('nickname_ko',None)
        db.execute('UPDATE generated_people SET nickname_key=?,payload=? WHERE id=?',
                   (nick.casefold(),json.dumps(p,ensure_ascii=False),pid))
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='solo_ranks'").fetchone():
            db.execute('UPDATE solo_ranks SET nickname=? WHERE person_id=?',(nick,pid))


def repair_initial_pool(db):
    """Restore selectable launch candidates only for untouched, incomplete new clubs."""
    import solo
    for cid, in db.execute("SELECT p.career_id FROM club_profiles p JOIN recruitment_state r ON r.career_id=p.career_id WHERE p.mode='create' AND r.complete=0").fetchall():
        if db.execute("SELECT 1 FROM generated_people WHERE career_id=? AND assignment NOT IN ('candidate','departed')",(cid,)).fetchone():continue
        for role in ROLES:
            candidates=[(pid,json.loads(raw)) for pid,raw in db.execute("SELECT id,payload FROM generated_people WHERE career_id=? AND assignment='candidate'",(cid,)) if json.loads(raw).get('role')==role]
            if any(solo.is_pro(db,pid) for pid,p in candidates):continue
            candidates.sort(key=lambda row:-sum((row[1].get('stats') or {}).values()))
            for pid,p in candidates[:3]:db.execute("UPDATE solo_ranks SET path='pro',mmr=MAX(mmr,2800) WHERE person_id=?",(pid,))
