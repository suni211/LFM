"""Role-locked ban/pick. Three bans a side, then one champion per role.

The pool has 17 kits and only three marksmen, so a ban or pick is legal only
when both teams can still be assigned a full role lineup.
"""
from data import KITS, ROLES

TURNS = [('ban', 0, None), ('ban', 1, None)] * 3 + [
    ('pick', 0, 'TOP'), ('pick', 1, 'TOP'),
    ('pick', 1, 'JUNGLE'), ('pick', 0, 'JUNGLE'),
    ('pick', 0, 'MID'), ('pick', 1, 'MID'),
    ('pick', 1, 'ADC'), ('pick', 0, 'ADC'),
    ('pick', 0, 'SUPPORT'), ('pick', 1, 'SUPPORT'),
]


def assignable(champions, slots):
    match = {}

    def visit(index, seen):
        role = slots[index]
        for champion in champions:
            if champion in seen or role not in KITS[champion].roles:
                continue
            seen.add(champion)
            if champion not in match or visit(match[champion], seen):
                match[champion] = index
                return True
        return False

    return all(visit(index, set()) for index in range(len(slots)))


class Draft:
    def __init__(self, pools=None):
        empty = [{} for _ in ROLES]
        self.pools = pools or (empty, [dict(pool) for pool in empty])
        self.banned = []
        self.picks = [[None] * 5, [None] * 5]
        self.index = 0

    @property
    def done(self):
        return self.index >= len(TURNS)

    def turn(self):
        return None if self.done else TURNS[self.index]

    def roster(self):
        return tuple(tuple(team) for team in self.picks)

    def taken(self):
        return set(self.banned) | {champion for team in self.picks for champion in team if champion}

    def open_slots(self):
        return [role for team in self.picks for role, champion in zip(ROLES, team) if champion is None]

    def legal(self, champion):
        turn = self.turn()
        if not turn or champion not in KITS or champion in self.taken():
            return False
        kind, _team, role = turn
        if kind == 'pick' and role not in KITS[champion].roles:
            return False
        slots = self.open_slots()
        if kind == 'pick':
            slots.remove(role)
        remaining = [name for name in KITS if name not in self.taken() and name != champion]
        return assignable(remaining, slots)

    def choose(self, champion):
        if not self.legal(champion):
            return False
        kind, team, role = self.turn()
        if kind == 'ban':
            self.banned.append(champion)
        else:
            self.picks[team][ROLES.index(role)] = champion
        self.index += 1
        return True

    def suggest(self):
        kind, team, role = self.turn()
        legal = [champion for champion in KITS if self.legal(champion)]
        if not legal:
            raise RuntimeError('선택할 수 있는 챔피언이 없습니다')
        if kind == 'ban':
            scores = {}
            for pool in self.pools[team ^ 1]:
                for champion, value in pool.items():
                    scores[champion] = scores.get(champion, 0) + value
            legal.sort(key=lambda champion: (scores.get(champion, 0), champion in ('Ashe', 'Sivir', 'Tristana')), reverse=True)
            return legal[0]
        pool = self.pools[team][ROLES.index(role)]
        legal.sort(key=lambda champion: pool.get(champion, 0), reverse=True)
        return legal[0]

    def auto(self):
        while not self.done:
            if not self.choose(self.suggest()):
                raise RuntimeError('밴픽이 진행되지 않습니다')
