"""Bind saved lineups to engine units. Pool champions are skilled; the rest are ordinary."""
import hashlib
import json
import sys
from pathlib import Path
import catalog
import recruitment

def _playbook():
    root = Path(__file__).resolve().parent
    engine = root.parent / 'engine' if (root.parent / 'engine' / 'playbook.py').exists() else root / 'engine'
    if str(engine) not in sys.path:
        sys.path.insert(0, str(engine))
    from playbook import directive, lane_order
    return directive, lane_order

def _bind(db, match, team_index, career):
    import training
    directive, lane_order = _playbook()
    lineup = recruitment.view(db, career)
    if not lineup['complete']:
        return
    by_role = {p['role']: p for p in lineup['roster']}
    for unit in match.players(team_index):
        person = by_role.get(unit.role)
        if not person:
            continue
        person = catalog.detail(db, career, person['id'])
        unit.player_id = person['id']
        unit.player_name = person['display_name']
        dev = training.ensure(db, career, person)
        ratings = (person.get('game_evaluation') or {}).get('ratings') or {}
        unit.command_skill=sum(ratings.get(key,50) for key in ('운영','협동','멘탈'))/300
        nudge = (ratings.get('교전', 50) - 50) / 500
        fatigue = 0
        ward = 90
        if db.execute("SELECT 1 FROM sqlite_master WHERE name='club_health'").fetchone():
            health = db.execute('SELECT fatigue,morale,growth FROM club_health WHERE career_id=? AND person_id=?', (career, person['id'])).fetchone()
            if health:
                fatigue, morale, raw = health
                growth = json.loads(raw)
                ward = max(50, ward - growth.get('시야', 0) / 200 + (60 - morale) * 0.05)
                import staffing
                analysts = sum(staffing.role(p) == 'ANALYST' for p in staffing.active(db, career))
                ward = max(50, ward - analysts * 2)
        on_pool = unit.name in dev['pool']
        unit.mechanics = training.combat_skill(dev['ovr'], on_pool, nudge, fatigue)
        unit.ward_interval = ward
        order, sub = directive(match.playbooks[team_index], 0)
        if sub == '시야 먼저' or lane_order(match.playbooks[team_index], unit.role) == '시야':
            unit.ward_interval = max(45, unit.ward_interval * 0.75)
        scale = (0.96 + dev['ovr'] / 1200) if on_pool else 0.92
        unit.ad *= scale
        unit.maxhp *= scale
        unit.hp = min(unit.maxhp, unit.hp)
        personality = int.from_bytes(hashlib.sha256(person['id'].encode()).digest()[:2], 'big') / 65535
        unit.aggression = .28 + .55 * personality + (0.08 if on_pool else 0)

def apply(db, fixture, match, blue):
    row = db.execute('SELECT career_id,opponent FROM fixtures WHERE id=?', (fixture,)).fetchone()
    if not row:
        raise ValueError('fixture missing')
    _bind(db, match, blue, row[0])
    opponent = db.execute('SELECT id FROM careers WHERE name=?', (row[1],)).fetchone()
    if opponent:
        _bind(db, match, 1 - blue, opponent[0])
