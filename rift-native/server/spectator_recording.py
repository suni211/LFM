"""Bounded, atomically published spectator chunks from the actual engine state.

No outcome or future event is needed to view a chunk. Old highlight files remain
compatible with native clients. Position units use the engine's 512px terrain.
"""
import gzip
import json
from pathlib import Path

CHUNK_SECONDS=15
STEP=.4

def paths(directory,fixture,set_index):
    return Path(directory)/f'{fixture}-set-{set_index}'

def atomic_json(path,payload,compressed=False):
    temporary=path.with_suffix(path.suffix+'.tmp')
    opener=gzip.open if compressed else open
    kwargs=dict(encoding='utf-8')
    if compressed:kwargs['compresslevel']=1
    with opener(temporary,'wt',**kwargs) as out:json.dump(payload,out,ensure_ascii=False,separators=(',',':'))
    temporary.replace(path)

class SpectatorRecorder:
    def __init__(self,directory,fixture,set_index,blue=0):
        self.root=paths(directory,fixture,set_index);self.root.mkdir(parents=True,exist_ok=True)
        self.fixture=fixture;self.set_index=set_index;self.blue=blue
        self.highlights=[];self.frames=[];self.chunks=0;self.next_frame=0;self.event_cursor=0;self.known=set();self.units=[];self.last_time=0
        self.publish(False)
    def publish(self,complete):
        atomic_json(self.root/'manifest.json',dict(version=1,fixture=self.fixture,set=self.set_index,blue=self.blue,
            chunk_count=self.chunks,recorded_until=round(self.last_time,2),complete=complete,map_size=512,units=self.units,highlights=self.highlights))
    def record(self,match,final=False):
        if not final and match.t+.001<self.next_frame:return
        self.next_frame=match.t+STEP;self.last_time=match.t
        for u in match.units:
            if u.id not in self.known:
                self.known.add(u.id);self.units.append(dict(id=u.id,name=u.name,team=u.team,kind=u.kind,role=u.role,
                    player_id=getattr(u,'player_id',None),player_name=getattr(u,'player_name',None)))
        positions=[[u.id,round(u.pos[0],2),round(u.pos[1],2),round(100*u.hp/max(1,u.maxhp),1)] for u in match.alive if u.alive]
        players=[dict(id=u.id,level=u.level,kda=[u.kills,u.deaths,u.assists],cs=u.cs,gold=round(u.earned),items=list(u.items),
            hp=round(u.hp),maxhp=round(u.maxhp),mana=round(u.mana),maxmana=round(u.maxmana),alive=u.alive,
            respawn=max(0,round(u.dead_until-match.t)),rune=u.rune,summoners=list(u.summoners)) for u in match.players()]
        events=[dict(e) for e in match.events[self.event_cursor:] if e.get('type') in ('kill','structure','objective','victory','spell','summoner')]
        self.event_cursor=len(match.events)
        # Retain attack/projectile/area data without recomputing combat in JavaScript.
        effects=[dict(v) for v in match.visuals if v.get('until',0)>=match.t]
        areas=[{k:v[k] for k in ('kind','a','p','r','end') if k in v} for v in match.areas if v.get('end',0)>=match.t]
        wards=[{k:w[k] for k in ('p','team','end') if k in w} for w in match.wards if w.get('end',0)>=match.t]
        frame=[round(match.t,2),positions,players,events,effects,areas,wards]
        if self.frames and self.frames[-1][0]==frame[0]:self.frames[-1]=frame
        else:self.frames.append(frame)
        if final:
            from replay import clips
            self.highlights=[dict(start=c['start'],end=c['end']) for c in clips(match.events,match.t,self.units)]
        if self.frames[-1][0]-self.frames[0][0]>=CHUNK_SECONDS or final:self.flush(final)
    def flush(self,complete=False):
        if self.frames:
            atomic_json(self.root/f'{self.chunks}.json.gz',dict(version=1,frames=self.frames),True)
            self.frames=[];self.chunks+=1
        self.publish(complete)

def read_manifest(directory,fixture,set_index):
    target=paths(directory,fixture,set_index)/'manifest.json'
    return json.loads(target.read_text(encoding='utf-8')) if target.exists() else None
