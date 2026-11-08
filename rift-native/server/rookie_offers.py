"""Persistent game-simulated offers sent to newly created manager accounts.

The 5 invitations are from EXISTING playable clubs, not invented real-world
employment approaches. Offers are frozen for each account and protected by
server-side acceptance validation.
"""
import hashlib
import catalog
import clubs
import career_rules

OFFER_COUNT=5

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS rookie_manager_offers(
        user_id INTEGER NOT NULL REFERENCES users(id),
        team_key TEXT NOT NULL,
        league TEXT NOT NULL,
        team TEXT NOT NULL,
        ordinal INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'offered',
        PRIMARY KEY(user_id,team_key), UNIQUE(user_id,ordinal))""")

def _unit(seed):
    return int.from_bytes(hashlib.sha256(seed.encode()).digest()[:8],'big') / 2**64

def _candidate(db, user_id):
    pool=[]
    for club in clubs.available(db):
        if not career_rules.takeover_allowed(club['league'],club['team']):
            continue
        if club['claimed']:
            row=db.execute('SELECT career_id FROM club_profiles WHERE team_key=?',(club['team_key'],)).fetchone()
            if row and clubs.human_owner(db,row[0]):
                continue
        rating=career_rules.club_power(club['league'],club['team'])
        if rating>65 and not career_rules.is_second(club['league']):
            continue
        rank=0 if career_rules.is_second(club['league']) else 1 if club['league'] in ('CBLOL','LCP') else 2
        variance=_unit(f'{user_id}|{club["team_key"]}|recruiter')
        # In an unverified data set, use reputation group and stable per-account chance;
        # power only breaks near ties. No direct elite-league interviews.
        pool.append((rank,variance+.015*max(0,rating-48),club))
    pool.sort(key=lambda entry:(entry[0],entry[1],entry[2]['team']))
    return [club for _,_,club in pool]

def list_offers(db,user_id):
    existing=db.execute('SELECT 1 FROM rookie_manager_offers WHERE user_id=? LIMIT 1',(user_id,)).fetchone()
    if not existing:
        pool=_candidate(db,user_id)
        if len(pool)<OFFER_COUNT:
            raise ValueError('리그 구단 정보가 부족해 5개 부임 제안을 발송할 수 없습니다.')
        # Include a mix of second division and entry-tier first-division clubs.
        secondary=[p for p in pool if career_rules.is_second(p['league'])]
        first=[p for p in pool if p['league'] in ('CBLOL','LCP')]
        choices=secondary[:4]
        if first and len(choices)>=3:
            choices=secondary[:3]+first[:2]
        choices.extend(p for p in pool if p not in choices)
        choices=choices[:OFFER_COUNT]
        for ordinal,item in enumerate(choices,1):
            db.execute('INSERT INTO rookie_manager_offers(user_id,team_key,league,team,ordinal) VALUES(?,?,?,?,?)',
                       (user_id,item['team_key'],item['league'],item['team'],ordinal))
    rows=db.execute('SELECT team_key,league,team,ordinal,status FROM rookie_manager_offers WHERE user_id=? ORDER BY ordinal',(user_id,)).fetchall()
    offers=[]
    for key,league,team,ordinal,status in rows:
        row=db.execute('SELECT career_id FROM club_profiles WHERE team_key=?',(key,)).fetchone()
        occupied=bool(row and clubs.human_owner(db,row[0]))
        offers.append(dict(team_key=key,league=league,team=team,ordinal=ordinal,
                          power=round(career_rules.club_power(league,team),1),
                          available=status=='offered' and not occupied,status='filled' if occupied and status=='offered' else status,
                          description='하위 리그에서 전술과 신인 육성 능력을 증명할 신임 감독을 찾습니다.' if career_rules.is_second(league)
                                      else '신인 감독에게 팀 재건과 성적 향상의 기회를 제공합니다.',
                          source='game-simulation'))
    return offers

def invited(db,user_id,team_key):
    return any(row['team_key']==team_key and row['available'] for row in list_offers(db,user_id))

def accept(db,user_id,team_key):
    if not invited(db,user_id,team_key):
        raise ValueError('받은 구단 부임 제안만 수락할 수 있습니다.')
    db.execute("""UPDATE rookie_manager_offers SET status='accepted'
                  WHERE user_id=? AND team_key=? AND status='offered'""",(user_id,team_key))
    db.execute("""UPDATE rookie_manager_offers SET status='closed'
                  WHERE user_id=? AND team_key!=? AND status='offered'""",(user_id,team_key))
