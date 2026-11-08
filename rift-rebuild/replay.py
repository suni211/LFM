import json,gzip,hashlib,sys,time,bisect,traceback
from pathlib import Path
from engine import Match,DT
ROOT=Path(__file__).parent
def signature():
    if not (ROOT/'engine.py').exists():
        from version import SIGNATURE
        return SIGNATURE
    return hashlib.sha256(b''.join((ROOT/f).read_bytes() for f in ('engine.py','data.py','terrain.py','replay.py'))).hexdigest()[:16]
def snapshot(m):
    return dict(t=m.t,units=[[u.id,round(u.pos[0],2),round(u.pos[1],2),round(u.hp),round(u.maxhp),round(u.dead_until,1)] for u in m.units if u.alive or u.kind in ('champion','boss','camp','tower','inhibitor','nexus')],
                players=[dict(id=u.id,name=u.name,team=u.team,role=u.role,hp=round(u.hp),maxhp=round(u.maxhp),mana=round(u.mana),level=u.level,k=u.kills,d=u.deaths,a=u.assists,cs=u.cs,gold=round(u.earned),items=list(u.items),damage=round(u.damage),intent=u.intent,target=u.target,respawn=u.dead_until,summoners=dict(u.summoners),rune=u.rune) for u in m.players()],
                effects=[dict(v) for v in m.visuals],missiles=[dict(v) for v in m.missiles],areas=[dict(a) for a in m.areas],dragons=[list(a) for a in m.dragons],grubs=list(m.grubs),herald=list(m.herald),barons=list(m.barons),element=m.element)
def clips(events,duration,meta=()):
    teams={u['id']:u['team'] for u in meta}
    gains=[e for e in events if e['type'] in ('kill','objective','structure','victory')]
    dragons={}
    key_objectives=set()
    for e in gains:
        if e['type']!='objective':continue
        if e['name']=='Dragon' and e.get('element')!='elder':
            team=e.get('team')
            dragons[team]=dragons.get(team,0)+1
            if dragons[team]==4:key_objectives.add(id(e))
        elif e['name']=='Baron' or e.get('element')=='elder':
            key_objectives.add(id(e))

    def team_of(event):
        return teams.get(event['killer']) if event['type']=='kill' else event.get('team')

    def linked(a,b,seconds,radius):
        team_a,team_b=team_of(a),team_of(b)
        return (abs(a['t']-b['t'])<=seconds and
                (team_a is None or team_b is None or team_a==team_b) and
                sum((x-y)**2 for x,y in zip(a['p'],b['p']))<=radius**2)

    featured=[]
    for e in gains:
        kind=e['type']
        if kind in ('kill','victory') or id(e) in key_objectives:
            featured.append(e)
        elif kind=='structure' and ('inhibitor' in e['name'] or e['name']=='Nexus tower'):
            featured.append(e)
        elif (kind=='structure' or e['name']!='Grub') and any(
            other is not e and (other['type']=='kill' or kind=='structure' and other['type']=='structure')
            and linked(e,other,22,95) for other in gains
        ):
            featured.append(e)
    for e in events:
        if e['type']=='fight' and len(set(e['ids']))>=6 and any(
            -2<=gain['t']-e['t']<=16 and linked(e,gain,16,65) for gain in featured
        ):
            featured.append(e)
    featured.sort(key=lambda e:e['t'])
    candidates=[]
    for e in featured:
        kind=e['type'];t=e['t'];ids=[];label='';pre=10;post=5
        if kind=='kill':
            ids=[e['killer'],e['victim']]+e['assists']
            label='갱킹' if e.get('gank') else '교전' if e['assists'] else '솔로 킬'
        elif kind=='fight' and len(set(e['ids']))>=6:ids=e['ids'];label='한타';pre=5;post=4
        elif kind=='objective':ids=[e['unit']];label={'Dragon':'드래곤 공략','Baron':'바론 공략','Grub':'유충 공략','Herald':'전령 공략'}[e['name']];pre=8;post=3
        elif kind=='structure':ids=[e['unit']];label='포탑 공략' if 'inhibitor' not in e['name'] else '억제기 공략';pre=8;post=3
        elif kind=='victory':ids=[e['unit']];label='넥서스 공략';pre=30;post=0
        else:continue
        candidates.append(dict(start=max(0,t-pre),end=min(duration,t+post),label=label,ids=ids,anchors=[dict(t=t,p=e['p'],ids=ids,kind=kind,label=label)],kills=int(kind=='kill'),victory=kind=='victory'))
    candidates.sort(key=lambda c:c['start']);merged=[]
    for c in candidates:
        if merged and c['start']<=merged[-1]['end']+(25 if c['victory'] else 2):
            old=merged[-1];old['end']=max(old['end'],c['end']);old['kills']+=c['kills'];old['anchors']+=c['anchors'];old['ids']=list(dict.fromkeys(old['ids']+c['ids']))
            if c['victory']:old['victory']=True;old['label']='한타 → 넥서스 공략' if old['label']=='한타' else c['label']
            elif c['label']=='한타':old['label']='한타'
        else:merged.append(c)
    for clip in merged:clip['anchors'].sort(key=lambda anchor:anchor['t'])
    return merged
def build(seed,path,mail=None,limit=None,roster=None,names=None):
    source_signature=signature()
    m=Match(seed,roster=roster) if roster else Match(seed);frames=[snapshot(m)];ticks=0;nextprogress=0;started=time.perf_counter()
    while m.winner is None and (limit is None or m.t<limit):
        m.step();ticks+=1
        if ticks%2==0:frames.append(snapshot(m))
        if mail and m.t>=nextprogress:mail.put(dict(type='progress',t=m.t));nextprogress=m.t+30
    if frames[-1]['t']!=m.t:frames.append(snapshot(m))
    meta=[dict(id=u.id,name=u.name,kind=u.kind,team=u.team,role=u.role,lane=u.lane,home=u.home,owner=u.owner,minor=u.minor,reach=u.reach) for u in m.units]
    result=m.result();result['compute_seconds']=round(time.perf_counter()-started,2)
    if signature()!=source_signature:raise RuntimeError('Source changed during match generation; rerun with a consistent engine')
    data=dict(signature=source_signature,seed=seed,frames=frames,meta=meta,events=[e for e in m.events if e['type']!='attack'],clips=clips(m.events,m.t,meta),result=result)
    if names:data['names']=list(names)
    data['attack_audit']=dict(count=sum(e['type']=='attack' for e in m.events),violations=sum(e['d']>e['reach']+.001 for e in m.events if e['type']=='attack'))
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    with gzip.open(p.with_suffix('.tmp'),'wt',encoding='utf-8',compresslevel=2) as f:json.dump(data,f,separators=(',',':'))
    p.with_suffix('.tmp').replace(p)
    if mail:mail.put(dict(type='done',path=str(p)))
    return data
def load(path):
    with gzip.open(path,'rt',encoding='utf-8') as f:r=json.load(f)
    if r.get('signature')!=signature():raise ValueError('Old match cache')
    return r
def worker(seed,path,mail,roster=None,names=None):
    try:build(seed,path,mail,roster=roster,names=names)
    except Exception:mail.put(dict(type='error',message=traceback.format_exc()))
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=1);p.add_argument('--limit',type=float,help='Optional diagnostics cutoff');args=p.parse_args()
    r=build(args.seed,ROOT/'runs'/f'match-{args.seed}.json.gz',limit=args.limit)
    print(json.dumps(dict(result=r['result'],clips=len(r['clips']),watch_seconds=sum(c['end']-c['start'] for c in r['clips']),audit=r['attack_audit']),ensure_ascii=False,indent=2))
