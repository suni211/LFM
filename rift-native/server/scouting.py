"""Fictional in-game scouting: per-club estimates and annual agency bulletin.

Not actual external scout/agency reports. Ratings vary with scout quality.
"""
import hashlib
import json
import catalog

ATTRS=catalog.ATTRIBUTES
AGENCY="R/M 리그 데이터 연구소"

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS agency_reports(
        person_id TEXT NOT NULL,season INTEGER NOT NULL,summary TEXT NOT NULL,
        PRIMARY KEY(person_id,season))""")

def unit(key):
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:8],"big")/(2**64-1)

def ratings(person):
    ev=person.get('game_evaluation') or {}
    vals=ev.get('ratings') or person.get('stats') or {}
    return {name:max(1,min(100,int(vals.get(name,50)))) for name in ATTRS}

def overall(person):
    r=ratings(person)
    return sum(r.values())/max(1,len(r))

def stars(score):
    return max(.5,min(5.0,round((.5+4.5*score/100)*2)/2))

def scout_quality(db,career):
    if not career: return (None,0)
    row=db.execute('SELECT stats FROM manager_profiles WHERE career_id=?',(career,)).fetchone()
    base=10
    if row:
        try:base=int(json.loads(row[0]).get('스카우팅',10))
        except (TypeError,ValueError):pass
    analysts=0
    try:
        import staffing
        analysts=sum(staffing.role(p)=='ANALYST' for p in staffing.active(db,career))
    except (ValueError,KeyError): pass
    return max(1,min(20,base+2*analysts)),analysts

def personal(db,career,person,season):
    skill,analysts=scout_quality(db,career)
    if skill is None:return None
    uncertainty=max(2,round((21-skill)*1.0))
    deviation=(2*unit(f'scout:{career}:{person["id"]}:{season}')-1)*uncertainty
    estimate=max(1,min(100,overall(person)+deviation))
    potential=min(100,estimate+3+unit(f'potential:{career}:{person["id"]}:{season}')*15)
    return dict(source='우리 구단 스카우팅팀',season=season,
        scout_skill=skill,analysts=analysts,
        confidence='높음' if skill>=17 else '보통' if skill>=11 else '낮음',
        current_stars=stars(estimate),potential_stars=stars(potential),
        summary='구단 스카우터의 추정치입니다. 담당자의 능력에 따라 실제 실력과 차이가 날 수 있습니다.')

def annual(db,person,season):
    row=db.execute('SELECT summary FROM agency_reports WHERE person_id=? AND season=?',
                   (person['id'],season)).fetchone()
    if row: return json.loads(row[0])
    rating=round(overall(person),1)
    report=dict(source=AGENCY,kind='게임 내 가상 기관 연례 발표',season=season,
                current_stars=stars(rating),score=rating,
                summary='한 시즌에 한 번 발표되며 같은 시즌에는 평가가 바뀌지 않습니다.')
    db.execute('INSERT OR IGNORE INTO agency_reports VALUES(?,?,?)',
               (person['id'],season,json.dumps(report,ensure_ascii=False)))
    return report

def report(db,career,person):
    row=db.execute('SELECT season FROM careers WHERE id=?',(career,)).fetchone() if career else None
    if not row:
        import online_world
        season=online_world.clock(db)['season']
    else:season=row[0]
    return dict(scout=personal(db,career,person,season),agency=annual(db,person,season))
