"""Personal training raises OVR or adds a champion. A player keeps two to six champions."""
import json
import random
import sys
from pathlib import Path

MIN_POOL = 2
MAX_POOL = 6
FOCUSES = ('auto', 'ovr', 'pool')

def _rules():
    root = Path(__file__).resolve().parent
    engine = root.parent / 'engine' if (root.parent / 'engine' / 'data.py').exists() else root / 'engine'
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    from data import KITS
    return KITS

def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS player_development(
        career_id INTEGER NOT NULL, person_id TEXT NOT NULL,
        focus TEXT NOT NULL, ovr INTEGER NOT NULL, pool TEXT NOT NULL, assigned TEXT NOT NULL,
        PRIMARY KEY(career_id, person_id))''')

def champions(role):
    return sorted(name for name, kit in _rules().items() if role in kit.roles)

def starting_ovr(person):
    ratings = (person.get('game_evaluation') or {}).get('ratings') or {}
    if ratings:
        return max(40, min(80, round(sum(ratings.values()) / len(ratings))))
    return 58

def seed_pool(person):
    role = person.get('role') or 'MID'
    names = champions(role)
    if len(names) < MIN_POOL:
        raise ValueError('champion pool cannot fill the role')
    rng = random.Random(person['id'] + ':' + role)
    return rng.sample(names, MIN_POOL)

def combat_skill(ovr, on_pool, nudge=0, fatigue=0):
    """Champions inside the pool are played well. Everything else is ordinary."""
    ovr = max(1, min(99, int(ovr)))
    if on_pool:
        value = 0.86 + nudge + (ovr - 60) / 400 - fatigue * 0.001
        return min(0.98, max(0.80, value))
    value = 0.64 + nudge * 0.4 - fatigue * 0.0005
    return min(0.72, max(0.55, value))

def _trim(person, pool):
    role = person.get('role') or 'MID'
    legal = set(champions(role))
    kept = []
    for name in pool:
        if name in legal and name not in kept:
            kept.append(name)
    rng = random.Random(person['id'] + ':fill')
    spare = [name for name in champions(role) if name not in kept]
    rng.shuffle(spare)
    while len(kept) < MIN_POOL and spare:
        kept.append(spare.pop())
    return kept[:MAX_POOL]

def ensure(db, career, person):
    init(db)
    row = db.execute('SELECT focus,ovr,pool,assigned FROM player_development WHERE career_id=? AND person_id=?', (career, person['id'])).fetchone()
    if row:
        focus = row[0] if row[0] in FOCUSES else 'auto'
        pool = _trim(person, json.loads(row[2]))
        return dict(focus=focus, ovr=max(1, min(99, row[1])), pool=pool, assigned=row[3] if row[3] in ('ovr', 'pool') else 'ovr')
    created = dict(focus='auto', ovr=starting_ovr(person), pool=seed_pool(person), assigned='ovr')
    db.execute('INSERT INTO player_development VALUES(?,?,?,?,?)', (career, person['id'], created['focus'], created['ovr'], json.dumps(created['pool'], ensure_ascii=False), created['assigned']))
    return created

def resolve(focus, ovr, pool, week):
    if focus == 'ovr' or len(pool) >= MAX_POOL:
        return 'ovr'
    if focus == 'pool' or len(pool) < 4 or (ovr >= 70 and week % 2 == 0):
        return 'pool'
    return 'ovr'

def apply_week(db, career, person, week, coach_bonus=0):
    if person.get('kind') not in (None, 'player') or person.get('role') not in ('TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'):
        return None
    state = ensure(db, career, person)
    assigned = resolve(state['focus'], state['ovr'], state['pool'], week)
    pool = list(state['pool'])
    ovr = state['ovr']
    if assigned == 'pool' and len(pool) < MAX_POOL:
        spare = [name for name in champions(person.get('role') or 'MID') if name not in pool]
        if spare:
            pick = spare[int.from_bytes(__import__('hashlib').sha256(f"{career}:{person['id']}:{week}".encode()).digest()[:2], 'big') % len(spare)]
            pool.append(pick)
        else:
            assigned = 'ovr'
    if assigned == 'ovr':
        ovr = min(99, ovr + 1 + (1 if coach_bonus else 0))
    db.execute('UPDATE player_development SET ovr=?,pool=?,assigned=? WHERE career_id=? AND person_id=?',
               (ovr, json.dumps(pool, ensure_ascii=False), assigned, career, person['id']))
    state.update(ovr=ovr, pool=pool, assigned=assigned)
    return state

def set_focus(db, career, person, focus):
    if focus not in FOCUSES:
        raise ValueError('invalid training focus')
    state = ensure(db, career, person)
    db.execute('UPDATE player_development SET focus=? WHERE career_id=? AND person_id=?', (focus, career, person['id']))
    state['focus'] = focus
    return state

def roster(db, career, people):
    rows = []
    for person in people:
        if person.get('role') not in ('TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT') or person.get('kind') in ('coach', 'staff'):
            continue
        state = ensure(db, career, person)
        rows.append(dict(person=person, focus=state['focus'], ovr=state['ovr'], pool=state['pool'], assigned=state['assigned'],
                         pool_min=MIN_POOL, pool_max=MAX_POOL))
    return rows

def pools_for_fixture(db, fixture):
    import catalog
    import recruitment
    row = db.execute('SELECT career_id,opponent FROM fixtures WHERE id=?', (fixture,)).fetchone()
    if not row:
        return {'0': {}, '1': {}}
    def side(cid):
        if not cid:
            return {}
        grouped = {}
        for person in recruitment.view(db, cid).get('roster', []):
            detail = catalog.detail(db, cid, person['id'])
            if detail.get('role') not in ('TOP', 'JUNGLE', 'MID', 'ADC', 'SUPPORT'):
                continue
            grouped[detail['role']] = ensure(db, cid, detail)['pool']
        return grouped
    opponent = db.execute('SELECT id FROM careers WHERE name=?', (row[1],)).fetchone()
    return {'0': side(row[0]), '1': side(opponent[0] if opponent else None)}
