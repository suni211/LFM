"""Series and draft rules. Pick priority and map side are independent."""
from dataclasses import dataclass
import random

CHOICES = {"priority": ("first", "second"), "side": ("blue", "red")}

@dataclass(frozen=True)
class Draft:
    first: int
    blue: int
    actions: tuple
    roster: tuple

def resolve_choices(chooser, category, value, other_value):
    if chooser not in (0, 1) or category not in CHOICES or value not in CHOICES[category]:
        raise ValueError("invalid initial draft choice")
    other_category = "side" if category == "priority" else "priority"
    if other_value not in CHOICES[other_category]:
        raise ValueError("opponent must choose the other category")
    owners = {category:(chooser,value),other_category:(1-chooser,other_value)}
    priority_team, priority = owners["priority"]
    side_team, side = owners["side"]
    return (priority_team if priority == "first" else 1-priority_team,
            side_team if side == "blue" else 1-side_team)

def remaining_assignment(slots, available, kits, roles):
    matched = {}
    def assign(slot, seen):
        role = roles[slot[1]]
        for champion in available:
            if champion in seen or role not in kits[champion].roles:
                continue
            seen.add(champion)
            if champion not in matched or assign(matched[champion],seen):
                matched[champion] = slot
                return True
        return False
    return all(assign(slot,set()) for slot in slots)

def auto_draft(seed, kits, roles, first, blue, blocked=(), reserve_sets=0, preferred=None):
    """Tournament 3-ban/3-pick/2-ban/2-pick draft, with hard fearless exclusions.

    Matching also reserves legal role assignments for every possible later set.
    Bans expire at the end of this draft; previous picks never do within a series.
    """
    rng = random.Random(seed)
    second = 1-first
    slots = [(team,role) for team in (0,1) for role in range(len(roles))]
    available = sorted(set(kits)-set(blocked))
    future=[(team+2*n,role) for n in range(1,reserve_sets+1) for team in (0,1) for role in range(len(roles))]
    if not remaining_assignment(slots,available,kits,roles):
        raise ValueError("champion pool cannot fill both teams")
    actions = []
    picked = {}
    def ban(team):
        valid = [champion for champion in available if remaining_assignment(
            slots+future,[other for other in available if other != champion],kits,roles)]
        if not valid:
            raise ValueError('champion pool cannot support tournament bans and fearless roles')
        champion = rng.choice(valid)
        available.remove(champion)
        actions.append(dict(action="ban",team=team,champion=champion))
    def pick(team):
        legal = []
        for slot in slots:
            if slot[0] != team:
                continue
            remaining = [other for other in slots if other != slot]
            for champion in available:
                if roles[slot[1]] in kits[champion].roles and remaining_assignment(
                    remaining+future,[other for other in available if other != champion],kits,roles):
                    legal.append((slot,champion))
        wanted=set()
        for names in (preferred or {}).get(team, {}).values():
            wanted.update(names)
        favored=[item for item in legal if item[1] in wanted]
        slot, champion = rng.choice(favored or legal)
        slots.remove(slot)
        available.remove(champion)
        picked[slot] = champion
        actions.append(dict(action="pick",team=team,champion=champion,role=roles[slot[1]]))
    for team in (first,second)*3:ban(team)
    for team in (first,second,second,first,first,second):pick(team)
    for team in (second,first)*2:ban(team)
    for team in (second,first,first,second):pick(team)
    roster = tuple(tuple(picked[team,i] for i in range(len(roles))) for team in (blue,1-blue))
    return Draft(first,blue,tuple(actions),roster)

def after_set(score, winner, finished_at, wins_needed=2):
    if (type(wins_needed) is not int or wins_needed not in (2,3) or
        len(score)!=2 or any(type(n) is not int or n<0 for n in score) or
        type(winner) is not int or winner not in (0,1) or max(score) >= wins_needed):
        raise ValueError("invalid set result")
    score = [*score]
    score[winner] += 1
    return {"score":score, "winner":winner if score[winner] == wins_needed else None,
            "feedback_until":None if score[winner] == wins_needed else finished_at + 60}
