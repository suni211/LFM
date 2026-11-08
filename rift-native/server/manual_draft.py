"""Authoritative manual tournament draft shared by server and standalone UI."""
import random,time
from pathlib import Path
import sys
from series import remaining_assignment

def engine_rules():
    base=Path(__file__).resolve().parent
    engine=base/'engine' if (base/'engine'/'data.py').exists() else base.parent/'engine'
    if str(engine) not in sys.path:sys.path.insert(0,str(engine))
    from data import KITS,ROLES
    return KITS,ROLES

def order(first):
    other=1-first
    return [('ban',t) for t in (first,other)*3]+[('pick',t) for t in (first,other,other,first,first,other)]+[('ban',t) for t in (other,first)*2]+[('pick',t) for t in (other,first,first,other)]

def start(state):
    state.update(phase='draft',draft=[],draft_picks=[[],[]],draft_bans=[],draft_version=0,response_until=time.time()+180)

def layout(picks,available,kits,roles,reserve_sets=0):
    """Place mandatory flex picks before filling open slots; never discard a pick."""
    chosen=sorted([(team,name) for team in (0,1) for name in picks[team]],key=lambda pair:len(kits[pair[1]].roles))
    placed={};slots={(team,role) for team in (0,1) for role in range(len(roles))}
    future=[(2*n+team,role) for n in range(1,reserve_sets+1) for team in (0,1) for role in range(len(roles))]
    def visit(index):
        if index==len(chosen):
            return dict(placed) if remaining_assignment(sorted(slots)+future,available,kits,roles) else None
        team,name=chosen[index]
        for role in range(len(roles)):
            slot=(team,role)
            if slot not in slots or roles[role] not in kits[name].roles:continue
            slots.remove(slot);placed[slot]=name
            result=visit(index+1)
            slots.add(slot);placed.pop(slot)
            if result is not None:return result
        return None
    return visit(0)

def legal(state,name,kits,roles):
    if state.get('phase')!='draft' or name not in kits:return False
    taken=set(state.get('fearless_bans',[]))|set(state['draft_bans'])|set(sum(state['draft_picks'],[]))
    if name in taken:return False
    step=len(state['draft']);sequence=order(state['first'])
    if step>=len(sequence):return False
    action,team=sequence[step]
    picks=[list(p) for p in state['draft_picks']]
    if action=='pick':picks[team].append(name)
    available=sorted(set(kits)-taken-{name})
    return layout(picks,available,kits,roles,max(0,state.get('best_of',3)-len(state['sets'])-1)) is not None

def submit(state,name,kits,roles,now,version=None):
    if version is not None and version!=state.get('draft_version'):raise ValueError('stale draft version')
    if not legal(state,name,kits,roles):raise ValueError('champion is unavailable or leaves no valid team composition')
    action,team=order(state['first'])[len(state['draft'])]
    state['draft'].append(dict(action=action,team=team,champion=name))
    (state['draft_bans'] if action=='ban' else state['draft_picks'][team]).append(name)
    state['draft_version']+=1
    state['response_until']=now+180
    if len(state['draft'])==20:
        placed=layout(state['draft_picks'],[],kits,roles)
        if placed is None:raise ValueError('invalid final draft')
        blue=state['blue']
        roster=[[placed[t,r] for r in range(len(roles))] for t in (blue,1-blue)]
        state.update(phase='swap',roster=roster,swap_until=now+(0 if state.get('autoplay') else 30),swap_version=0,
                     response_until=None,role_options={name:list(kits[name].roles) for row in roster for name in row})

def bot(state,seed,kits,roles,now,all_teams=False):
    rng=random.Random(seed+state.get('draft_version',0)*97+len(state['sets'])*101)
    while state.get('phase')=='draft':
        _,team=order(state['first'])[len(state['draft'])]
        if team==0 and not all_teams and not state.get('autoplay'):break
        candidates=sorted(kits);rng.shuffle(candidates)
        pool=set()
        for names in (state.get('pools') or {}).get(str(team), {}).values():
            pool.update(names)
        favored=[n for n in candidates if n in pool and legal(state,n,kits,roles)]
        name=next(iter(favored), None) or next((n for n in candidates if legal(state,n,kits,roles)),None)
        if name is None:raise ValueError('no legal draft action')
        submit(state,name,kits,roles,now)
