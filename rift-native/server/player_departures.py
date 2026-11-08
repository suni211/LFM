"""Player-led release requests. User managers decide; AI-managed careers auto-consent.

This subsystem does not treat a poor mood as automatic contract termination.
An unhappy player can ask for release; approval creates a true free-agent.
"""
import hashlib
import catalog
import club_messages

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS player_departure_requests(
        career_id INTEGER NOT NULL, person_id TEXT NOT NULL,
        season INTEGER NOT NULL, week INTEGER NOT NULL,
        reason TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
        PRIMARY KEY(career_id,person_id,season,week))""")

def _unit(value):
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], 'big') / (2**64-1)

def pending(db,career):
    rows=db.execute("""SELECT r.person_id,r.season,r.week,r.reason,
            h.morale,coalesce(cr.assignment,g.assignment,'unknown')
        FROM player_departure_requests r
        LEFT JOIN club_health h ON h.career_id=r.career_id AND h.person_id=r.person_id
        LEFT JOIN club_roster cr ON cr.career_id=r.career_id AND cr.person_id=r.person_id
        LEFT JOIN generated_people g ON g.career_id=r.career_id AND g.id=r.person_id
        WHERE r.career_id=? AND r.status='pending'
        ORDER BY r.season,r.week,r.person_id""",(career,)).fetchall()
    return [dict(person_id=pid,season=season,week=week,reason=reason,
                 morale=morale,assignment=assignment)
            for pid,season,week,reason,morale,assignment in rows]

def release(db,career,pid):
    """Terminate contract and free ownership atomically in caller's transaction."""
    owner=db.execute("SELECT career_id FROM person_ownership WHERE person_id=?",(pid,)).fetchone()
    if owner and owner[0] not in (career,None):
        raise ValueError('player ownership has changed')
    if not db.execute("SELECT 1 FROM club_contracts WHERE career_id=? AND person_id=? AND active=1",(career,pid)).fetchone():
        raise ValueError('active player contract required')
    db.execute("UPDATE club_roster SET assignment='departed' WHERE career_id=? AND person_id=?",(career,pid))
    db.execute("UPDATE generated_people SET assignment='departed' WHERE career_id=? AND id=?",(career,pid))
    db.execute("UPDATE club_contracts SET active=0 WHERE career_id=? AND person_id=?",(career,pid))
    db.execute("""INSERT INTO person_ownership VALUES(?,NULL,'free-agent')
                  ON CONFLICT(person_id) DO UPDATE SET career_id=NULL,club_key='free-agent'""",(pid,))

def resolve(db,career,pid,approve):
    if not isinstance(pid,str) or type(approve) is not bool: raise ValueError('invalid release decision')
    row=db.execute("""SELECT season,week FROM player_departure_requests
        WHERE career_id=? AND person_id=? AND status='pending'
        ORDER BY season DESC,week DESC LIMIT 1""",(career,pid)).fetchone()
    if not row: raise ValueError('no pending player request')
    season,week=row
    if approve:
        release(db,career,pid)
    db.execute("""UPDATE player_departure_requests SET status=?
        WHERE career_id=? AND person_id=? AND season=? AND week=?""",
        ('approved' if approve else 'declined',career,pid,season,week))
    club_messages.publish(db,career,'release-decision:'+pid+':'+str(season)+':'+str(week),
                          season,week,'선수 FA 방출 결정',
                          pid+(' 선수와 합의하여 FA가 되었습니다.' if approve else ' 선수의 방출 요청을 거절했습니다.'))
    return dict(approved=approve,person_id=pid)

def weekly(db,career,season,week):
    """Bench frustration can produce a request; it never silently releases a user player."""
    now=(season-1)*104+week
    import online_world
    import recruitment
    roster=recruitment.view(db,career)['people']
    manager=db.execute("""SELECT 1 FROM members m
        WHERE m.career_id=? AND m.role='admin'
        AND m.user_id NOT IN (SELECT user_id FROM league_operators) LIMIT 1""",(career,)).fetchone()
    for person in roster:
        if person.get('kind')!='player': continue
        assignment=person.get('assignment')
        if assignment not in ('reserve','academy'): continue
        pid=person['id']
        row=db.execute("""SELECT h.morale FROM club_health h JOIN club_contracts c
            ON c.career_id=h.career_id AND c.person_id=h.person_id
            WHERE h.career_id=? AND h.person_id=? AND c.active=1""",(career,pid)).fetchone()
        if not row: continue
        morale=row[0]
        # Players who cannot start become dissatisfied, especially reserves.
        morale=max(0,morale-(5 if assignment=='reserve' else 3))
        db.execute("UPDATE club_health SET morale=? WHERE career_id=? AND person_id=?",(morale,career,pid))
        if morale>45: continue
        if db.execute("SELECT 1 FROM player_departure_requests WHERE career_id=? AND person_id=? AND status='pending'",(career,pid)).fetchone(): continue
        chance=(0.65 if assignment=='reserve' else 0.35)*(1+(45-morale)/100)
        if _unit(f'{career}:{pid}:{now}:departure')>=chance: continue
        reason='주전 경쟁에서 밀려 다른 팀의 선발 기회를 원합니다.' if assignment=='reserve' else '2군 생활에 불만이 있어 정기 출전을 원합니다.'
        db.execute("INSERT OR IGNORE INTO player_departure_requests VALUES(?,?,?,?,?,'pending')",
                   (career,pid,season,week,reason))
        club_messages.publish(db,career,'release-request:'+pid+':'+str(now),season,week,
                              '선수 FA 방출 요청',(person.get('nickname') or catalog.display(person))+' · '+reason+' 구단에서 협의가 필요합니다.')
        if not manager:
            resolve(db,career,pid,True)
