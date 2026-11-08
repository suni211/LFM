import json,gzip,hashlib,sys,time,bisect,traceback
try:import orjson
except ImportError:orjson=None
from pathlib import Path
from engine import Match,DT
ROOT=Path(__file__).parent
def signature():
    import champion_catalog
    source=champion_catalog.ROOT/'champions.json'
    return hashlib.sha256(b'broadcast-korean-runes-fountain-stream-v2'+source.read_bytes()).hexdigest()[:16]
def snapshot(m):
    return dict(t=m.t,units=[[u.id,round(u.pos[0],2),round(u.pos[1],2),round(u.hp),round(u.maxhp),round(u.dead_until,1)] for u in (*m.persistent,*m.wave_units) if u.alive or u.kind in ('champion','boss','camp','tower','inhibitor','nexus')],
                players=[dict(id=u.id,name=u.name,team=u.team,role=u.role,hp=round(u.hp),maxhp=round(u.maxhp),mana=round(u.mana),level=u.level,k=u.kills,d=u.deaths,a=u.assists,cs=u.cs,gold=round(u.earned),items=list(u.items),damage=round(u.damage),intent=u.intent,target=u.target,respawn=u.dead_until,summoners=dict(u.summoners),rune=u.rune,rune_state={k:v for k,v in u.rune_state.items() if isinstance(k,str) and isinstance(v,(int,float,str,bool))}) for u in m.players()],
                effects=[dict(v) for v in m.visuals],missiles=[dict(v) for v in m.missiles],areas=[dict(a) for a in m.areas],dragons=[list(a) for a in m.dragons],grubs=list(m.grubs),element=m.element)
def clips(events,duration):
    candidates=[]
    for e in events:
        kind=e['type'];t=e['t'];ids=[];label='';pre=10;post=5
        if kind=='kill':
            ids=[e['killer'],e['victim']]+e['assists']
            label='갱킹' if e.get('gank') else '교전' if e['assists'] else '솔로 킬'
        elif kind=='objective':ids=[e['unit']];label={'Dragon':'드래곤 공략','Baron':'바론 공략','Grub':'유충 공략','Herald':'전령 공략'}.get(e['name'],e['name']);pre=12;post=3
        elif kind=='structure':ids=[e['unit']];label='포탑 공략' if 'inhibitor' not in e['name'] else '억제기 공략';pre=8;post=3
        elif kind=='victory':ids=[e['unit']];label='넥서스 공략';pre=30;post=0
        else:continue
        candidates.append(dict(start=max(0,t-pre),end=min(duration,t+post),label=label,ids=ids,anchors=[dict(t=t,p=e['p'],ids=ids,kind=kind,label=label)],kills=int(kind=='kill'),victory=kind=='victory'))
    candidates.sort(key=lambda c:c['start']);merged=[]
    for c in candidates:
        if merged and c['start']<=merged[-1]['end']+(25 if c['victory'] else 2):
            old=merged[-1];old['end']=max(old['end'],c['end']);old['kills']+=c['kills'];old['anchors']+=c['anchors'];old['ids']=list(dict.fromkeys(old['ids']+c['ids']))
            if c['victory']:old['victory']=True;old['label']='한타 → 넥서스 공략' if old['kills'] else c['label']
            elif old['kills']>=3:old['label']='한타'
        else:merged.append(c)
    return merged
def build(seed,path,mail=None,limit=None,roster=None,runes=None):
    source_signature=signature()
    m=Match(seed,roster) if roster is not None else Match(seed);frames=[snapshot(m)];ticks=0;nextprogress=0;started=time.perf_counter()
    if runes:
        from data import RUNE_NAMES
        for u in m.players():
            key=runes.get(str(u.team)+':'+u.role)
            if key in RUNE_NAMES:u.rune=key
        frames[0]=snapshot(m)
    sent_frames=sent_meta=sent_events=0
    def stream():
        nonlocal sent_frames,sent_meta,sent_events
        if mail:
            meta=[dict(id=u.id,name=u.name,kind=u.kind,team=u.team,role=u.role,lane=u.lane,home=u.home,owner=u.owner,minor=u.minor,reach=u.reach) for u in m.units[sent_meta:]]
            mail.put(dict(type='live',frames=frames[sent_frames:],meta=meta,events=[e for e in m.events[sent_events:] if e['type']!='attack']))
            sent_frames=len(frames);sent_meta=len(m.units);sent_events=len(m.events)
    stream()
    while m.winner is None and (limit is None or m.t<limit):
        m.step();ticks+=1
        if ticks%2==0:frames.append(snapshot(m))
        if mail and m.t>=nextprogress:stream();nextprogress=m.t+10
    if frames[-1]['t']!=m.t:frames.append(snapshot(m))
    stream()
    meta=[dict(id=u.id,name=u.name,kind=u.kind,team=u.team,role=u.role,lane=u.lane,home=u.home,owner=u.owner,minor=u.minor,reach=u.reach) for u in m.units]
    result=m.result();result['compute_seconds']=round(time.perf_counter()-started,2)
    if signature()!=source_signature:raise RuntimeError('Source changed during match generation; rerun with a consistent engine')
    data=dict(signature=source_signature,seed=seed,frames=frames,meta=meta,events=[e for e in m.events if e['type']!='attack'],clips=clips(m.events,m.t),result=result)
    data['attack_audit']=dict(count=sum(e['type']=='attack' for e in m.events),violations=sum(e['d']>e['reach']+.001 for e in m.events if e['type']=='attack'))
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    packed=orjson.dumps(data) if orjson else json.dumps(data,separators=(',',':')).encode('utf-8')
    with gzip.open(p.with_suffix('.tmp'),'wb',compresslevel=1) as f:f.write(packed)
    p.with_suffix('.tmp').replace(p)
    if mail:mail.put(dict(type='done',path=str(p)))
    return data
def load(path):
    with gzip.open(path,'rb') as f:packed=f.read()
    r=orjson.loads(packed) if orjson else json.loads(packed)
    if r.get('signature')!=signature():raise ValueError('Old match cache')
    return r
def worker(seed,path,mail,roster=None,runes=None):
    try:build(seed,path,mail,roster=roster,runes=runes)
    except Exception:mail.put(dict(type='error',message=traceback.format_exc()))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=1);p.add_argument('--limit',type=float,help='Optional diagnostics cutoff');args=p.parse_args()
    r=build(args.seed,ROOT/'runs'/f'match-{args.seed}.json.gz',limit=args.limit)
    print(json.dumps(dict(result=r['result'],clips=len(r['clips']),watch_seconds=sum(c['end']-c['start'] for c in r['clips']),audit=r['attack_audit']),ensure_ascii=False,indent=2))
