"""One shared online-league clock, with distinct-user majority readiness."""
def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS online_clock(
        id INTEGER PRIMARY KEY CHECK(id=1),season INTEGER NOT NULL,week INTEGER NOT NULL,version INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS league_operators(user_id INTEGER PRIMARY KEY REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS online_ready(user_id INTEGER NOT NULL REFERENCES users(id),
        version INTEGER NOT NULL,PRIMARY KEY(user_id,version));''')
    latest=db.execute('SELECT season,week,version FROM careers ORDER BY season DESC,week DESC LIMIT 1').fetchone()
    db.execute('INSERT OR IGNORE INTO online_clock VALUES(1,?,?,?)',latest or (1,1,1))
    # Operator privileges are explicitly provisioned, never assigned to the first sign-up.
    former=[r[0] for r in db.execute("SELECT career_id FROM members WHERE user_id IN (SELECT user_id FROM league_operators) AND role='admin'")]
    db.execute("UPDATE members SET role='viewer' WHERE user_id IN (SELECT user_id FROM league_operators) AND role='admin'")
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='manager_profiles'").fetchone():
        for cid in former:
            if not db.execute("SELECT 1 FROM members WHERE career_id=? AND role='admin' AND user_id NOT IN (SELECT user_id FROM league_operators)",(cid,)).fetchone():
                db.execute("UPDATE manager_profiles SET name='AI 감독' WHERE career_id=?",(cid,))

def clock(db):
    return dict(zip(('season','week','version'),db.execute('SELECT season,week,version FROM online_clock WHERE id=1').fetchone()))

def operator(db,user): return bool(db.execute('SELECT 1 FROM league_operators WHERE user_id=?',(user,)).fetchone())

def participants(db):
    return {r[0] for r in db.execute('''SELECT DISTINCT m.user_id FROM members m
        JOIN recruitment_state s ON s.career_id=m.career_id WHERE s.complete=1 AND m.role='admin' AND m.user_id NOT IN (SELECT user_id FROM league_operators)''')}

def status(db,user):
    state=clock(db); users=participants(db)
    ready={r[0] for r in db.execute('SELECT user_id FROM online_ready WHERE version=?',(state['version'],))}&users
    return dict(state,ready_count=len(ready),member_count=len(users),ready=user in ready,operator=operator(db,user))

def vote(db,user):
    state=clock(db)
    users=participants(db)
    if user not in users: raise ValueError('finalize the five-player lineup before advancing')
    db.execute('INSERT OR IGNORE INTO online_ready VALUES(?,?)',(user,state['version']))
    return status(db,user)
