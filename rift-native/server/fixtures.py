"""Durable fixtures. Week changes enqueue only explicitly scheduled games."""
import json
import secrets
import time
import series_state

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS fixtures(
        id INTEGER PRIMARY KEY, career_id INTEGER NOT NULL REFERENCES careers(id),
        season INTEGER NOT NULL, week INTEGER NOT NULL CHECK(week BETWEEN 1 AND 104),
        opponent TEXT NOT NULL, seed INTEGER NOT NULL,
        state TEXT NOT NULL DEFAULT 'scheduled', result TEXT,
        UNIQUE(career_id,season,week))""")
    series_state.init(db)
    columns={row[1] for row in db.execute('PRAGMA table_info(fixtures)')}
    if 'best_of' not in columns:
        db.execute('ALTER TABLE fixtures ADD COLUMN best_of INTEGER NOT NULL DEFAULT 3 CHECK(best_of IN (3,5))')
    if 'competition' not in columns:
        db.execute("ALTER TABLE fixtures ADD COLUMN competition TEXT NOT NULL DEFAULT 'practice'")
    if 'stage' not in columns:
        db.execute("ALTER TABLE fixtures ADD COLUMN stage TEXT NOT NULL DEFAULT 'practice'")

def add(db, career_id, season, week, opponent, best_of=3, competition='practice', stage='practice'):
    if type(best_of) is not int or best_of not in (3,5):
        raise ValueError('unsupported series format')
    if season < 1 or not 1 <= week <= 104 or not 1 <= len(opponent.strip()) <= 40:
        raise ValueError('invalid fixture')
    db.execute('BEGIN IMMEDIATE')
    try:
        current = db.execute('SELECT season,week FROM careers WHERE id=?',(career_id,)).fetchone()
        if not current or (season,week) <= tuple(current):
            raise ValueError('fixture must be in a future week')
        fixture = db.execute(
            'INSERT INTO fixtures(career_id,season,week,opponent,seed,best_of,competition,stage) VALUES(?,?,?,?,?,?,?,?)',
            (career_id,season,week,opponent.strip(),secrets.randbits(31),best_of,competition,stage)).lastrowid
        db.execute('COMMIT')
        return fixture
    except BaseException:
        db.execute('ROLLBACK')
        raise

def reciprocal(db, fixture):
    """One simulated result for a pair of managed teams, not two games."""
    game=db.execute("""SELECT f.season,f.week,c.name,f.opponent,p.league FROM fixtures f
        JOIN careers c ON c.id=f.career_id
        JOIN club_profiles p ON p.career_id=c.id WHERE f.id=?""",(fixture,)).fetchone()
    if not game: return None
    season,week,home,opponent,league=game
    return db.execute("""SELECT f.id,f.career_id,f.state FROM fixtures f
        JOIN careers c ON c.id=f.career_id
        JOIN club_profiles p ON p.career_id=c.id
        WHERE f.id!=? AND f.season=? AND f.week=?
        AND c.name=? AND f.opponent=? AND p.league=?
        ORDER BY f.id LIMIT 1""",
        (fixture,season,week,opponent,home,league)).fetchone()


def enqueue(db, career_id, season, week):
    rows = db.execute("""SELECT id,seed,best_of FROM fixtures
        WHERE career_id=? AND season=? AND week=? AND state='scheduled'""",
        (career_id,season,week)).fetchall()
    for fixture,seed,best_of in rows:
        pair=reciprocal(db,fixture)
        if pair and pair[0]<fixture:
            # The earlier fixture is authoritative; the mirror receives its result.
            continue
        db.execute("UPDATE fixtures SET state='queued' WHERE id=?",(fixture,))
        series_state.start(db,fixture,seed,best_of)

def list_for_member(db, user_id, career_id):
    if not db.execute('SELECT 1 FROM members WHERE user_id=? AND career_id=?',
                      (user_id,career_id)).fetchone():
        return None
    rows = db.execute("""SELECT f.id,f.season,f.week,f.opponent,f.state,f.result,s.state,f.seed,f.best_of,f.competition,f.stage FROM fixtures f
        LEFT JOIN match_series s ON s.fixture_id=f.id
        WHERE f.career_id=? ORDER BY f.season DESC,f.week DESC LIMIT 104""",(career_id,))
    games = []
    now = time.time()
    for fixture,season,week,opponent,state,result,raw,seed,best_of,competition,stage in rows:
        series = json.loads(raw) if raw else None
        if series and series['phase']=='feedback' and now >= series['feedback_until']:
            series_state.next_choice(series,seed)
        games.append(dict(id=fixture,season=season,week=week,opponent=opponent,state=state,
                          result=json.loads(result) if result else None,series=series,
                          best_of=best_of,competition=competition,stage=stage))
    return games

def next_job(db):
    # The worker runs under an exclusive process lock. A killed worker leaves the job queued.
    return db.execute("""SELECT id,seed FROM fixtures WHERE state='queued'
        ORDER BY id LIMIT 1""").fetchone()

def complete(db, fixture, result):
    changed=db.execute("UPDATE fixtures SET state='finished',result=? WHERE id=? AND state='queued'",
               (json.dumps(result,ensure_ascii=False),fixture))
    if changed.rowcount:
        import management
        row=db.execute('SELECT career_id FROM fixtures WHERE id=?',(fixture,)).fetchone()
        management.record_match(db,row[0],fixture,result)
        pair=reciprocal(db,fixture)
        if pair and pair[2]=='scheduled':
            mirrored=dict(result)
            if result.get('winner') in (0,1):
                mirrored['winner']=1-result['winner']
            if isinstance(result.get('score'),list) and len(result['score'])==2:
                mirrored['score']=list(reversed(result['score']))
            updated=db.execute("UPDATE fixtures SET state='finished',result=? WHERE id=? AND state='scheduled'",
                (json.dumps(mirrored,ensure_ascii=False),pair[0]))
            if updated.rowcount:
                management.record_match(db,pair[1],pair[0],mirrored)
        import solo
        solo.record_result(db,result)
        import qualification
        qualification.observe(db,fixture,result)
        meta=db.execute("SELECT season,competition,stage FROM fixtures WHERE id=?",(fixture,)).fetchone()
        if meta and meta[1].casefold() in ('worlds','world championship','월즈','롤드컵') and meta[2].casefold().replace(' ','_') in ('final','finals','grand_final','grand_finals','결승'):
            import season_awards
            season_awards.record_worlds_final(db,meta[0])
    return bool(changed.rowcount)
