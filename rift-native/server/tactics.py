"""Saved team orders. The match worker passes this document into the engine."""
import json
import sys
from pathlib import Path

def _playbook():
    engine = Path(__file__).resolve().parent.parent / 'engine'
    if not (engine / 'playbook.py').exists():
        engine = Path(__file__).resolve().parent / 'engine'
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    import playbook
    return playbook

def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS settings(
        career_id INTEGER NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
        PRIMARY KEY(career_id, key))''')

def load(db, career):
    playbook = _playbook()
    row = db.execute("SELECT value FROM settings WHERE career_id=? AND key='plan'", (career,)).fetchone()
    if not row:
        legacy = db.execute("SELECT value FROM settings WHERE career_id=? AND key='tactics'", (career,)).fetchone()
        return playbook.plan_from_style(legacy[0] if legacy else '균형')
    try:
        return playbook.check(json.loads(row[0]))
    except (ValueError, TypeError, json.JSONDecodeError):
        return playbook.default_plan()

def save(db, career, plan):
    playbook = _playbook()
    checked = playbook.check(plan)
    import recruitment
    selected={p['id'] for p in recruitment.view(db,career)['roster']}
    if any(pid and pid not in selected for pid in checked['callers'].values()):
        raise ValueError('오더 담당은 현재 1군 주전 선수 중에서 선택하세요.')
    raw = json.dumps(checked, ensure_ascii=False)
    db.execute('''INSERT INTO settings(career_id,key,value) VALUES(?,?,?)
        ON CONFLICT(career_id,key) DO UPDATE SET value=excluded.value''', (career, 'plan', raw))
    db.execute('''INSERT INTO settings(career_id,key,value) VALUES(?,?,?)
        ON CONFLICT(career_id,key) DO UPDATE SET value=excluded.value''', (career, 'tactics', checked['mid']['order'] if checked['mid']['order'] in playbook.MACRO else '균형'))
    return checked

def catalog():
    playbook = _playbook()
    return dict(orders=playbook.ORDERS, subs=playbook.SUBS, laning=playbook.LANING, default=playbook.default_plan())
