"""Stable club public identity, operator renaming, editable logos and full history.

Canonical team names and team_key NEVER change. This prevents match,
transfer and player references from breaking on brand-name updates.
Manager: can change own crest only. Operator: can edit all names and crests.
"""
import base64
import binascii
import re

def init(db):
    db.executescript("""CREATE TABLE IF NOT EXISTS club_public_identity(
      league TEXT NOT NULL, canonical_team TEXT NOT NULL,
      display_name TEXT NOT NULL DEFAULT '',logo_data TEXT NOT NULL DEFAULT '',
      short TEXT NOT NULL DEFAULT '',color TEXT NOT NULL DEFAULT '#17324d',
      PRIMARY KEY(league,canonical_team));
    CREATE TABLE IF NOT EXISTS club_identity_history(
      id INTEGER PRIMARY KEY,league TEXT NOT NULL,canonical_team TEXT NOT NULL,
      season INTEGER NOT NULL,week INTEGER NOT NULL,event TEXT NOT NULL,
      headline TEXT NOT NULL,details TEXT NOT NULL DEFAULT '',
      source TEXT NOT NULL DEFAULT 'game-simulation');""")
    db.execute("""CREATE INDEX IF NOT EXISTS club_identity_history_lookup
        ON club_identity_history(league,canonical_team,season DESC,week DESC,id DESC)""")

def validate_logo(value):
    if not isinstance(value,str):
        raise ValueError('로고 형식이 잘못됐습니다.')
    if not value:return ''
    if len(value)>110000 or not re.fullmatch(
        r'data:image/(png|jpeg|webp);base64,[A-Za-z0-9+/=]+',value):
        raise ValueError('로고는 80KB 이하 PNG/JPEG/WebP여야 합니다.')
    try:raw=base64.b64decode(value.partition(',')[2],validate=True)
    except (binascii.Error,ValueError):
        raise ValueError('잘못된 로고 이미지입니다.')
    if len(raw)>80000 or not (
        raw.startswith(b'\x89PNG\r\n\x1a\n') or
        raw.startswith(b'\xff\xd8\xff') or
        (raw.startswith(b'RIFF') and raw[8:12]==b'WEBP')):
        raise ValueError('80KB 이하의 유효한 이미지 파일만 등록할 수 있습니다.')
    return value

def display(db,league,team):
    row=db.execute("""SELECT display_name FROM club_public_identity
         WHERE league=? AND canonical_team=?""",(league,team)).fetchone()
    return row[0] if row and row[0] else team

def visual(db,league,team):
    row=db.execute("""SELECT display_name,logo_data,short,color FROM club_public_identity
         WHERE league=? AND canonical_team=?""",(league,team)).fetchone()
    return dict(zip(('display_name','logo_data','short','color'),row)) if row else None

def record(db,league,team,season,week,event,headline,details='',
           source='game-simulation'):
    if not isinstance(league,str) or not isinstance(team,str):
        raise ValueError('invalid club identity')
    db.execute("""INSERT INTO club_identity_history
        (league,canonical_team,season,week,event,headline,details,source)
        VALUES(?,?,?,?,?,?,?,?)""",
        (league,team,season,week,event,headline,details,source))

def history(db,league,team,limit=80):
    return [dict(zip(('season','week','event','headline','details','source'),r))
        for r in db.execute("""SELECT season,week,event,headline,details,source
            FROM club_identity_history WHERE league=? AND canonical_team=?
            ORDER BY season DESC,week DESC,id DESC LIMIT ?""",
            (league,team,min(100,max(1,limit))))]

def exists(db,league,team):
    import catalog
    if any(p['league']==league and p['team']==team for p in catalog.teams()):
        return True
    return bool(db.execute("""SELECT 1 FROM careers c
        JOIN club_profiles p ON p.career_id=c.id
        WHERE p.league=? AND c.name=?""",(league,team)).fetchone())

def update_logo(db,league,team,logo_data,season,week,actor='manager'):
    if not exists(db,league,team):
        raise ValueError('등록된 구단을 찾을 수 없습니다.')
    image=validate_logo(logo_data)
    db.execute("""INSERT INTO club_public_identity
        (league,canonical_team,logo_data) VALUES(?,?,?)
        ON CONFLICT(league,canonical_team) DO UPDATE SET
        logo_data=excluded.logo_data""",(league,team,image))
    record(db,league,team,season,week,'logo-change',
           '구단 대표 로고 변경','운영자 승인' if actor=='operator' else '구단 감독 설정',
           'game-user-action')

def rename(db,league,team,new_name,season,week):
    """Operator-only, enforced at HTTP entry. Never rename canonical data."""
    if not exists(db,league,team):
        raise ValueError('등록된 구단을 찾을 수 없습니다.')
    if not isinstance(new_name,str) or not 2<=len(new_name.strip())<=48:
        raise ValueError('구단 이름은 2~48자로 입력해야 합니다.')
    name=new_name.strip()
    if any(ch in name for ch in '<>{}\n\r\t'):
        raise ValueError('구단명에 허용되지 않는 문자가 있습니다.')
    import catalog
    if any(row['league']==league and row['team']!=team and row['team'].casefold()==name.casefold()
           for row in catalog.teams()):
        raise ValueError('이미 존재하는 구단명입니다.')
    for row in db.execute("""SELECT canonical_team,display_name FROM club_public_identity
        WHERE league=?""",(league,)):
        if row[0]!=team and row[1].casefold()==name.casefold():
            raise ValueError('해당 이름을 사용하는 구단이 이미 있습니다.')
    for row in db.execute("""SELECT name FROM careers c
        JOIN club_profiles p ON p.career_id=c.id WHERE p.league=?""",(league,)):
        if row[0]!=team and row[0].casefold()==name.casefold():
            raise ValueError('같은 리그에 동일한 구단명이 존재합니다.')
    before=display(db,league,team)
    if name==before:return dict(changed=False,display_name=name)
    db.execute("""INSERT INTO club_public_identity
        (league,canonical_team,display_name) VALUES(?,?,?)
        ON CONFLICT(league,canonical_team) DO UPDATE SET
        display_name=excluded.display_name""",(league,team,name))
    record(db,league,team,season,week,'club-renamed',
           '구단명 변경… '+before+' → '+name,
           '과거 경기 및 소속 기록은 이전 이름과 연결됨','game-operator-action')
    return dict(changed=True,display_name=name,previous_name=before)
