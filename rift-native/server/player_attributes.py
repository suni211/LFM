"""Per-person FM-style detailed game attributes with operator-only editing.

30 stats on a 1–20 scale. Values without existing source data are stable
*game-only estimates*, NEVER factual assessments of real-world players.
Authoritative operator changes are stored by player ID across all careers.
"""
import hashlib
import json
import math

GROUPS=(
    ('기술 · 라인전',('라인전','CS 수급','스킬 적중','챔피언 숙련','교전','피지컬')),
    ('전술 · 운영',('운영','맵 리딩','오브젝트 판단','로밍','시야','오더 이해')),
    ('팀플레이 · 판단',('협동','한타 포지셔닝','상황 대처','의사소통','팀워크','리더십')),
    ('멘탈 · 경쟁력',('멘탈','집중력','승부욕','압박 대처','꾸준함','자신감')),
    ('성장 · 잠재력',('훈련 태도','프로 의식','성장 가능성','적응력','창의성','경기 이해도')),
)
KEYS=tuple(key for _,group in GROUPS for key in group)
# Preserve existing game six-attribute schema for match/scout compatibility.
BASE=('라인전','교전','운영','시야','협동','멘탈')
FAMILY={}
for _,group in GROUPS:
    for key in group:
        FAMILY[key]=group[0] if group[0] in BASE else (
            '협동' if '팀플레이' in _ else '멘탈')
# Retain skill category anchors explicitly, even for the secondary skills.
FAMILY.update({
    'CS 수급':'라인전','스킬 적중':'교전','챔피언 숙련':'라인전','피지컬':'교전',
    '맵 리딩':'운영','오브젝트 판단':'운영','로밍':'운영',
    '오더 이해':'운영','한타 포지셔닝':'교전','상황 대처':'운영',
    '의사소통':'협동','팀워크':'협동','리더십':'협동',
    '집중력':'멘탈','승부욕':'멘탈','압박 대처':'멘탈','꾸준함':'멘탈',
    '자신감':'멘탈','훈련 태도':'멘탈','프로 의식':'협동',
    '성장 가능성':'멘탈','적응력':'운영','창의성':'운영','경기 이해도':'운영'
})
POS_BONUS={
    'TOP':{'라인전':1,'교전':1,'멘탈':1},
    'JUNGLE':{'운영':2,'시야':2,'협동':1},
    'MID':{'라인전':2,'교전':1,'운영':1},
    'ADC':{'라인전':1,'교전':2,'멘탈':1},
    'SUPPORT':{'시야':2,'협동':2,'운영':1},
}
SOURCE_DEFAULT='game-estimated'
SOURCE_OPERATOR='operator-edited'
NOTICE='선수별 능력치는 LFM 게임 시뮬레이션 수치입니다. 실존 선수의 공식 능력치를 의미하지 않습니다.'

def init(db):
    db.executescript("""CREATE TABLE IF NOT EXISTS player_attribute_overrides(
        person_id TEXT PRIMARY KEY,ratings TEXT NOT NULL,revision INTEGER NOT NULL DEFAULT 1,
        updated_by INTEGER NOT NULL,updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS player_attribute_history(
        id INTEGER PRIMARY KEY,person_id TEXT NOT NULL,updated_by INTEGER NOT NULL,
        changed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,old_ratings TEXT,
        new_ratings TEXT NOT NULL);""")

def _unit(*parts):
    b=hashlib.sha256(':'.join(map(str,parts)).encode('utf8')).digest()
    return int.from_bytes(b[:8],'big')/(2**64)

def _twenty(value):
    if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value):
        return None
    if not 1<=value<=100:return None
    # Existing six-attribute source is out of 100, unlike these 1–20 ratings.
    return max(1,min(20,round(value/5)))

def estimated(person):
    """Stable distinct per-person game stats, anchored to the existing six scores."""
    raw=(person.get('game_evaluation') or {}).get('ratings') or person.get('stats') or {}
    if not isinstance(raw,dict):raw={}
    role=person.get('role') or ''
    player=person['id']
    base={}
    for item in BASE:
        observed=_twenty(raw.get(item))
        base[item]=observed if observed is not None else 9+round(_unit(player,'base',item)*8)
    out={}
    for key in KEYS:
        family=FAMILY.get(key,'운영')
        if key in BASE:score=base[key]
        else:
            jitter=round((_unit(player,'stat',key)-.5)*6)
            score=base[family]+jitter+POS_BONUS.get(role,{}).get(family,0)
        out[key]=max(1,min(20,int(score)))
    return out

def _row(db,person_id):
    return db.execute("""SELECT ratings,revision,updated_by,updated_at
        FROM player_attribute_overrides WHERE person_id=?""",(person_id,)).fetchone()

def read(db,person):
    if person.get('kind')!='player':
        return None
    base=estimated(person)
    row=_row(db,person['id'])
    if row:
        try:
            saved=json.loads(row[0])
            if isinstance(saved,dict):
                base.update({k:int(v) for k,v in saved.items() if k in KEYS
                             and type(v)==int and 1<=v<=20})
        except (ValueError,TypeError,OverflowError):pass
    return dict(ratings=base,groups=[dict(name=name,keys=list(keys)) for name,keys in GROUPS],
                overall=round(sum(base.values())/len(base),1),scale=20,
                source=SOURCE_OPERATOR if row else SOURCE_DEFAULT,
                revision=row[1] if row else 0,updated_at=row[3] if row else None,
                notice=NOTICE)

def save(db,person,ratings,user_id):
    if person.get('kind')!='player':
        raise ValueError('선수만 능력치를 편집할 수 있습니다.')
    if (type(user_id) is not int or user_id<=0 or not isinstance(ratings,dict)
        or set(ratings)!=set(KEYS)
        or any(type(value)!=int or not 1<=value<=20 for value in ratings.values())):
        raise ValueError('30개 선수 능력치를 각각 1~20의 정수로 입력하세요.')
    old=_row(db,person['id'])
    previous=old[0] if old else None
    payload=json.dumps({key:ratings[key] for key in KEYS},ensure_ascii=False,separators=(',',':'))
    if previous!=payload:
        db.execute("""INSERT INTO player_attribute_overrides
            (person_id,ratings,updated_by) VALUES(?,?,?)
            ON CONFLICT(person_id) DO UPDATE SET ratings=excluded.ratings,
                revision=revision+1,updated_by=excluded.updated_by,
                updated_at=CURRENT_TIMESTAMP""",(person['id'],payload,user_id))
        db.execute("""INSERT INTO player_attribute_history
            (person_id,updated_by,old_ratings,new_ratings) VALUES(?,?,?,?)""",
            (person['id'],user_id,previous,payload))
    return read(db,person)

def apply_to_game_evaluation(db,person):
    """Apply operator-edited primary attributes to gameplay and scout estimates."""
    row=_row(db,person['id'])
    if not row or person.get('kind')!='player':return person
    edit=json.loads(row[0])
    if not isinstance(edit,dict):return person
    evaluation=dict(person.get('game_evaluation') or {})
    ratings=dict(evaluation.get('ratings') or {})
    for key in BASE:
        if type(edit.get(key))==int and 1<=edit[key]<=20:
            ratings[key]=edit[key]*5
    evaluation['ratings']=ratings
    evaluation['origin']='game-operator-detail'
    person['game_evaluation']=evaluation
    return person
