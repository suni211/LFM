"""Career onboarding policies and custom second-division club identities.

All values are game balancing rules rather than real-world team rankings.
"""
import re
import base64
import binascii
import json
import catalog

MAJORS={'LCK','LPL','LEC','LCS'}
STARTER_FIRST={'CBLOL','LCP'}
SECOND={'LCK CL','LDL','LCP CL','LCP 2부','LEC ERL','LCS NACL','CBLOL Academy','LPL LDL'}

def is_second(league):
    val=(league or '').casefold()
    return league in SECOND or any(tag in val for tag in ('academy','challenger',' 2부','cl','ldl','erl','nacl'))

def creation_leagues(db):
    found={p.get('league','') for p in catalog.load()['people']}
    return sorted({league for league in found if is_second(league)}|{'LCK CL','LDL','LCP 2부','CBLOL Academy'})

def power(person):
    eval_=(person.get('game_evaluation') or {}).get('ratings') or person.get('stats') or {}
    vals=[v for v in eval_.values() if type(v) in (int,float)]
    return sum(vals)/len(vals) if vals else 50

def club_power(league,team):
    players=[p for p in catalog.load()['people'] if p.get('league')==league and p.get('team')==team and p.get('kind')=='player']
    if not players:return 50.
    return sum(sorted((power(p) for p in players),reverse=True)[:5])/min(5,len(players))

def takeover_allowed(league,team):
    if is_second(league) or league in STARTER_FIRST:return True
    if league in MAJORS:
        # Newcomers cannot take over established top-flight organizations.
        # A genuinely weak first-division team can occasionally accept a rookie.
        rating=club_power(league,team)
        import hashlib
        seed=int(hashlib.sha256((league+'|'+team).encode()).hexdigest()[:8],16)
        return rating<46 and seed%5==0
    return league not in {'LCK','LPL','LEC','LCS'}

def takeover_reason(league,team):
    return '' if takeover_allowed(league,team) else '신인 감독은 상위 파워랭킹 1부 구단에 즉시 부임할 수 없습니다.'

def valid_brand(name,short,color):
    if not isinstance(name,str) or not 2<=len(name.strip())<=40:
        raise ValueError('구단 이름은 2~40자로 입력하세요.')
    if not isinstance(short,str) or not re.fullmatch(r'[A-Z]{3}',short):
        raise ValueError('구단 약자는 영문 대문자 정확히 3자여야 합니다.')
    if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):
        raise ValueError('구단 색상은 #RRGGBB 형식이어야 합니다.')

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS club_branding(
        career_id INTEGER PRIMARY KEY REFERENCES careers(id),
        short TEXT NOT NULL,color TEXT NOT NULL,emblem TEXT NOT NULL DEFAULT 'shield',logo_data TEXT NOT NULL DEFAULT '')""")
    columns={row[1] for row in db.execute('PRAGMA table_info(club_branding)')}
    if 'logo_data' not in columns:db.execute("ALTER TABLE club_branding ADD COLUMN logo_data TEXT NOT NULL DEFAULT ''")

def store_brand(db,career,short,color,emblem,logo_data=''):
    if emblem not in ('shield','star','crown','bolt','diamond'):
        raise ValueError('올바른 엠블럼 형태를 선택하세요.')
    if logo_data:
        if not isinstance(logo_data,str) or len(logo_data)>110000 or not re.fullmatch(r'data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+',logo_data):
            raise ValueError('구단 로고는 80KB 이하 PNG/JPEG/WebP 이미지여야 합니다.')
        try: data=base64.b64decode(logo_data.split(',',1)[1],validate=True)
        except binascii.Error:raise ValueError('잘못된 로고 이미지입니다.')
        if len(data)>80000 or not (data.startswith(b'\x89PNG\r\n\x1a\n') or data.startswith(b'\xff\xd8\xff') or data.startswith(b'RIFF') and data[8:12]==b'WEBP'):
            raise ValueError('잘못된 이미지 형식 또는 80KB 초과 로고입니다.')
    db.execute('INSERT INTO club_branding(career_id,short,color,emblem,logo_data) VALUES(?,?,?,?,?)',(career,short,color,emblem,logo_data))

def brand(db,career):
    row=db.execute('SELECT short,color,emblem,logo_data FROM club_branding WHERE career_id=?',(career,)).fetchone()
    return dict(zip(('short','color','emblem','logo_data'),row)) if row else None

def seed_league(db,career,league,season,week):
    """Create real scheduled fixtures if at least three genuine opponent clubs exist."""
    import league as league_engine
    if week>=95:return 0
    names={p['team'] for p in catalog.teams() if p['league']==league}
    names.update(r[0] for r in db.execute(
        'SELECT c.name FROM careers c JOIN club_profiles p ON p.career_id=c.id WHERE p.league=?',(league,)))
    own=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    names.discard(own)
    opponents=sorted(names)[:min(7,max(0,96-week))]
    # In fictional expansion divisions, use clearly identified AI clubs instead of
    # inventing genuine historical second-tier affiliates.
    for suffix in ('Academy North (AI)','Academy South (AI)','Academy West (AI)'):
        if len(opponents)>=3:break
        name=league+' '+suffix
        if name!=own and name not in opponents:opponents.append(name)
    # All assignments and future fixtures generated in this transaction.
    return league_engine.create(db,career,season,week+1,opponents)
