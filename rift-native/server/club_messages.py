"""Shared club inbox with per-member read status and personal recruitment lists."""
import catalog

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS club_mail(
        id INTEGER PRIMARY KEY, career_id INTEGER NOT NULL REFERENCES careers(id),
        event_key TEXT NOT NULL, season INTEGER NOT NULL, week INTEGER NOT NULL,
        subject TEXT NOT NULL, body TEXT NOT NULL, UNIQUE(career_id,event_key));
        CREATE TABLE IF NOT EXISTS mail_reads(
        mail_id INTEGER NOT NULL REFERENCES club_mail(id), user_id INTEGER NOT NULL REFERENCES users(id),
        PRIMARY KEY(mail_id,user_id));
        CREATE TABLE IF NOT EXISTS shortlists(
        career_id INTEGER NOT NULL REFERENCES careers(id), user_id INTEGER NOT NULL REFERENCES users(id),
        person_id TEXT NOT NULL, PRIMARY KEY(career_id,user_id,person_id));''')

def publish(db,career,key,season,week,subject,body):
    db.execute('INSERT OR IGNORE INTO club_mail(career_id,event_key,season,week,subject,body) VALUES(?,?,?,?,?,?)',
               (career,key,season,week,subject,body))

def inbox(db,career,user,before=None):
    if before is not None and (type(before) is not int or before<1): raise ValueError('invalid cursor')
    rows=db.execute('''SELECT m.id,m.season,m.week,m.subject,m.body,r.user_id IS NOT NULL
        FROM club_mail m LEFT JOIN mail_reads r ON r.mail_id=m.id AND r.user_id=?
        WHERE m.career_id=? AND (? IS NULL OR m.id<?) ORDER BY m.id DESC LIMIT 150''',(user,career,before,before))
    return [dict(zip(('id','season','week','subject','body','read'),row)) for row in rows]

def mark_read(db,career,user,mail_id):
    if type(mail_id) is not int or not 1<=mail_id<=2**63-1: raise ValueError('invalid message')
    row=db.execute('SELECT id FROM club_mail WHERE id=? AND career_id=?',(mail_id,career)).fetchone()
    if row is None: raise KeyError(mail_id)
    db.execute('INSERT OR IGNORE INTO mail_reads VALUES(?,?)',(mail_id,user))

def shortlist(db,career,user):
    ids=[row[0] for row in db.execute('SELECT person_id FROM shortlists WHERE career_id=? AND user_id=? ORDER BY person_id',(career,user))]
    return [catalog.detail(db,career,person_id) for person_id in ids]

def set_shortlist(db,career,user,person_id,enabled):
    if type(enabled) is not bool or not isinstance(person_id,str): raise ValueError('invalid shortlist')
    if enabled:
        catalog.detail(db,career,person_id)
        count=db.execute('SELECT COUNT(*) FROM shortlists WHERE career_id=? AND user_id=?',(career,user)).fetchone()[0]
        if count>=150 and not db.execute('SELECT 1 FROM shortlists WHERE career_id=? AND user_id=? AND person_id=?',(career,user,person_id)).fetchone():
            raise ValueError('shortlist is full')
        inserted=db.execute('INSERT OR IGNORE INTO shortlists VALUES(?,?,?)',(career,user,person_id))
        if inserted.rowcount:
            import rumors
            rumors.interest(db,career,catalog.detail(db,career,person_id))
    else:
        db.execute('DELETE FROM shortlists WHERE career_id=? AND user_id=? AND person_id=?',(career,user,person_id))
