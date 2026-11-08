"""Select causally connected highlights from recorded simulation events."""
import math

def clips(events,duration,meta=()):
    teams={unit['id']:unit['team'] for unit in meta}
    selected=[]
    for event in events:
        kind=event['type']
        if kind not in ('kill','objective','structure','victory'):continue
        t=event['t'];ids=[];team=event.get('team')
        if kind=='kill':
            ids=[event['killer'],event['victim'],*event.get('assists',[])];team=teams.get(event['killer'])
            label='한타' if len(event.get('assists',[]))>=2 else '갱킹' if event.get('gank') else '솔로 킬'
            before,after=10,9
        elif kind=='victory':ids=[event['unit']];label='넥서스 파괴';before,after=30,0
        elif kind=='structure':ids=[event['unit']];label='포탑 · 구조물 파괴';before,after=8,5
        else:ids=[event['unit']];label=event.get('name','주요 오브젝트');before,after=10,7
        p=event.get('p',(256,256))
        selected.append(dict(start=max(0,t-before),end=min(duration,t+after),label=label,team=team,
            anchors=[dict(t=t,p=p,ids=list(dict.fromkeys(ids)),kind=kind)],victory=kind=='victory'))
    selected.sort(key=lambda clip:(clip['start'],clip['end']))
    merged=[]
    for clip in selected:
        old=merged[-1] if merged else None
        connected=bool(old and (clip['start']<=old['end'] or clip['victory'] and clip['team']==old['team'] and clip['start']-old['end']<=35 and old['label'] in ('한타','솔로 킬','갱킹','포탑 · 구조물 파괴')))
        if connected:
            old['end']=max(old['end'],clip['end']);old['anchors']+=clip['anchors']
            if clip['victory']:old['label']='교전 → 넥서스 공략';old['victory']=True
            elif clip['label']=='한타':old['label']='한타'
        else:merged.append(clip)
    for clip in merged:clip['anchors'].sort(key=lambda event:event['t'])
    return merged
