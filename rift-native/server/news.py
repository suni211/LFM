"""Career news preferences and simulation-only editorial stories."""
import json

KINDS = {'team','player','competition'}

def init(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS news_follows(
            user_id INTEGER NOT NULL REFERENCES users(id),
            career_id INTEGER NOT NULL REFERENCES careers(id),
            kind TEXT NOT NULL, entity TEXT NOT NULL,
            PRIMARY KEY(user_id,career_id,kind,entity));
        CREATE TABLE IF NOT EXISTS career_news(
            id INTEGER PRIMARY KEY, career_id INTEGER NOT NULL REFERENCES careers(id),
            event_key TEXT NOT NULL, season INTEGER NOT NULL, week INTEGER NOT NULL,
            headline TEXT NOT NULL, body TEXT NOT NULL, subjects TEXT NOT NULL,
            competition TEXT NOT NULL, origin TEXT NOT NULL DEFAULT 'simulation',
            UNIQUE(career_id,event_key));
    """)

def member(db, user, career):
    return db.execute('SELECT 1 FROM members WHERE user_id=? AND career_id=?',(user,career)).fetchone()

def follow(db, user, career, kind, entity, enabled):
    if kind not in KINDS or not isinstance(entity,str) or not 1<=len(entity.strip())<=120 or type(enabled) is not bool:
        raise ValueError('invalid follow')
    if not member(db,user,career):
        raise PermissionError()
    if enabled:
        db.execute('INSERT OR IGNORE INTO news_follows VALUES(?,?,?,?)',(user,career,kind,entity.strip()))
    else:
        db.execute('DELETE FROM news_follows WHERE user_id=? AND career_id=? AND kind=? AND entity=?',
                   (user,career,kind,entity.strip()))

def preferences(db,user,career):
    if not member(db,user,career):
        raise PermissionError()
    return [dict(kind=kind,entity=entity) for kind,entity in db.execute(
        'SELECT kind,entity FROM news_follows WHERE user_id=? AND career_id=? ORDER BY kind,entity',(user,career))]

def publish(db,career,event_key,season,week,headline,body,subjects,competition):
    db.execute("""INSERT OR IGNORE INTO career_news
        (career_id,event_key,season,week,headline,body,subjects,competition)
        VALUES(?,?,?,?,?,?,?,?)""",
        (career,event_key,season,week,headline,body,json.dumps(subjects,ensure_ascii=False),competition))

def appointment(db,career,manager,club,competition,region,reputation,club_prestige):
    row=db.execute('SELECT season,week FROM careers WHERE id=?',(career,)).fetchone()
    subjects=[dict(kind='team',entity=club)]
    scrutiny=club_prestige>=70 and reputation<30
    if scrutiny:
        headline=f'{club}, {manager} 선임에 의문… “검증된 경력이 먼저”'
        body=f'게임 속 일부 평론가와 팬들이 {manager} 감독의 경험과 구단의 선임 기준을 비판했다. 구단은 시즌 성적으로 평가하겠다는 입장이다.'
        if region=='KR':
            body+=' 온라인 팬 커뮤니티에서는 명문 구단의 기대에 걸맞은 인선인지 논쟁이 확산됐다.'
    else:
        headline=f'{club}, {manager} 감독과 새 시즌 준비'
        body='게임 속 구단은 훈련 체계와 선수단 소통을 우선 과제로 제시했다.'
    publish(db,career,'appointment',*row,headline,body,subjects,competition)

def _item(nid,season,week,headline,body,subjects,league,origin,club,follows,scope,competition):
    entities={(item['kind'],item['entity']) for item in subjects}
    entities.add(('competition',league))
    own=('team',club) in entities
    followed=bool(entities & follows)
    eligible=(own or followed or bool(competition and league==competition)) if scope=='home' else followed if scope=='following' else bool(competition and league==competition)
    if scope=='operator': eligible=True
    if not eligible: return None
    label='스토브 유출' if origin=='leak' and 1<=week<=10 else '유출 기사' if origin=='leak' else '게임 내 가상 기사'
    return dict(id=nid,season=season,week=week,headline=headline,body=body,subjects=subjects,competition=league,
                origin=origin,own_team=own,label=label)

def feed(db,user,career,competition='',scope='home',before=None):
    if scope not in ('home','league','following'):
        raise ValueError('invalid scope')
    import rumors
    rumors.prune(db)
    follows={(item['kind'],item['entity']) for item in preferences(db,user,career)}
    club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    home=db.execute('SELECT league FROM club_profiles WHERE career_id=?',(career,)).fetchone()
    home_league=home[0] if home else ''
    if not competition:competition=home_league
    # In-game league articles are public across clubs; inbox is private.
    query='SELECT id,season,week,headline,body,subjects,competition,origin FROM career_news WHERE (career_id=? OR competition=?)'
    params=[career,competition]
    if before is not None:
        if type(before) is not int or before<1: raise ValueError('invalid cursor')
        query+=' AND id<?'; params.append(before)
    query+=' ORDER BY id DESC'
    selected=[]
    for nid,season,week,headline,body,raw,league,origin in db.execute(query,params):
        item=_item(nid,season,week,headline,body,json.loads(raw),league,origin,club,follows,scope,competition)
        if item: selected.append(item)
        if len(selected)==150: break
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='league_rumors'").fetchone():
        for nid,season,week,headline,body,raw,league in db.execute(
                'SELECT id,season,week,headline,body,subjects,league FROM league_rumors WHERE headline!=\'\' ORDER BY id DESC LIMIT 400'):
            item=_item(10**12+nid,season,week,headline,body,json.loads(raw),league,'leak',club,follows,scope,competition)
            if item: selected.append(item)
    selected.sort(key=lambda item:(-item['season'],-item['week'],-item['id']))
    if scope=='home': selected.sort(key=lambda item:(not item['own_team'],-item['season'],-item['week'],-item['id']))
    return selected[:150]

def operator_feed(db, user, competition='', before=None):
    """All public league and rumour news across every club, without membership."""
    import online_world
    if not online_world.operator(db,user):
        raise PermissionError()
    if not isinstance(competition,str) or len(competition)>80:
        raise ValueError('invalid league')
    if before is not None and (type(before) is not int or before<1):
        raise ValueError('invalid cursor')
    where=[]
    params=[]
    if competition:
        where.append('competition=?')
        params.append(competition)
    if before is not None:
        where.append('id<?')
        params.append(before)
    query='SELECT id,season,week,headline,body,subjects,competition,origin FROM career_news'
    if where: query+=' WHERE '+' AND '.join(where)
    query+=' ORDER BY season DESC,week DESC,id DESC LIMIT 1000'
    rows=db.execute(query,params)
    selected=[]
    for nid,season,week,headline,body,raw,league,origin in rows:
        item=_item(nid,season,week,headline,body,json.loads(raw),league,origin,'',set(),'operator',competition)
        if item: selected.append(item)
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='league_rumors'").fetchone():
        query='SELECT id,season,week,headline,body,subjects,league FROM league_rumors'
        where=[]
        params=[]
        if competition:
            where.append('league=?')
            params.append(competition)
        if before is not None:
            where.append('id<?')
            params.append(before-10**12)
        if where: query+=' WHERE '+' AND '.join(where)
        query+=' ORDER BY season DESC,week DESC,id DESC LIMIT 1000'
        for nid,season,week,headline,body,raw,league in db.execute(query,params):
            if not headline: continue
            item=_item(10**12+nid,season,week,headline,body,json.loads(raw),league,'leak','',set(),'operator',competition)
            if item: selected.append(item)
    selected.sort(key=lambda item:(-item['season'],-item['week'],-item['id']))
    return selected[:150]
