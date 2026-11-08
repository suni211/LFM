"""Persistent between-set transitions shared by the API and the worker."""
import json
import random
import time
from series import CHOICES, after_set, resolve_choices, auto_draft

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS match_series(
        fixture_id INTEGER PRIMARY KEY REFERENCES fixtures(id), state TEXT NOT NULL)""")

def put(db, fixture, state):
    db.execute("""INSERT INTO match_series VALUES(?,?)
        ON CONFLICT(fixture_id) DO UPDATE SET state=excluded.state""",
        (fixture,json.dumps(state,ensure_ascii=False)))

def next_choice(state, seed, now=None):
    state['phase'] = 'choice'
    state['feedback_until'] = None
    state['choice'] = None
    state['response_until']=(time.time() if now is None else now)+180
    state['fearless_bans']=sorted({a['champion'] for game in state['sets'] for a in game.get('draft',[]) if a['action']=='pick'})
    state.pop('reply',None)
    state.pop('draft',None)
    for key in ('roster','swap_until','swap_version','role_options','draft_picks','draft_bans','draft_version'):state.pop(key,None)
    if state['chooser'] == 1:
        rng = random.Random(seed + len(state['sets']))
        category = rng.choice(tuple(CHOICES))
        state['choice'] = {'category':category,'value':rng.choice(CHOICES[category])}

def start(db, fixture, seed, best_of=3):
    if type(best_of) is not int or best_of not in (3,5):
        raise ValueError('unsupported series format')
    state = dict(score=[0,0], sets=[], chooser=0, feedback=[], best_of=best_of,fearless=True,autoplay=False)
    next_choice(state,seed)
    put(db,fixture,state)

def submit_choice(state, seed, category, value):
    if state['phase'] != 'choice' or category not in CHOICES or value not in CHOICES[category]:
        return False
    choice = state['choice']
    if state['chooser'] == 0:
        other = 'side' if category == 'priority' else 'priority'
        reply = random.Random(seed ^ (len(state['sets']) + 1)).choice(CHOICES[other])
        first,blue = resolve_choices(0,category,value,reply)
        state['choice'] = dict(category=category,value=value)
        state['reply'] = dict(category=other,value=reply)
    else:
        if choice['category'] == category:
            return False
        first,blue = resolve_choices(1,choice['category'],choice['value'],value)
        state['reply'] = dict(category=category,value=value)
    state.update(phase='draft_pending',first=first,blue=blue,response_until=None)
    return True

def tick(state,seed,now):
    """Authoritative deadlines; polling the API never extends a timeout."""
    changed=False
    if state['phase']=='draft' and now>=state.get('response_until',now+180) and not state.get('autoplay'):
        state['autoplay']=True;state['skip_viewing']=True;changed=True
    if state['phase']=='feedback' and (state.get('autoplay') or now>=state['feedback_until']):
        next_choice(state,seed,now);changed=True
    if state['phase']=='choice':
        if state.get('response_until') is None:
            state['response_until']=now+180;changed=True
        if state.get('autoplay') or now>=state['response_until']:
            choice=state.get('choice')
            category=('side' if choice['category']=='priority' else 'priority') if choice else 'priority'
            value=random.Random(seed+len(state['sets'])*37).choice(CHOICES[category])
            state['autoplay']=True;state['skip_viewing']=True
            submit_choice(state,seed,category,value);changed=True
    return changed

def prepare_draft(state,seed,kits,roles,now):
    if state['phase']!='draft_pending':raise ValueError('automatic draft unavailable')
    blocked=sorted({a['champion'] for game in state['sets'] for a in game.get('draft',[]) if a['action']=='pick'})
    state['fearless_bans']=blocked;state['fearless']=True
    draft=auto_draft(seed+len(state['sets']),kits,roles,state['first'],state['blue'],blocked,
                     max(0,state.get('best_of',3)-len(state['sets'])-1))
    state.update(phase='swap',draft=list(draft.actions),roster=[list(team) for team in draft.roster],
                 swap_until=now+(0 if state.get('autoplay') else 90),swap_version=0,role_options={name:list(kits[name].roles) for team in draft.roster for name in team})

def swap(state,first,second,version,now):
    roles=('TOP','JUNGLE','MID','ADC','SUPPORT')
    if state['phase']!='swap' or now>=state['swap_until']:raise ValueError('스왑 시간이 종료됐습니다. 경기 진행 화면을 확인하세요.')
    if type(version) is not int or version!=state['swap_version']:raise ValueError('다른 스왑이 먼저 적용됐습니다. 최신 배치를 확인하세요.')
    if first not in roles or second not in roles or first==second:raise ValueError('서로 다른 두 포지션을 선택해야 합니다.')
    a,b=roles.index(first),roles.index(second);side=state['blue'];roster=state['roster'][side]
    if second not in state['role_options'][roster[a]] or first not in state['role_options'][roster[b]]:
        raise ValueError('두 챔피언의 플레이 가능 포지션이 맞지 않아 스왑할 수 없습니다.')
    roster[a],roster[b]=roster[b],roster[a];state['swap_version']+=1

def complete_swap(state,now):
    """Manager can confirm player-champion assignment before timeout."""
    if state.get('phase')!='swap':
        raise ValueError('이미 스왑 단계가 종료됐습니다.')
    state['swap_until']=now
    state['phase']='ready'


def finish_swap(state,now):
    if state['phase']=='swap' and now>=state['swap_until']:
        state['phase']='ready';return True
    return False

def set_complete(state, result, draft, now):
    winner = draft.blue if result['winner'] == 0 else 1-draft.blue
    transition = after_set(state['score'],winner,now,state.get('best_of',3)//2+1)
    state['sets'].append(dict(result,club_winner=winner,first=draft.first,blue=draft.blue,
                              draft=list(draft.actions)))
    state['fearless_bans']=sorted({a['champion'] for game in state['sets'] for a in game.get('draft',[]) if a['action']=='pick'})
    state.update(transition)
    state['phase'] = 'finished' if transition['winner'] is not None else 'feedback'
    state['chooser'] = 1-winner
    if state['phase'] == 'finished':
        return dict(winner=transition['winner'], finished=True, score=state['score'], best_of=state.get('best_of',3),
                    sets=state['sets'], highlights=[clip for game in state['sets'] for clip in game['highlights']])
    return None
