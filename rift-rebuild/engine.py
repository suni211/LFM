"""Fixed-step, seeded match simulation. No renderer, camera, or scripted kill events."""
from dataclasses import dataclass,field
import random,math
from collections import defaultdict,Counter
from data import *
from terrain import Terrain,distance
DT=.2
STRUCTURES={'tower','inhibitor','nexus'}
@dataclass
class Unit:
    id:int;name:str;team:int;kind:str;pos:tuple;hp:float;maxhp:float;ad:float;reach:float
    role:str='';lane:str='';home:tuple=();speed:float=12.;armor:float=30;mr:float=30;ap:float=0
    dead_until:float=0;expires:float=0;owner:int=-1;depth:int=0;root:int=-1;minor:bool=False
    level:int=1;xp:float=0;gold:float=0;earned:float=0;cs:int=0;kills:int=0;deaths:int=0;assists:int=0
    mana:float=450;maxmana:float=450;nextattack:float=0;cool:list=field(default_factory=lambda:[0.]*4)
    items:list=field(default_factory=list);path:list=field(default_factory=list);pathgoal:tuple=()
    effects:dict=field(default_factory=dict);buffs:dict=field(default_factory=dict);attackers:dict=field(default_factory=dict)
    shield:float=0;shielduntil:float=0;cc:float=0;rootuntil:float=0;silence:float=0;blind:float=0;immune:float=0
    spellshield:float=0;guard:float=0;guarduntil:float=0;haste:float=0;hasteuntil:float=0
    lastdamage:float=-999;recall:float=0;intent:str='배치';target:int=-1;decision:float=0;goal:tuple=()
    aggression:float=.5;mechanics:float=.8;damage:float=0;attacks:int=0;channel:dict=field(default_factory=dict)
    ward:float=0;ward_interval:float=90;proc:dict=field(default_factory=dict)
    quest:float=0;gank_until:float=0;gank_ready:float=0
    summoners:dict=field(default_factory=dict)
    rune:str='';rune_state:dict=field(default_factory=dict)
    @property
    def alive(self):return self.hp>0

class Match:
    def __init__(self,seed=1,roster=ROSTER):
        self.seed=seed;self.rng=random.Random(seed);self.terrain=Terrain();self.t=0.;self.winner=None
        self.units=[];self.structures=[];self.champions=[];self.persistent=[];self.wave_units=[];self.events=[];self.visuals=[];self.missiles=[];self.areas=[];self.wards=[];self.camps=[]
        self.alive=[];self.buckets={};self.nextwave=65;self.wave=0;self.nextmacro=0;self.plans=[{},{}];self.defenders=[{},{}];self.objective_retry=[{},{}]
        self.lanes_started=set();self.lane_waves={};self.next_wave_read=0
        self.dragons=[[],[]];self.grubs=[0,0];self.elements=self.rng.sample(['infernal','ocean','cloud','mountain','hextech','chemtech'],6);self.element=self.elements[0]
        self.herald=[0,0];self.barons=[0,0];self.fights=[];self.lastseen=[{},{}];self.sight={};self.vision=[0,0];self.nextfight=0
        if len(roster)!=2 or any(len(team)!=5 for team in roster):raise ValueError('Two teams of five required')
        if len(set(sum((list(team) for team in roster),[])))!=10:raise ValueError('Duplicate champion')
        for team in (0,1):
            for role,name in zip(ROLES,roster[team]):
                c=KITS[name]
                if role not in c.roles:raise ValueError(f'{name}: {role}')
                u=self.add(name,team,'champion',SPAWNS[team],c.hp,c.attack,map_range(c.reach));u.role=role
                u.lane={'TOP':'TOP','MID':'MID','ADC':'BOT','SUPPORT':'BOT','JUNGLE':'MID'}[role]
                u.aggression=self.rng.uniform(.3,.8);u.mechanics=self.rng.uniform(.7,.95)
                roll=random.Random(seed*61+team*11+ROLES.index(role)).random()
                if role=='TOP':pair=('Flash','Teleport')
                elif role=='JUNGLE':pair=('Flash','Smite')
                elif role=='MID':pair=('Flash','Dot' if roll<.25 and u.aggression>.55 else 'Teleport')
                elif role=='ADC':pair=('Flash','Haste' if roll<.25 else 'Barrier')
                else:pair=('Flash',('Heal','Exhaust','Dot')[int(roll*3)])
                u.summoners=dict.fromkeys(pair,0.)
                u.rune=KEYSTONES[name]
            for lane in ('TOP','MID','BOT'):
                for depth,raw in enumerate(TOWERS[team][lane]):
                    u=self.add(lane+f' T{depth+1}',team,'tower',project(*raw),(4200,4200,4500)[depth],(155,170,185)[depth],TOWER_RANGE);u.lane=lane;u.depth=depth
                u=self.add(lane+' inhibitor',team,'inhibitor',project(*INHIB[team][lane]),3400,0,0);u.lane=lane
            for raw in BASE_TOWERS[team]:
                u=self.add('Nexus tower',team,'tower',project(*raw),3600,190,TOWER_RANGE);u.lane='BASE'
            self.add('Nexus',team,'nexus',NEXUS[team],4500,0,0)
        for team in (0,1):
            for name,raw in CAMP[team].items():
                members=[];count={'Wolves':3,'Raptors':6,'Krugs':2}.get(name,1)
                for i in range(count):
                    home=project(*raw);angle=i*math.tau/max(1,count)
                    p=home if i==0 else (home[0]+math.cos(angle)*7,home[1]+math.sin(angle)*7)
                    u=self.add(name, -1,'camp',p,1000 if i==0 else 220,32 if i==0 else 12,12)
                    u.minor=i>0;u.hp=0;u.dead_until=90;u.speed=10;members.append(u.id)
                for i in members:self.units[i].root=members[0]
                self.camps.append(dict(id=members[0],members=members,team=team,delay=300 if name in ('Blue','Red') else 150,clears=0))
        for name,hp,start in (('Dragon',6500,300),('Baron',11000,1200),('Grub',1800,360),('Herald',6500,840)):
            members=[]
            for i in range(3 if name=='Grub' else 1):
                p=PITS['Baron' if name=='Herald' else name]
                if name=='Grub':p=(p[0]+(i-1)*7,p[1]+i%2*6)
                attack={'Dragon':42,'Baron':85,'Grub':14,'Herald':46}[name]
                u=self.add(name,-1,'boss',p,hp,attack,16);u.hp=0;u.dead_until=start;u.speed=8;members.append(u.id)
            for i in members:self.units[i].root=members[0]
            self.camps.append(dict(id=members[0],members=members,team=-1,delay=300 if name=='Dragon' else 360 if name=='Baron' else 240,clears=0))
        self.lanes={}
        for lane in ('TOP','MID','BOT'):
            blue=[self.terrain.snap(project(*p)) for p in reversed(TOWERS[0][lane])]
            red=[self.terrain.snap(project(*p)) for p in TOWERS[1][lane]]
            corner=[(65,65)] if lane=='TOP' else [(448,448)] if lane=='BOT' else [(256,256)]
            self.lanes[lane]=[self.terrain.snap(SPAWNS[0])]+blue+[self.terrain.snap(p) for p in corner]+red+[self.terrain.snap(SPAWNS[1])]
        self.reindex();self.log('start',seed=seed)

    def add(self,name,team,kind,pos,hp,ad,reach):
        p=self.terrain.snap(pos);u=Unit(len(self.units),name,team,kind,p,hp,hp,ad,reach,home=p)
        self.units.append(u)
        (self.wave_units if kind in ('minion','pet') else self.persistent).append(u)
        if kind in STRUCTURES:self.structures.append(u)
        if kind=='champion':self.champions.append(u)
        return u
    def log(self,event,**data):self.events.append(dict(t=round(self.t,2),type=event,**data))
    def players(self,team=None):return [u for u in self.champions if team is None or u.team==team]
    def nearby(self,p,r):
        size=64;out=[]
        for x in range(int((p[0]-r)//size),int((p[0]+r)//size)+1):
            for y in range(int((p[1]-r)//size),int((p[1]+r)//size)+1):
                out.extend(u for u in self.buckets.get((x,y),()) if u.alive and distance(u.pos,p)<=r)
        return out
    def reindex(self):
        # Preserve historical unit IDs for projectiles, statistics and replay.
        # Dead waves do not respawn and should not be scanned every tick.
        self.wave_units=[u for u in self.wave_units if u.alive or u.dead_until]
        self.alive=[u for u in self.persistent if u.alive]+[u for u in self.wave_units if u.alive]
        self.buckets=defaultdict(list);self.sight={}
        for u in self.alive:self.buckets[(int(u.pos[0]//64),int(u.pos[1]//64))].append(u)
    def ward_sees(self,team,pos):
        return any(w['team']==team and w['end']>self.t and distance(w['p'],pos)<65
                   and self.terrain.sight(w['p'],pos) for w in self.wards)

    def visible(self,team,u):
        if u.team==team or u.kind in STRUCTURES:return True
        key=(team,u.id)
        if key not in self.sight:
            self.sight[key]=self.vision[team]>self.t or any(a.team==team and self.terrain.sight(a.pos,u.pos) for a in self.nearby(u.pos,135)) or self.ward_sees(team,u.pos)
        return self.sight[key]
    def move(self,u,p,dt=DT):
        if u.cc>self.t or u.rootuntil>self.t or u.channel or self.buff(u,'stasis'):return
        slow=u.effects.get('slow',(0,0));speed=u.speed
        surge=self.buff(u,'stormraider')
        if slow[0]>self.t:u.speed*=1-slow[1]*(.5 if surge else 1)
        if surge:u.speed*=1.3 if u.reach>map_range(175) else 1.4
        if u.hasteuntil>self.t:u.speed*=1+min(.5,u.haste*.3)
        if self.buff(u,'ghost'):u.speed*=1.28
        self.terrain.move(u,p,dt);u.speed=speed
    def buff(self,u,key):return u.buffs.get(key,0)>self.t
    def heal(self,u,amount):
        if u.alive:u.hp=min(u.maxhp,u.hp+amount*(.6 if self.buff(u,'grievous') else 1))
    def earn(self,u,gold,xp=0):
        if u.kind!='champion':return
        u.gold+=gold;u.earned+=gold;u.xp+=xp
        while u.level<18 and u.xp>=180+u.level*100:
            u.xp-=180+u.level*100;u.level+=1;u.maxhp+=90;u.hp+=90;u.ad+=3;u.armor+=3;u.maxmana+=30;u.mana+=30
            if u.name=='Kayle' and u.level in (6,16):u.reach=map_range(525 if u.level==6 else 625)
            if u.name=='Tristana':u.reach=map_range(KITS[u.name].reach+8*(u.level-1))
    def open_structure(self,u):
        if u.kind=='tower':
            if u.lane=='BASE':return any(v.kind=='inhibitor' and v.team==u.team and not v.alive for v in self.structures)
            return not any(v.kind=='tower' and v.team==u.team and v.lane==u.lane and v.depth<u.depth and v.alive for v in self.structures)
        if u.kind=='inhibitor':return not any(v.kind=='tower' and v.team==u.team and v.lane==u.lane and v.alive for v in self.structures)
        if u.kind=='nexus':return not any(v.kind=='tower' and v.team==u.team and v.lane=='BASE' and v.alive for v in self.structures) and any(v.kind=='inhibitor' and v.team==u.team and not v.alive for v in self.structures)
        return True
    def rune_ready(self,u):
        return self.t>=u.rune_state.get('ready',0)

    def rune_used(self,u,cooldown,target):
        u.rune_state['ready']=self.t+cooldown
        self.log('rune',unit=u.id,rune=u.rune,target=target.id,p=target.pos)

    def rune_hit(self,a,b,actual,hit_kind,source):
        state=a.rune_state
        rune=a.rune
        extra=0
        if rune=='tempo' and hit_kind=='auto':
            stacks=state.get('stacks',0) if self.buff(a,'tempo') else 0
            state['stacks']=min(6,stacks+1)
            a.buffs['tempo']=self.t+6
            if stacks==6:extra=8+a.level
            elif stacks==5:self.rune_used(a,0,b)
        elif rune=='pta' and hit_kind=='auto' and not self.buff(a,'pta'):
            hits,expires=state.get(b.id,(0,0))
            hits=hits+1 if self.t<expires else 1
            state[b.id]=(hits,self.t+4)
            if hits==3:
                state.pop(b.id)
                a.buffs['pta']=self.t+6
                extra=35+5*a.level
                self.rune_used(a,0,b)
        elif rune=='electrocute' and self.rune_ready(a):
            hits=state.setdefault(b.id,{})
            for key in list(hits):
                if self.t-hits[key]>3:del hits[key]
            # A single cast or multi-hit packet only contributes once.
            hits[source]=self.t
            if len(hits)>=3:
                hits.clear()
                extra=35+4*a.level+.1*a.ap
                self.rune_used(a,20,b)
        elif rune=='stormraider' and self.rune_ready(a):
            hits=[(t,d) for t,d in state.get(b.id,()) if self.t-t<=3]
            hits.append((self.t,actual))
            state[b.id]=hits
            if sum(d for _,d in hits)>=b.maxhp*.25:
                state.pop(b.id)
                a.buffs['stormraider']=self.t+3
                self.rune_used(a,20-(a.level-1)*10/17,b)
        elif rune=='grasp' and hit_kind=='auto' and self.rune_ready(a) and self.t-state.get('combat_start',self.t)>=4:
            extra=a.maxhp*.035
            self.heal(a,a.maxhp*.013)
            a.maxhp+=5
            a.hp+=5
            self.rune_used(a,4,b)
        elif rune=='hail' and hit_kind=='auto':
            if self.rune_ready(a):
                state['stacks']=3
                a.buffs['hail']=self.t+3
                self.rune_used(a,12,b)
            if self.buff(a,'hail') and state.get('stacks',0)>0:
                state['stacks']-=1
                self.damage(a,b,4+a.level,true=True,spell=True)
        elif rune=='aery' and self.rune_ready(a):
            extra=8+2*a.level+.05*a.ap
            self.rune_used(a,3,b)
        elif rune=='comet' and hit_kind=='ability' and self.rune_ready(a):
            self.areas.append(dict(kind='comet',a=a.id,p=b.pos,r=map_range(155),power=25+3*a.level+.1*a.ap,end=self.t+1,next=self.t+.65,cc=0))
            self.rune_used(a,18-a.level*.4,b)
        elif rune=='deathfire' and hit_kind=='ability':
            duration=2 if source[0] in ('aoe','zone','counter','channel') else 4
            key=f'deathfire:{a.id}'
            expiry,next_tick,start=b.effects.get(key,(0,self.t+1,self.t))
            if expiry<self.t:next_tick,start=self.t+1,self.t
            b.effects[key]=(max(expiry,self.t+duration),next_tick,start)
        if extra:
            self.damage(a,b,extra,magic=rune in ('grasp','aery') or KITS[a.name].style=='ap',spell=True)

    def damage(self,a,b,power,magic=False,true=False,spell=False,hit_kind=None,source=None):
        if self.winner is not None or not b.alive or b.immune>self.t:return 0
        if b.kind in STRUCTURES:
            if not self.open_structure(b):return 0
            if b.kind=='tower' and not any(u.team==a.team and u.kind=='minion' for u in self.nearby(b.pos,b.reach+8)):power*=.2
            if b.kind=='tower' and a.kind=='minion':power*=.84 if a.name=='Cannon' else .5
            if b.kind=='tower' and self.buff(b,'early_siege_guard'):power*=.30
            if b.kind=='tower' and a.team in (0,1):
                escort=sum(v.team==a.team and v.kind=='champion' for v in self.nearby(b.pos,43))
                if escort<3:power*=.48 if escort==2 else .28
            if a.team in (0,1):power*=1+.025*self.grubs[a.team]
            if a.kind=='minion' and any(self.buff(p,'baron') for p in self.players(a.team) if p.alive and distance(p.pos,a.pos)<45):power*=1.65
        if spell and b.spellshield>self.t:b.spellshield=0;self.log('block',unit=b.id);return 0
        if not spell and (a.blind>self.t or self.buff(b,'dodge')):return 0
        if b.kind=='champion' and hit_kind and self.buff(a,'pta'):
            power*=1.08
            a.buffs['pta']=self.t+6
        resist=(b.mr if magic else b.armor)+(35 if self.buff(b,'aftershock') else 0)
        if a.kind=='champion' and b.kind=='minion':power*=1.7
        if a.kind=='tower' and b.kind=='minion':power=max(power,b.maxhp*(.22 if b.name in ('Cannon','Super') else .48))
        if a.kind=='minion' and b.kind in STRUCTURES:power*=.4
        if not true:power*=100/(100+max(0,resist))
        if a.role=='JUNGLE' and b.kind in ('camp','boss') and not true:power*=1.45
        if b.guarduntil>self.t:power*=1-b.guard
        if a.kind=='minion' and b.kind=='champion':power*=.35
        if a.kind=='tower' and b.kind=='champion':
            previous,count,until=a.proc.get('tower_focus',(-1,0,0))
            count=min(3,count+1) if previous==b.id and self.t<until else 0
            a.proc['tower_focus']=(b.id,count,self.t+3)
            power*=1+.30*count
        if self.buff(a,'exhaust') and not true:power*=.65
        if b.shielduntil>self.t:
            absorb=min(b.shield,power);b.shield-=absorb;power-=absorb
        actual=min(b.hp,max(0,power));b.hp-=actual;b.lastdamage=self.t;b.recall=0;b.attackers[a.id]=self.t
        owner=self.units[a.owner] if a.kind=='pet' else a
        if b.kind=='champion' and owner.kind=='champion':
            owner.damage+=actual
            if owner.intent=='갱킹':owner.proc['gank_hit']=self.t
        if b.kind in ('camp','boss'):
            cfg=next(c for c in self.camps if b.id in c['members'])
            for i in cfg['members']:
                if self.units[i].alive:self.units[i].attackers[a.id]=self.t
        self.visuals.append(dict(t=self.t,until=self.t+.35,kind='impact',a=a.id,b=b.id,p=b.pos,value=round(actual),magic=magic))
        if a.kind=='champion':
            if 3153 in a.items and not spell:self.heal(a,actual*.1)
            if a.name=='Warwick':self.heal(a,actual*.1)
            if 3033 in a.items:b.buffs['grievous']=self.t+3
        if actual and b.kind=='champion' and owner.kind=='champion' and self.t>=self.nextfight:
            fighters=[u for u in self.nearby(b.pos,55) if u.kind=='champion']
            if all(sum(u.team==team for u in fighters)>=3 for team in (0,1)):
                active=set()
                for fighter in fighters:
                    for i,t in fighter.attackers.items():
                        if self.t-t<=3 and self.units[i].kind=='champion' and self.units[i].team!=fighter.team:
                            active.update((fighter.id,i))
                if all(sum(u.team==team and u.id in active for u in fighters)>=2 for team in (0,1)):
                    self.log('fight',ids=[u.id for u in fighters],p=b.pos)
                    self.nextfight=self.t+25
        for champion in (a,b):
            if champion.rune=='grasp':
                state=champion.rune_state
                if self.t-state.get('last_combat',-999)>4:state['combat_start']=self.t
                state['last_combat']=self.t
        if b.hp<=0:self.die(owner,b)
        elif hit_kind and a.alive and b.kind=='champion' and a.rune:
            self.rune_hit(a,b,actual,hit_kind,source)
        return actual
    def die(self,a,b):
        self.log('death',unit=b.id,killer=a.id,kind=b.kind,p=b.pos)
        if b.kind=='champion':
            b.deaths+=1;b.dead_until=self.t+10+b.level*2.8;b.channel={};b.recall=0
            contributors=[self.units[i] for i,t in b.attackers.items() if self.t-t<10 and self.units[i].kind=='champion' and self.units[i].team!=b.team]
            killer=a if a.kind=='champion' else max(contributors,key=lambda u:b.attackers[u.id],default=None)
            if killer:
                killer.kills+=1;self.earn(killer,300,200);assist=[u for u in contributors if u.id!=killer.id]
                for u in assist:u.assists+=1;self.earn(u,150/max(1,len(assist)),100)
                gank=any(u.role=='JUNGLE' and self.t-u.proc.get('gank_hit',-999)<10 for u in (killer,*assist))
                self.log('kill',killer=killer.id,victim=b.id,assists=[u.id for u in assist],p=b.pos,gank=gank)
            if b.name=='Sion':
                pet=self.add('최후의 영광',b.team,'pet',b.pos,b.maxhp*.45,b.ad*1.4,20);pet.owner=b.id;pet.expires=self.t+7
        elif b.kind=='minion':
            friends=[u for u in self.nearby(b.pos,140) if u.kind=='champion' and u.team==1-b.team]
            xp={'Melee':62,'Caster':31,'Cannon':75,'Super':75}[b.name]
            share=(1,.65,.433,.325,.26)[min(5,len(friends))-1]
            for u in friends:self.earn(u,0,xp*share)
            if a.kind=='champion':
                gold=20 if b.name=='Melee' else 14 if b.name=='Caster' else 50+int(self.t//90)
                a.cs+=1;self.earn(a,gold)
                if a.role in ('TOP','MID','ADC') and a.lane==b.lane:a.quest=min(100,a.quest+1)
        elif b.kind in ('camp','boss'):
            cfg=next(c for c in self.camps if b.id in c['members']);b.dead_until=0
            if a.kind=='champion':
                a.cs+=1;self.earn(a,15 if b.minor else 100,28 if b.minor else 155)
                if a.role=='JUNGLE' and not b.minor:a.quest=min(100,a.quest+5)
            if b.name=='Grub' and a.team in (0,1):self.grubs[a.team]+=1
            if b.kind=='boss' and a.team in (0,1):
                self.log('objective',unit=b.id,name=b.name,team=a.team,element=self.element,p=b.pos)
                for u in self.players(a.team):self.earn(u,80,80)
                if b.name=='Dragon':
                    self.dragons[a.team].append(self.element)
                    self.element='elder' if max(map(len,self.dragons))>=4 else self.elements[min(2,sum(map(len,self.dragons)))]
                if b.name=='Herald':self.herald[a.team]+=1;a.buffs['herald']=self.t+240
                if b.name=='Baron':
                    self.barons[a.team]+=1
                    for u in self.players(a.team):u.buffs['baron']=self.t+180
            if all(not self.units[i].alive for i in cfg['members']):
                cfg['clears']+=1;allow=b.name not in ('Grub','Herald')
                for i in cfg['members']:self.units[i].dead_until=self.t+cfg['delay'] if allow else 0
                self.log('camp_clear',root=cfg['id'],team=a.team)
        elif b.kind in ('tower','inhibitor'):
            if b.kind=='inhibitor':b.dead_until=self.t+300
            elif self.t<840 and b.lane!='BASE':
                for tower in self.structures:
                    if tower.kind=='tower' and tower.team==b.team and tower.lane==b.lane and tower.depth==b.depth+1 and tower.alive:
                        tower.buffs['early_siege_guard']=self.t+90
                        break
            for u in self.players(1-b.team):self.earn(u,150,50)
            self.log('structure',unit=b.id,team=1-b.team,p=b.pos,name=b.name)
        elif b.kind=='nexus':self.winner=1-b.team;self.log('victory',team=self.winner,unit=b.id,p=b.pos)
    def attack(self,a,b):
        # Every attack, including tower and monster attacks, must satisfy range
        # and terrain line-of-sight at the moment it is launched.
        if not a.alive or not b.alive or self.t<a.nextattack or a.cc>self.t or a.channel:return False
        if distance(a.pos,b.pos)>a.reach or not self.terrain.sight(a.pos,b.pos):return False
        if a.kind==b.kind=='minion' and a.lane==b.lane and a.team!=b.team:
            self.lanes_started.add(a.lane)
        rune_speed=a.rune_state.get('stacks',0)*(.04 if a.reach>map_range(175) else .06) if self.buff(a,'tempo') else 0
        if a.rune=='hail' and b.kind=='champion' and (self.rune_ready(a) or self.buff(a,'hail') and a.rune_state.get('stacks',0)>0):
            rune_speed=1.2
        a.nextattack=self.t+1.25/(1+a.level*.02+(.5 if a.hasteuntil>self.t else 0)+(.25 if 3006 in a.items else 0)+rune_speed);a.attacks+=1
        self.visuals.append(dict(t=self.t,until=self.t+.32,kind='ranged' if a.kind=='tower' or a.reach>map_range(175) else 'melee',a=a.id,b=b.id,start=a.pos,p=b.pos,value=0,magic=False))
        self.log('attack',a=a.id,b=b.id,d=round(distance(a.pos,b.pos),3),reach=a.reach)
        if a.kind=='tower' or a.reach>map_range(175):
            self.missiles.append(dict(t=self.t+distance(a.pos,b.pos)/300,a=a.id,b=b.id,p=b.pos,origin=a.pos,power=a.ad,magic=False,spell=False,kind='attack',cc=0,sequence=a.attacks))
        else:self.damage(a,b,a.ad,hit_kind='auto' if a.rune else None,source=('attack',a.attacks))
        if a.kind=='champion':
            if a.name=='Ashe':b.effects['slow']=(self.t+1,.22)
            if a.name=='MasterYi' and a.attacks%4==0:self.damage(a,b,a.ad*.5)
            if self.buff(a,'truebuff'):self.damage(a,b,40+a.level*2,true=True)
            if a.name=='Teemo' or self.buff(a,'poisonbuff'):b.effects[f'poison:{a.id}']=(self.t+4,12+a.ap*.1,self.t+1)
            if self.buff(a,'ricochet'):
                for u in [u for u in self.nearby(b.pos,45) if u.team==b.team and u.id!=b.id][:3]:self.damage(a,u,a.ad*.4)
            bomb=b.effects.get(f'bomb:{a.id}')
            if bomb:b.effects[f'bomb:{a.id}']=(bomb[0] if bomb[2]<3 else self.t,bomb[1],bomb[2]+1)
        return True
    def cast(self,u,target,slot=None):
        if u.cc>self.t or u.silence>self.t or u.channel:return False
        c=KITS[u.name]
        for i in ((slot,) if slot is not None else (3,0,2,1)):
            name,kind,power,reach,cool,cc=c.spells[i]
            if self.t<u.cool[i] or u.mana<45 or (i==3 and u.level<6) or (i in (1,2) and u.level<i+1):continue
            friends=[a for a in self.players(u.team) if a.alive and distance(u.pos,a.pos)<=max(reach,1)]
            ally=min(friends,key=lambda a:a.hp/a.maxhp,default=u)
            support=kind in ('heal','globalheal','shield','immune','guard','haste','teamhaste','spellshield','vision','meditate','truebuff','poisonbuff','ricochet','portal','gate')
            if kind in ('heal','globalheal','meditate') and (u if kind=='meditate' else ally).hp/(u if kind=='meditate' else ally).maxhp>.7:continue
            if u.name=='Soraka' and i==1 and (ally==u or u.hp/u.maxhp<.3):continue
            if not support and (not target or not target.alive or target.kind in STRUCTURES or distance(u.pos,target.pos)>reach or not self.terrain.sight(u.pos,target.pos)):continue
            if kind in ('guard','shield','immune','spellshield','haste','teamhaste','vision') and (not target or target.kind!='champion'):continue
            if i==3 and target and target.kind in ('camp','minion') and slot is None:continue
            if kind in ('portal','gate') and (not target or target.kind!='champion'):continue
            u.mana-=45;u.cool[i]=self.t+cool;power+=u.ap*.55+u.level*3
            self.log('cast',unit=u.id,target=target.id if target else u.id,slot=i,name=name)
            packet=dict(t=self.t,a=u.id,b=target.id if target else u.id,p=target.pos if target else u.pos,origin=u.pos,power=power,magic=True,spell=True,kind=kind,cc=cc,slot=i,cast_at=self.t)
            if kind in ('heal','globalheal'):
                for a in (self.players(u.team) if kind=='globalheal' else [ally]):self.heal(a,power)
                if u.rune=='aery' and ally!=u and self.rune_ready(u):
                    ally.shield=max(ally.shield if ally.shielduntil>self.t else 0,24+3*u.level+.1*u.ap)
                    ally.shielduntil=max(ally.shielduntil,self.t+2)
                    self.rune_used(u,3,ally)
                if u.name=='Soraka' and i==1:u.hp=max(1,u.hp-u.maxhp*.1)
            elif kind=='shield':ally.shield=power;ally.shielduntil=self.t+4
            elif kind=='immune':ally.immune=self.t+2.5
            elif kind=='guard':u.guard=c.spells[i][2];u.guarduntil=self.t+5
            elif kind in ('haste','teamhaste'):
                for a in (self.players(u.team) if kind=='teamhaste' else [u]):a.haste=c.spells[i][2];a.hasteuntil=self.t+6
            elif kind=='spellshield':u.spellshield=self.t+2
            elif kind=='vision':self.vision[u.team]=self.t+6
            elif kind in ('truebuff','poisonbuff','ricochet'):u.buffs[kind]=self.t+6
            elif kind in ('meditate','channel','storm','portal','gate'):
                u.channel=dict(end=self.t+(2.5 if kind!='storm' else 1.5),next=self.t+.5,packet=packet)
                if kind=='gate':self.vision[u.team]=self.t+8
            elif kind=='trap':self.areas.append(dict(kind='trap',a=u.id,p=target.pos,r=8,power=power,end=self.t+180,next=self.t+1,cc=1))
            elif kind=='zone':self.areas.append(dict(kind='zone',a=u.id,p=target.pos,r=9,power=power/4,end=self.t+4,next=self.t,cc=cc))
            elif kind=='bomb':target.effects[f'bomb:{u.id}']=(self.t+4,power,0)
            elif kind=='tether':
                for a in self.nearby(u.pos,reach):
                    if a.kind=='champion' and a.team==1-u.team:self.damage(u,a,power*.4,True,spell=True);a.effects[f'tether:{u.id}']=(self.t+2.5,power*.6,reach+6)
            elif kind=='pet':
                self.hit(packet);a=self.add('티버',u.team,'pet',target.pos,850+u.level*40,40+u.ap*.15,20);a.owner=u.id;a.expires=self.t+40
            else:
                if kind in ('dash','blink'):
                    # Even abilities cannot silently walk through walls. Blink is
                    # explicit and shown as a distinct teleport visual.
                    if kind=='blink':
                        u.pos=self.terrain.snap(target.pos);u.path=[]
                        self.visuals.append(dict(t=self.t,until=self.t+.5,kind='blink',a=u.id,b=target.id,p=u.pos,start=packet['origin'],value=0,magic=True))
                    else:self.move(u,target.pos,min(1,reach/u.speed))
                    if distance(u.pos,target.pos)>u.reach+4:continue
                if kind=='counter':u.buffs['dodge']=self.t+1.5;packet['t']=self.t+1.5
                elif kind in ('line','pierce'):
                    packet['t']=self.t+distance(u.pos,target.pos)/240
                    # Aim accuracy affects skill shots, never targeted spells or champion base damage.
                    angle=self.rng.uniform(0,math.tau)
                    error=max(0,1-min(1,max(0,u.mechanics)))*12*self.rng.random()
                    packet['p']=(target.pos[0]+math.cos(angle)*error,target.pos[1]+math.sin(angle)*error)
                self.missiles.append(packet)
            return True
        return False
    def cc_apply(self,u,duration,kind='stun'):
        if not u.alive or u.kind in STRUCTURES or u.kind=='boss':return
        if kind=='root':u.rootuntil=max(u.rootuntil,self.t+duration)
        elif kind=='slow':u.effects['slow']=(self.t+duration,.35)
        elif kind=='blind':u.blind=self.t+duration
        else:u.cc=max(u.cc,self.t+duration);u.channel={}
    def hit(self,p):
        a=self.units[p['a']];b=self.units[p['b']];kind=p['kind']
        if not b.alive:return
        targets=[b]
        if kind in ('aoe','counter','channel'):targets=[v for v in self.nearby(a.pos,15 if kind=='channel' else 10) if v.team!=a.team and v.kind not in STRUCTURES]
        for v in targets:
            blocked=v.spellshield>self.t or v.immune>self.t
            hit_kind=('auto' if kind=='attack' else 'ability') if a.rune else None
            source=(kind,p.get('sequence') if kind=='attack' else p.get('cast_at'),p.get('slot'))
            dealt=self.damage(a,v,p['power']*(3 if kind=='consume' and v.kind in ('camp','boss') else 1),p['magic'],kind=='consume' and v.kind in ('camp','boss'),p['spell'],hit_kind,source)
            if blocked:continue
            if kind in ('drain','consume'):self.heal(a,dealt*.65)
            if p['cc']:
                cc_kind='blind' if kind=='blind' else 'root' if a.name in ('Ryze','Morgana') else 'slow' if a.name=='Ashe' and p.get('slot')==1 else 'stun'
                self.cc_apply(v,p['cc'],cc_kind)
                if v.alive and v.kind=='champion' and cc_kind in ('stun','root') and a.rune=='aftershock' and self.rune_ready(a):
                    a.buffs['aftershock']=self.t+2.5
                    self.rune_used(a,20,v)
                    self.areas.append(dict(kind='aftershock',a=a.id,p=a.pos,r=map_range(350),power=35+2*a.level+.05*a.maxhp,end=self.t+3,next=self.t+2.5,cc=0))
            if a.name=='Annie' and p.get('slot') is not None:
                a.proc['stacks']=a.proc.get('stacks',0)+1
                if a.proc['stacks']%4==0:self.cc_apply(v,1.2)
            if kind=='knockback':
                dx=v.pos[0]-a.pos[0];dy=v.pos[1]-a.pos[1];d=max(.01,distance(a.pos,v.pos));end=(v.pos[0]+dx/d*45,v.pos[1]+dy/d*45)
                # Forced movement also stops at terrain, never clips across walls.
                for k in range(1,31):
                    pos=(v.pos[0]+(end[0]-v.pos[0])*k/30,v.pos[1]+(end[1]-v.pos[1])*k/30)
                    if not self.terrain.clear(v.pos,pos):break
                    last=pos
                if 'last' in locals():v.pos=last;v.path=[]
    def resolve(self):
        remaining=[]
        for p in self.missiles:
            if p['t']>self.t:remaining.append(p);continue
            a=self.units[p['a']];b=self.units[p['b']]
            if p['kind'] in ('line','pierce'):
                origin=p['origin'];aim=p['p'];dx=aim[0]-origin[0];dy=aim[1]-origin[1];length=max(.01,dx*dx+dy*dy);victims=[]
                for v in self.nearby(((origin[0]+aim[0])/2,(origin[1]+aim[1])/2),distance(origin,aim)/2+12):
                    if v.team==a.team or v.kind in STRUCTURES:continue
                    f=max(0,min(1,((v.pos[0]-origin[0])*dx+(v.pos[1]-origin[1])*dy)/length))
                    closest=(origin[0]+dx*f,origin[1]+dy*f)
                    if distance(v.pos,closest)<3 and self.terrain.sight(origin,v.pos):victims.append((f,v.id))
                for _,uid in sorted(victims)[:99 if p['kind']=='pierce' else 1]:self.hit(dict(p,b=uid))
            elif p['kind']=='attack':
                if b.alive:self.hit(p)
            else:self.hit(p)
        self.missiles=remaining
    def buy(self,u):
        for item in KITS[u.name].build:
            if item in u.items:continue
            name,cost,stat,value=ITEMS[item]
            if u.gold<cost:break
            u.gold-=cost;u.items.append(item)
            if stat=='hp':u.maxhp+=value;u.hp+=value
            elif stat in ('ad','ap','armor','mr','speed'):setattr(u,stat,getattr(u,stat)+value)
            self.log('purchase',unit=u.id,item=item)
    def macro(self,team):
        friends=[a for a in self.players(team) if a.alive and a.hp/a.maxhp>.5];observer=self.players(team)[0]
        enemies=[v for v in self.players(1-team) if v.alive and self.visible(team,v)]
        threats=[v for v in self.nearby(NEXUS[team],42)
                 if v.team==1-team and (v.kind=='minion' or v.kind=='champion' and self.visible(team,v))]
        if len(threats)>=4 or any(v.kind=='champion' or v.name=='Super' or distance(v.pos,NEXUS[team])<22 for v in threats):
            target=min(threats,key=lambda v:distance(v.pos,NEXUS[team]))
            return dict(kind='수비',p=target.pos)
        for tower in self.structures:
            if tower.kind!='tower' or tower.team!=team or not tower.alive:continue
            attackers=[v for v in self.nearby(tower.pos,48) if v.team==1-team and v.kind=='champion' and self.visible(team,v)]
            if len(attackers)>=2 and len(friends)>=3:return dict(kind='수비',p=tower.pos)
        enemy_alive=sum(v.alive for v in self.players(1-team))
        if any(v.kind=='inhibitor' and v.team==1-team and not v.alive for v in self.structures) and len(friends)>=3 and enemy_alive<=2:
            return dict(kind='넥서스 공략',p=self.terrain.snap(NEXUS[1-team]))
        own_gold=sum(v.earned for v in self.players(team))
        enemy_gold=sum(v.earned for v in self.players(1-team))
        if self.t>=900 and own_gold<enemy_gold*.88 and len(friends)>=3:
            defender=self.assign_defenders(team)
            tower=next(iter(defender.values()),None)
            if tower:return dict(kind='수비',p=tower.pos)
            wave=self.lane_waves.get((team,'MID'))
            if wave:return dict(kind='미드 집결',p=wave[0])
        # An objective plan persists until the entire pack is cleared. This is
        # essential for grubs: one kill must not send the jungler back to farming.
        old=self.plans[team]
        if old.get('kind')=='오브젝트':
            cfg=self.camps[old['camp']];living=[self.units[i] for i in cfg['members'] if self.units[i].alive]
            if living:
                target=min(living,key=lambda v:distance(v.pos,old['p']))
                contest=sum(distance(v.pos,target.pos)<90 for v in enemies)
                present=sum(distance(a.pos,target.pos)<90 for a in friends)
                damage_progress=sum(v.hp for v in living)<old.get('hp',0)*.75
                if self.t-old['since']<(100 if damage_progress else 55) and (not contest or present>=contest) and any(a.role=='JUNGLE' for a in friends):
                    return dict(old,p=target.pos)
                self.objective_retry[team][old['camp']]=self.t+80
        camps=sorted(enumerate(self.camps),key=lambda c:(self.units[c[1]['id']].name!='Grub',self.units[c[1]['id']].name!='Dragon'))
        setup=None;conceded=None
        enemy_down=sum(not v.alive and v.dead_until-self.t>=10 for v in self.players(1-team))
        for ci,cfg in camps:
            if cfg['team']!=-1 or self.t<self.objective_retry[team].get(ci,0):continue
            alive=[self.units[i] for i in cfg['members'] if self.units[i].alive]
            if not alive:continue
            boss=alive[0];rival=[v for v in enemies if distance(v.pos,boss.pos)<130]
            healthy=[a for a in friends if distance(a.pos,boss.pos)<260]
            if boss.name=='Baron' and len(healthy)<3:continue
            priority_lanes=('TOP','MID') if boss.name in ('Grub','Herald','Baron') else ('MID','BOT')
            wave_priority=any(self.wave_advantage(team,lane) for lane in priority_lanes)
            jungler_near=any(a.role=='JUNGLE' and distance(a.pos,boss.pos)<150 for a in friends)
            committed=[a for a in healthy if a.role=='JUNGLE' or (a.lane in priority_lanes and self.wave_advantage(team,a.lane))]
            if self.t>=1200:
                committed=[a for a in healthy if distance(a.pos,boss.pos)<165]
            recent_rivals={i for i,t in boss.attackers.items() if self.t-t<5 and self.units[i].team==1-team}
            rival_started=boss.hp<boss.maxhp*.90 and bool(recent_rivals) and (
                self.ward_sees(team,boss.pos) or any(distance(a.pos,boss.pos)<40 for a in friends)
            )
            local=[a for a in friends if distance(a.pos,boss.pos)<100]
            if rival_started and len(local)<max(len(recent_rivals),len(rival)):
                jungler=next((a for a in local if a.role=='JUNGLE' and a.aggression>=.64 and
                              a.hp/a.maxhp>=.68 and self.ready(a,'Smite')),None)
                if jungler and boss.hp<=boss.maxhp*.50 and len(local)+1>=len(recent_rivals):
                    return dict(kind='강타 스틸',p=boss.pos,camp=ci,runner=jungler.id)
                conceded=boss
                continue
            enough=boss.name!='Baron' or len(committed)>=3
            if enough and jungler_near and (not rival or rival_started or (wave_priority or enemy_down) and len(committed)>=len(rival)):
                return dict(kind='오브젝트',camp=ci,p=boss.pos,since=self.t,contest=rival_started,hp=sum(v.hp for v in alive))
            if setup is None and (not rival or len(local)>=len(rival)):
                setup=dict(kind='시야 준비',p=boss.home,lanes=priority_lanes)
        for cfg in self.camps:
            if cfg['team']!=-1:continue
            boss=self.units[cfg['id']]
            if 0<boss.dead_until-self.t<=45 and any(a.role=='JUNGLE' and distance(a.pos,boss.home)<170 for a in friends):
                lanes=('MID','BOT') if boss.name=='Dragon' else ('TOP','MID')
                setup=dict(kind='시야 준비',p=boss.home,lanes=lanes)
                break
        if self.t>=180:
            for enemy in enemies:
                lane=enemy.proc.get('active_lane',enemy.lane)
                on_ward=self.ward_sees(team,enemy.pos)
                if not on_ward:
                    if lane not in ('TOP','BOT'):continue
                    outer=self.lanes[lane][3 if team==0 else 5]
                    if distance(enemy.pos,outer)>36 or distance(enemy.pos,self.lanes[lane][4])<30:continue
                backup=sum(v.id!=enemy.id and distance(v.pos,enemy.pos)<52 for v in enemies)
                if backup>1:continue
                if any(v.kind=='tower' and v.team==enemy.team for v in self.nearby(enemy.pos,TOWER_RANGE+6)):continue
                nearby=sorted((v for v in friends if v.hp/v.maxhp>.65 and distance(v.pos,enemy.pos)<45 and self.terrain.sight(v.pos,enemy.pos)),
                              key=lambda v:distance(v.pos,enemy.pos))
                if len(nearby)>=2 and (not backup or enemy.hp/enemy.maxhp<.48 and nearby[0].aggression>=.64):
                    return dict(kind='고립된 적 압박',target=enemy.id,hunters=[v.id for v in nearby[:2]])
        if conceded and self.t>=900:
            other_lane='TOP' if conceded.name=='Dragon' else 'BOT'
            wave=self.lane_waves.get((team,other_lane))
            if wave and self.wave_advantage(team,other_lane):
                return dict(kind='반대편 압박',p=wave[0],lane=other_lane)
        baron_ready=sum(self.buff(v,'baron') for v in friends)>=3
        if self.t>=840 and len(friends)>=3 and (baron_ready or enemy_down>=1):
            waves=[(lane,self.lane_waves[team,lane]) for lane in ('MID','TOP','BOT')
                   if (team,lane) in self.lane_waves and self.wave_advantage(team,lane)]
            if waves:
                lane,wave=max(waves,key=lambda pair:distance(pair[1][0],NEXUS[team])+pair[1][1]*3)
                return dict(kind='웨이브 공성',p=wave[0],lane=lane)
        if setup:return setup
        if self.t>=1200 and len(friends)>=3:
            wave=self.lane_waves.get((team,'MID'))
            if wave:return dict(kind='미드 집결',p=wave[0])
        return dict(kind='라인전' if self.t<900 else '운영',p=self.terrain.snap(NEXUS[1-team]))
    def assign_defenders(self,team):
        available=[u for u in self.players(team) if u.alive and u.hp/u.maxhp>.55 and u.role!='JUNGLE']
        threatened=[]
        for lane in ('TOP','MID','BOT'):
            wave=self.lane_waves.get((1-team,lane))
            if not wave:continue
            tower=next((v for v in self.structures if v.team==team and v.kind=='tower' and v.lane==lane and v.alive),None)
            if tower and wave[1]>=2 and distance(tower.pos,wave[0])<44:
                threatened.append((tower,wave))
        assignments={}
        for tower,wave in sorted(threatened,key=lambda pair:(-pair[0].depth,-pair[1][1])):
            if not available:break
            u=min(available,key=lambda v:distance(v.pos,tower.pos)+(0 if v.lane==tower.lane else 24))
            available.remove(u)
            assignments[u.id]=tower
        return assignments

    def read_waves(self):
        groups=defaultdict(list)
        for u in self.alive:
            if u.kind=='minion':groups[u.team,u.lane].append(u)
        self.lane_waves={}
        for key, units in groups.items():
            team,lane=key
            path=self.lanes[lane] if team==0 else self.lanes[lane][::-1]
            front=max(units,key=lambda u:(u.depth,-distance(u.pos,path[min(u.depth,len(path)-1)])))
            force=sum(u.hp/260 for u in units if distance(u.pos,front.pos)<=42)
            self.lane_waves[key]=(front.pos,force)

    def wave_advantage(self,team,lane):
        own=self.lane_waves.get((team,lane))
        enemy=self.lane_waves.get((1-team,lane))
        if own is None:return False
        center=self.lanes[lane][4]
        forward=distance(own[0],self.lanes[lane][3 if team==0 else 5])>distance(own[0],self.lanes[lane][5 if team==0 else 3])
        if forward and (enemy is None or distance(own[0],enemy[0])>42):return True
        return own[1]>=(enemy[1] if enemy else 0)+1.5 and (forward or distance(own[0],center)<45)

    def lane_mode(self,u,lane):
        own=self.lane_waves.get((u.team,lane))
        enemy=self.lane_waves.get((1-u.team,lane))
        outer=self.lanes[lane][3 if u.team==0 else 5]
        if enemy and distance(enemy[0],outer)<27 and (not own or enemy[1]>own[1]+3):
            return '라인 받아먹기'
        plan=self.plans[u.team]
        next_boss=any(
            c['team']==-1 and 0<self.units[c['id']].dead_until-self.t<=55 and
            (lane=='MID' or (lane=='BOT')==(self.units[c['id']].name=='Dragon'))
            for c in self.camps
        )
        if next_boss or plan.get('kind')=='오브젝트' or self.t>=1200 and lane=='MID':
            return '웨이브 밀기'
        if own and enemy and own[1]>enemy[1]+1.5:return '웨이브 쌓기'
        return '라인전' if self.t<900 else '사이드 운영'

    def goal(self,u):
        enemies=[a for a in self.nearby(u.pos,130) if a.kind=='champion' and a.team==1-u.team and self.visible(u.team,a)]
        allies=[a for a in self.nearby(u.pos,130) if a.kind=='champion' and a.team==u.team]
        if u.hp/u.maxhp<((.49-.13*u.aggression) if self.t<900 else .33) or (u.mana/u.maxmana<.12 and not enemies) or len(enemies)>len(allies)+1:
            u.intent='귀환';return self.terrain.snap(SPAWNS[u.team])
        plan=self.plans[u.team]
        own_group=self.t>=900 and sum(v.earned for v in self.players(u.team))<sum(v.earned for v in self.players(1-u.team))*.88
        if plan.get('kind') in ('수비','넥서스 공략'):
            u.intent=plan['kind'];return plan['p']
        if plan.get('kind')=='웨이브 공성':
            u.intent='웨이브 공성';u.proc['active_lane']=plan['lane']
            return plan['p']
        if plan.get('kind')=='강타 스틸' and u.id==plan['runner'] and self.ready(u,'Smite'):
            u.intent='강타 스틸';return plan['p']
        if plan.get('kind')=='반대편 압박' and u.role not in ('JUNGLE','SUPPORT') and distance(u.pos,plan['p'])<130:
            u.intent='사이드 운영';u.proc['active_lane']=plan['lane'];return plan['p']
        if plan.get('kind')=='미드 집결' and (u.role not in ('TOP','JUNGLE') or own_group) and not self.defenders[u.team].get(u.id):
            u.intent='미드 집결'
            return plan['p']
        if plan.get('kind')=='고립된 적 압박' and u.id in plan['hunters']:
            enemy=self.units[plan['target']]
            if enemy.alive and self.visible(u.team,enemy) and distance(u.pos,enemy.pos)<55:
                u.intent='고립된 적 압박'
                return enemy.pos
        defense=self.defenders[u.team].get(u.id)
        if defense and defense.alive:
            u.intent='포탑 수비';u.proc['active_lane']=defense.lane
            return defense.pos
        if plan.get('kind')=='오브젝트':
            boss=self.units[self.camps[plan['camp']]['id']].name
            lane_can_leave=(boss in ('Grub','Herald','Baron') and u.lane in ('TOP','MID')) or (boss=='Dragon' and u.lane in ('MID','BOT'))
            if u.role=='JUNGLE' or self.t>=1200 or (lane_can_leave and self.wave_advantage(u.team,u.lane)):
                u.intent='오브젝트';return plan['p']
        if plan.get('kind')=='시야 준비':
            can_ward=u.role=='SUPPORT' and self.t>=u.ward and (
                self.wave_advantage(u.team,u.proc.get('active_lane',u.lane)) or
                any(v.role=='JUNGLE' and v.id!=u.id and distance(v.pos,u.pos)<45 for v in allies)
            )
            if u.role=='JUNGLE' or can_ward:
                u.intent='시야 준비';return plan['p']
        if u.role=='JUNGLE':
            # Opportunistic gank requires visible opponent, nearby ally, and a
            # favourable health/number advantage. No random "kill event".
            exposed=[a for a in enemies if a.hp/a.maxhp<.65 and distance(a.pos,u.pos)<55 and any(b.id!=u.id and b.lane==a.lane and b.hp/b.maxhp>.6 and distance(b.pos,a.pos)<35 for b in allies) and not any(v.kind=='tower' and v.team==a.team for v in self.nearby(a.pos,TOWER_RANGE))]
            if exposed and self.t>=210 and u.aggression>.4 and (self.t>=u.gank_ready or self.t<u.gank_until):
                if self.t>=u.gank_ready:u.gank_ready=self.t+105;u.gank_until=self.t+10
                u.intent='갱킹';return min(exposed,key=lambda a:distance(a.pos,u.pos)).pos
            camps=[self.units[i] for c in self.camps if c['team']==u.team for i in c['members'] if self.units[i].alive]
            if camps:u.intent='정글링';return min(camps,key=lambda a:distance(a.pos,u.pos)).pos
            if plan.get('kind')=='미드 집결':
                mid=[a for a in allies if a.id!=u.id and a.hp/a.maxhp>.55 and distance(a.pos,plan['p'])<50]
                if len(mid)>=2:
                    u.intent='합류';return plan['p']
            pending=[self.units[c['id']] for c in self.camps if c['team']==u.team and self.units[c['id']].dead_until>self.t]
            if pending:
                camp=min(pending,key=lambda v:max(v.dead_until-self.t,distance(u.pos,v.home)/u.speed))
                if self.t<90 or camp.dead_until-self.t<=35:
                    u.intent='정글 대기';return camp.home
            u.intent='귀환';return self.terrain.snap(SPAWNS[u.team])
        if u.role in ('MID','SUPPORT') and self.t>=480 and self.wave_advantage(u.team,u.lane):
            fighting=[a for a in enemies if self.t-a.lastdamage<2 and distance(a.pos,u.pos)<45 and any(b.id!=u.id and distance(b.pos,a.pos)<30 for b in allies)]
            if fighting:u.intent='합류';return fighting[0].pos
        lane=u.lane
        bot_outer_down=self.t>=840 and any(
            v.kind=='tower' and v.lane=='BOT' and v.depth==0 and not v.alive for v in self.units
        )
        if bot_outer_down:
            if u.role=='MID':lane='BOT'
            elif u.role in ('ADC','SUPPORT'):lane='MID'
        targets=[a for a in self.alive if a.team==1-u.team and a.kind in STRUCTURES and (a.lane==lane or a.lane=='BASE' or a.kind=='nexus') and self.open_structure(a)]
        dest=min(targets,key=lambda a:distance(u.pos,a.pos)).pos if targets else self.terrain.snap(NEXUS[1-u.team])
        path=self.lanes[lane] if u.team==0 else list(reversed(self.lanes[lane]))
        index=min(range(len(path)),key=lambda i:distance(u.pos,path[i]));end=min(range(len(path)),key=lambda i:distance(dest,path[i]))
        u.intent=self.lane_mode(u,lane)
        u.proc['active_lane']=lane
        if self.t>=840 and lane!='MID' and u.role in ('TOP','MID','ADC'):
            own_outer=self.lanes[lane][3 if u.team==0 else 5]
            enemy_outer=self.lanes[lane][5 if u.team==0 else 3]
            alone=not any(v.id!=u.id and distance(v.pos,u.pos)<45 for v in allies)
            missing=sum(v.alive and not self.visible(u.team,v) for v in self.players(1-u.team))
            if alone and missing>=2 and distance(u.pos,enemy_outer)<distance(u.pos,own_outer):
                u.intent='사이드 후퇴'
                return self.terrain.snap(own_outer)
        if u.intent=='라인 받아먹기':
            return self.lane_waves[1-u.team,lane][0]
        if index<end and distance(u.pos,path[index])<70:return path[index+1]
        if index<end:return path[index]
        return dest
    def effects(self):
        for u in self.alive:
            if not u.alive:continue
            if u.expires and self.t>=u.expires:u.hp=0;continue
            for key,e in list(u.effects.items()):
                if key.startswith('deathfire:'):
                    if self.t>=e[1] and self.t<=e[0]+.01:
                        owner=self.units[int(key.split(':')[1])]
                        power=(4+8*(owner.level-1)/17+.03*owner.ap)*(2 if self.t-e[2]>=3 else 1)
                        self.damage(owner,u,power,magic=True,spell=True)
                        u.effects[key]=(e[0],e[1]+1,e[2])
                    if self.t>e[0]+.01:u.effects.pop(key,None)
                    continue
                if key.startswith('ignite:') and self.t>=e[2] and self.t<=e[0]+.01:
                    self.damage(self.units[int(key.split(':')[1])],u,e[1],true=True,spell=True)
                    u.effects[key]=(e[0],e[1],e[2]+1)
                if key.startswith('poison:') and self.t>=e[2] and self.t<e[0]:
                    self.damage(self.units[int(key.split(':')[1])],u,e[1],True);u.effects[key]=(e[0],e[1],self.t+1)
                if key.startswith('tether:'):
                    a=self.units[int(key.split(':')[1])]
                    if not a.alive or distance(a.pos,u.pos)>e[2]:u.effects.pop(key,None);continue
                if self.t>=e[0]:
                    u.effects.pop(key,None)
                    if key.startswith('bomb:') or key.startswith('tether:'):
                        a=self.units[int(key.split(':')[1])];self.damage(a,u,e[1]*(1+e[2]*.25 if key.startswith('bomb:') else 1),True,spell=True)
                        if key.startswith('tether:'):self.cc_apply(u,1.5)
            if u.channel:
                channel=u.channel;p=channel['packet'];kind=p['kind']
                if u.cc>self.t or u.silence>self.t:u.channel={};continue
                if kind=='meditate' and self.t>=channel['next']:self.heal(u,50+u.level*4);channel['next']=self.t+.5
                if self.t>=channel['end']:
                    u.channel={}
                    if kind=='storm':
                        old=u.pos;u.pos=self.terrain.snap(p['p']);u.path=[]
                        self.visuals.append(dict(t=self.t,until=self.t+.6,kind='blink',a=u.id,b=u.id,p=u.pos,start=old,value=0,magic=True))
                        self.areas.append(dict(kind='zone',a=u.id,p=u.pos,r=15,power=p['power']/5,end=self.t+5,next=self.t,cc=0))
                    elif kind in ('portal','gate'):
                        old=u.pos;travellers=[a for a in self.players(u.team) if a.alive and distance(a.pos,old)<50] if kind=='portal' else [u]
                        for a in travellers:
                            a.pos=self.terrain.snap(p['p']);a.path=[];self.visuals.append(dict(t=self.t,until=self.t+.6,kind='blink',a=a.id,b=a.id,p=a.pos,start=old,value=0,magic=True))
                    elif kind=='channel':self.hit(p)
                    elif kind=='teleport' and self.units[p['target']].alive:
                        u.pos=self.terrain.snap(self.units[p['target']].pos);u.path=[];u.decision=0
                        self.log('summoner_arrival',unit=u.id,spell='Teleport',p=u.pos)
            if u.kind=='champion':
                if 3157 in u.items and u.hp/u.maxhp<.2 and self.t-u.lastdamage<2 and u.proc.get('stasis',0)<=self.t:
                    u.immune=self.t+2.5;u.buffs['stasis']=self.t+2.5;u.proc['stasis']=self.t+100;u.channel={}
        remaining=[]
        for a in self.areas:
            if self.t>a['end']:continue
            owner=self.units[a['a']]
            if a['next']>self.t:remaining.append(a);continue
            if a['kind']=='aftershock' and not owner.alive:continue
            center=owner.pos if a['kind']=='aftershock' else a['p']
            targets=[u for u in self.nearby(center,a['r']) if u.team!=owner.team and u.kind not in STRUCTURES]
            if a['kind']=='trap' and not targets:remaining.append(a);continue
            for u in targets:
                if a['kind']=='comet' and u.kind!='champion':continue
                hit_kind='ability' if a['kind'] in ('zone','trap') and owner.rune else None
                self.damage(owner,u,a['power'],True,spell=True,hit_kind=hit_kind,source=(a['kind'],a['end']))
                if a['cc']:self.cc_apply(u,a['cc'],'slow')
            if a['kind']=='zone':a['next']=self.t+1;remaining.append(a)
        self.areas=remaining
    def step(self):
        if self.winner is not None:return
        self.t=round(self.t+DT,4)
        if self.t>=825:
            for u in self.persistent:
                if u.name=='Grub' or u.name=='Herald' and self.t>=1185:u.hp=0;u.dead_until=0
        for u in (*self.persistent,*self.wave_units):
            if not u.alive and u.dead_until and self.t>=u.dead_until:
                u.hp=u.maxhp;u.dead_until=0;u.attackers={};u.path=[];u.effects={};u.channel={};u.cc=0;u.rootuntil=0;u.silence=0;u.blind=0
                u.pos=u.home if u.kind!='champion' else self.terrain.snap(SPAWNS[u.team])
                u.mana=u.maxmana;u.recall=0;u.decision=0;self.log('respawn',unit=u.id)
        if self.t>=self.nextwave:
            self.nextwave+=20 if self.t>=1800 else 25 if self.t>=840 else 30
            self.wave+=1
            cannon=self.wave%(1 if self.t>=2100 else 2 if self.t>=900 else 3)==0
            for team in (0,1):
                for lane in ('TOP','MID','BOT'):
                    names=['Melee']*(2 if cannon and 840<=self.t<1800 else 3)+['Caster']*(2 if self.t>=1800 else 3)
                    if cannon:names.append('Cannon')
                    if any(u.kind=='inhibitor' and u.team==1-team and u.lane==lane and not u.alive for u in self.structures):names.append('Super')
                    for name in names:
                        mult=2.8 if name=='Super' else 1.8 if name=='Cannon' else 1
                        u=self.add(name,team,'minion',SPAWNS[team],(260+self.t*.13)*mult,(18+self.t*.008)*mult,map_range(550 if name in ('Caster','Cannon') else 110));u.lane=lane;u.depth=1;u.speed=11
        self.reindex();self.effects();self.resolve()
        if self.t>=self.next_wave_read:
            self.next_wave_read=self.t+1
            self.read_waves()
        self.wards=[w for w in self.wards if w['end']>self.t]
        if self.t>=self.nextmacro:
            self.nextmacro=self.t+5
            for team in (0,1):
                self.plans[team]=self.macro(team)
                self.defenders[team]=self.assign_defenders(team)
        for u in self.players():
            self.earn(u,DT*(2.4 if u.role=='SUPPORT' else 2))
            if self.t>=65 and u.alive and u.intent in ('라인전','웨이브 쌓기','웨이브 밀기','라인 받아먹기') and u.role in ('TOP','MID','ADC','SUPPORT'):
                if any(v.kind=='minion' and v.lane==u.lane and v.team!=u.team for v in self.nearby(u.pos,40)):
                    u.quest=min(100,u.quest+DT*.075)
        for u in list(self.alive):
            if not u.alive:continue
            if self.winner is not None:break
            if u.kind=='champion':self.champion_step(u)
            elif u.kind in ('camp','boss'):self.neutral_step(u)
            elif u.kind=='pet':
                a=self.units[u.owner];enemies=[v for v in self.nearby(u.pos,110) if v.team==1-u.team]
                target=min(enemies,key=lambda v:(v.kind!='champion',distance(u.pos,v.pos)),default=None)
                if target:
                    if not self.attack(u,target):self.move(u,target.pos)
                elif a.alive:self.move(u,a.pos)
            elif u.kind in ('tower','minion'):
                enemies=[v for v in self.nearby(u.pos,u.reach+8) if v.team==1-u.team and self.open_structure(v) and self.terrain.sight(u.pos,v.pos)]
                def priority(v):
                    aggro=u.kind=='tower' and v.kind=='champion' and any(a.kind=='champion' and a.team==u.team and self.t-a.attackers.get(v.id,-999)<3 for a in self.nearby(u.pos,120))
                    return(0 if aggro else 1 if v.kind=='minion' else 2,distance(u.pos,v.pos))
                if u.kind=='minion':
                    enemies=[v for v in enemies if v.kind!='minion' or v.lane==u.lane]
                target=min(enemies,key=priority,default=None)
                if target:
                    self.attack(u,target)
                    if u.kind=='minion' and distance(u.pos,target.pos)>u.reach:self.move(u,target.pos)
                elif u.kind=='minion':
                    lane=self.lanes[u.lane] if u.team==0 else list(reversed(self.lanes[u.lane]))
                    if u.depth<len(lane):
                        self.move(u,lane[u.depth])
                        if distance(u.pos,lane[u.depth])<9:u.depth+=1
        self.visuals=[e for e in self.visuals if e['until']>=self.t]
    def neutral_step(self,u):
        attackers=[self.units[i] for i,t in u.attackers.items() if self.t-t<7 and self.units[i].alive and distance(self.units[i].pos,u.home)<85]
        leash=12 if u.kind=='boss' else 20
        if distance(u.pos,u.home)>leash or not attackers:
            if u.hp<u.maxhp or distance(u.pos,u.home)>2:
                u.attackers={};self.move(u,u.home);self.heal(u,u.maxhp*DT*.12)
            return
        target=min(attackers,key=lambda a:distance(a.pos,u.pos))
        if not self.attack(u,target):
            gap=distance(u.home,target.pos)
            destination=target.pos if gap<=leash else tuple(a+(b-a)*leash/gap for a,b in zip(u.home,target.pos))
            self.move(u,destination)
    def opening_lane_step(self,u):
        lane=self.lanes[u.lane]
        corner=lane[4]
        outer=lane[3 if u.team==0 else 5]
        staging=tuple(a+(b-a)*.7 for a,b in zip(outer,corner))
        u.intent='초반 배치';u.target=-1
        if self.t<45 or u.hp/u.maxhp<.6:
            self.move(u,staging if u.hp/u.maxhp>=.6 else outer)
            return

        allies=[v for v in self.nearby(u.pos,25) if v.kind=='champion' and v.team==u.team and v.id!=u.id and v.hp/v.maxhp>=.6]
        targets=[v for v in self.nearby(u.pos,28) if v.kind=='champion' and v.team!=u.team and self.visible(u.team,v) and self.terrain.sight(u.pos,v.pos)]
        for target in sorted(targets,key=lambda v:distance(u.pos,v.pos)):
            if any(v.kind=='tower' and v.team==target.team for p in (u.pos,target.pos) for v in self.nearby(p,TOWER_RANGE)):
                continue
            opponents=[v for v in self.nearby(target.pos,25) if v.kind=='champion' and v.team!=u.team]
            support=[v for v in allies if distance(v.pos,target.pos)<=25]
            advantage=bool(support) and len(support)+1>len(opponents)
            bot_trade=u.role in ('ADC','SUPPORT') and target.role in ('ADC','SUPPORT') and any(v.role in ('ADC','SUPPORT') for v in support)
            if advantage or bot_trade and distance(u.pos,target.pos)<=u.reach:
                u.target=target.id;u.intent='초반 견제'
                if not self.attack(u,target) and advantage and distance(u.pos,target.pos)>u.reach:
                    self.move(u,target.pos)
                return
        self.move(u,staging)

    def combat_balance(self,u,target):
        nearby=self.nearby(target.pos,43)
        def strength(v):
            return (.45+.55*v.hp/v.maxhp)*(1+.07*(v.level-u.level))
        allies=sum(strength(v) for v in nearby if v.kind=='champion' and v.team==u.team and v.id!=u.id and self.terrain.sight(v.pos,target.pos))
        enemies=sum(strength(v) for v in nearby if v.kind=='champion' and v.team!=u.team and self.visible(u.team,v))
        return strength(u)+allies,enemies

    def retreat(self,u,threats):
        choices=[v.pos for v in self.nearby(u.pos,100)
                 if v.team==u.team and (v.kind=='tower' or v.kind=='champion' and v.id!=u.id and v.hp/v.maxhp>.65)
                 and self.terrain.clear(u.pos,v.pos)]
        choices=[p for p in choices if min(distance(p,v.pos) for v in threats)>min(distance(u.pos,v.pos) for v in threats)+5]
        destination=min(choices,key=lambda p:distance(u.pos,p),default=SPAWNS[u.team])
        u.intent='후퇴';u.target=-1;u.recall=0;u.decision=0
        self.move(u,destination)

    def jungle_siege(self,u,target):
        if u.intent not in ('합류','넥서스 공략','웨이브 공성'):return False
        nearby=self.nearby(target.pos,43)
        allies=sum(v.kind=='champion' and v.team==u.team and v.id!=u.id and v.hp/v.maxhp>.5 for v in nearby)
        wave=any(v.kind=='minion' and v.team==u.team for v in nearby)
        return allies>=2 and wave

    def champion_step(self,u):
        self.heal(u,DT*.8);u.mana=min(u.maxmana,u.mana+DT*2.5)
        if distance(u.pos,self.terrain.snap(SPAWNS[u.team]))<22:
            self.heal(u,u.maxhp*DT*.18);u.mana=min(u.maxmana,u.mana+DT*120);self.buy(u)
            if u.hp<u.maxhp-.01 or u.mana<u.maxmana-.01:u.intent='회복 중';u.decision=0;return
            if self.t>=300 and self.t-u.lastdamage<25 and self.ready(u,'Teleport') and not u.channel:
                self.teleport_to_lane(u)
        if not u.channel and not self.buff(u,'stasis'):self.defensive_summoner(u)
        if u.cc>self.t or self.buff(u,'stasis') or u.channel:return
        if u.role!='JUNGLE' and u.lane not in self.lanes_started and self.t<150:
            self.opening_lane_step(u)
            return
        threats=[v for v in self.nearby(u.pos,32) if v.kind=='champion' and v.team==1-u.team and self.visible(u.team,v) and self.terrain.sight(u.pos,v.pos)]
        if threats:
            closest=min(threats,key=lambda v:distance(u.pos,v.pos))
            friendly,hostile=self.combat_balance(u,closest)
            steal=self.plans[u.team].get('runner')==u.id and self.ready(u,'Smite') and u.hp/u.maxhp>.60
            retreat_ratio=.88-.34*u.aggression
            if u.hp/u.maxhp<.34 or friendly<hostile*retreat_ratio and not steal:
                self.retreat(u,threats)
                return
        if u.hp/u.maxhp<.42:
            wave=[v for v in self.nearby(u.pos,23) if v.kind=='minion' and v.team==1-u.team]
            if len(wave)>=3 and self.t-u.lastdamage<1.6:
                self.retreat(u,wave)
                return
        if self.t>=u.decision:u.goal=self.goal(u);u.decision=self.t+1.4
        if u.intent=='사이드 후퇴':
            self.move(u,u.goal)
            return
        if u.intent=='귀환':
            if self.t-u.lastdamage>4 and distance(u.pos,SPAWNS[u.team])>30:
                if not u.recall:u.recall=self.t+8
                if self.t>=u.recall:u.pos=self.terrain.snap(SPAWNS[u.team]);u.path=[];u.recall=0;u.decision=0
                return
            self.move(u,SPAWNS[u.team]);return
        nearby=[v for v in self.nearby(u.pos,145) if v.team!=u.team and self.visible(u.team,v) and self.open_structure(v)]
        neutral=u.intent in ('정글링','오브젝트','강타 스틸')
        nearby=[v for v in nearby if v.team!=-1 or neutral and distance(v.home,u.goal)<55]
        lane_intent=u.intent in ('라인전','웨이브 쌓기','웨이브 밀기','라인 받아먹기','사이드 운영','포탑 수비')
        if u.intent=='고립된 적 압박':
            nearby=[v for v in nearby if v.id==self.plans[u.team].get('target')]
        if u.intent=='웨이브 공성':
            lane=u.proc['active_lane']
            nearby=[v for v in nearby if distance(v.pos,u.goal)<44 and (v.kind=='champion' or v.lane in (lane,'BASE'))]
        if u.intent=='강타 스틸':
            nearby=[v for v in nearby if v.kind=='boss']
        if u.intent=='오브젝트':
            nearby=[v for v in nearby if v.kind=='boss' or v.kind=='champion' and distance(v.pos,u.goal)<65]
        if lane_intent:
            lane=u.proc.get('active_lane',u.lane)
            nearby=[v for v in nearby if (v.lane==lane or v.kind=='champion') and distance(u.pos,v.pos)<max(29,u.reach+10)]
        elif u.intent in ('정글링','정글 대기'):
            nearby=[v for v in nearby if v.team==-1 or v.kind=='champion' and self.t-u.attackers.get(v.id,-999)<2]
        def priority(v):
            if v.kind=='champion':
                if u.intent=='오브젝트' and self.plans[u.team].get('contest') and distance(v.pos,u.pos)<32:
                    return(-1,distance(v.pos,u.pos))
                good=u.intent in ('갱킹','합류','수비') or self.t-u.attackers.get(v.id,-999)<2
                return(0 if good else 4,distance(u.pos,v.pos))
            if v.kind=='minion':
                if u.intent=='웨이브 쌓기' and v.hp>=u.ad*1.25:return(1 if v.name=='Caster' else 3,v.hp)
                return(5 if u.role=='SUPPORT' else 1,v.hp)
            return(0 if u.intent=='오브젝트' and v.kind=='boss' else 2,distance(u.pos,v.pos))
        if u.role=='JUNGLE':
            nearby=[v for v in nearby if v.kind not in STRUCTURES or self.jungle_siege(u,v)]
            if u.intent in ('갱킹','시야 준비','오브젝트','합류'):
                nearby=[v for v in nearby if v.kind!='minion']
        target=min(nearby,key=priority,default=None)
        if u.role=='SUPPORT' and target and target.kind=='minion' and any(a.team==u.team and a.role=='ADC' for a in self.nearby(u.pos,120)):target=None
        u.target=target.id if target else -1
        if u.role in ('SUPPORT','JUNGLE') and self.t>=u.ward and self.t>130:
            in_river=u.intent in ('시야 준비','오브젝트') and distance(u.pos,u.goal)<30
            if (in_river or u.intent=='합류') and not any(w['team']==u.team and distance(w['p'],u.pos)<55 for w in self.wards):
                self.wards.append(dict(team=u.team,p=u.pos,end=self.t+100));u.ward=self.t+u.ward_interval
                self.log('ward',unit=u.id,team=u.team,p=u.pos)
        if self.ready(u,'Smite') and u.intent in ('정글링','오브젝트','강타 스틸'):
            monsters=[v for v in self.nearby(u.pos,map_range(500)) if v.kind in ('camp','boss') and v.hp<=600 and self.terrain.sight(u.pos,v.pos)]
            if u.intent=='강타 스틸':
                monsters=[v for v in monsters if v.kind=='boss' and distance(v.home,u.goal)<25]
            if monsters:
                v=min(monsters,key=lambda a:(a.kind!='boss',a.hp));self.use_summoner(u,'Smite',v);self.damage(u,v,600,true=True,spell=True)
        if not target:
            if lane_intent:
                lane=u.proc.get('active_lane',u.lane)
                wave=self.lane_waves.get((u.team,lane))
                tower=next((v for v in self.nearby(u.goal,TOWER_RANGE) if v.kind=='tower' and v.team==1-u.team),None)
                if tower and wave and distance(wave[0],tower.pos)>TOWER_RANGE:
                    self.move(u,wave[0]);return
            self.move(u,u.goal);return
        if not target.alive:return
        if target.kind=='champion':
            friendly,hostile=self.combat_balance(u,target)
            enemy_tower=any(v.kind=='tower' and v.team==target.team for v in self.nearby(target.pos,TOWER_RANGE))
            dive=target.hp/target.maxhp<.22 and u.hp/u.maxhp>.65 and friendly>=2.25 and friendly>hostile*1.5
            if enemy_tower and not dive or friendly<hostile*(1.07-.35*u.aggression):
                if threats:self.retreat(u,threats)
                else:self.move(u,u.goal)
                return
            if u.role in ('ADC','MID') and distance(u.pos,target.pos)>u.reach:
                frontline=[v for v in self.nearby(target.pos,37) if v.team==u.team and v.id!=u.id and v.kind=='champion' and v.reach<=map_range(175)]
                if frontline and all(distance(v.pos,target.pos)>distance(u.pos,target.pos) for v in frontline):
                    self.move(u,min(frontline,key=lambda v:distance(v.pos,u.pos)).pos)
                    return
        if target.kind=='champion' and self.ready(u,'Dot') and target.hp/target.maxhp<.29 and distance(u.pos,target.pos)<=map_range(600) and self.terrain.clear(u.pos,target.pos):
            self.use_summoner(u,'Dot',target)
            target.effects[f'ignite:{u.id}']=(self.t+5,(70+20*u.level)/5,self.t+1)
            target.buffs['grievous']=self.t+5
        clear_wave=u.intent in ('웨이브 밀기','라인 받아먹기','사이드 운영','포탑 수비','수비','미드 집결','웨이브 공성')
        if target.kind!='minion' or clear_wave:self.cast(u,target)
        if u.channel:return
        towers=[a for a in self.nearby(target.pos,TOWER_RANGE) if a.kind=='tower' and a.team==1-u.team]
        safe=not towers or any(a.kind=='minion' and a.team==u.team for a in self.nearby(towers[0].pos,TOWER_RANGE))
        dive=target.kind=='champion' and target.hp/target.maxhp<.25 and sum(a.kind=='champion' and a.team==u.team for a in self.nearby(target.pos,100))>=3
        if distance(u.pos,target.pos)>u.reach or not self.terrain.sight(u.pos,target.pos):
            if safe or dive or target.team==-1:self.move(u,target.pos)
            else:
                friendly=[v for v in self.nearby(u.pos,65) if v.team==u.team and v.kind=='minion']
                if friendly:self.move(u,min(friendly,key=lambda v:distance(v.pos,u.pos)).pos)
        else:
            # Prefer a last hit rather than autoattacking every healthy wave.
            if target.kind=='tower' and self.buff(u,'herald') and safe:
                u.buffs.pop('herald',None);self.damage(u,target,1200,true=True);self.log('herald_charge',unit=u.id,target=target.id)
            last_hit=target.hp<=u.ad*100/(100+target.armor)
            thin_wave=u.intent=='웨이브 쌓기' and target.name=='Caster'
            if target.kind!='minion' or last_hit or clear_wave or thin_wave:self.attack(u,target)
            if u.reach>map_range(175) and target.kind=='champion' and distance(u.pos,target.pos)<u.reach*.6:
                dx=u.pos[0]-target.pos[0];dy=u.pos[1]-target.pos[1];d=max(1,distance(u.pos,target.pos));self.move(u,(u.pos[0]+dx/d*20,u.pos[1]+dy/d*20))
    def ready(self,u,spell):
        return spell in u.summoners and self.t>=u.summoners[spell]

    def use_summoner(self,u,spell,target=None):
        u.summoners[spell]=self.t+SUMMONERS[spell][1]
        self.log('summoner',unit=u.id,target=target.id if target else None,spell=spell,p=u.pos)

    def teleport_to_lane(self,u):
        towers=[v for v in self.alive if v.kind=='tower' and v.team==u.team and v.lane==u.lane and distance(v.pos,u.pos)>120]
        for tower in sorted(towers,key=lambda v:v.depth):
            nearby=self.nearby(tower.pos,35)
            if any(v.kind=='champion' and v.team==1-u.team for v in nearby):continue
            if not any(v.kind=='minion' and v.team==1-u.team for v in nearby):continue
            self.use_summoner(u,'Teleport',tower)
            u.channel=dict(end=self.t+4,next=0,packet=dict(kind='teleport',target=tower.id))
            return

    def defensive_summoner(self,u):
        if self.ready(u,'Boost') and (u.cc>self.t or u.rootuntil>self.t or u.blind>self.t):
            self.use_summoner(u,'Boost');u.cc=u.rootuntil=u.blind=self.t;u.effects.pop('slow',None)
        if u.cc>self.t:return
        enemies=[v for v in self.nearby(u.pos,28) if v.kind=='champion' and v.team==1-u.team and self.terrain.clear(u.pos,v.pos)]
        if not enemies:return
        hp=u.hp/u.maxhp
        if hp<.32 and self.ready(u,'Barrier'):
            self.use_summoner(u,'Barrier');u.shield=max(u.shield,100+12*u.level);u.shielduntil=self.t+2.5
        if self.ready(u,'Heal'):
            allies=[v for v in self.nearby(u.pos,28) if v.kind=='champion' and v.team==u.team]
            partner=min(allies,key=lambda v:v.hp/v.maxhp,default=u)
            if partner.hp/partner.maxhp<.38:
                self.use_summoner(u,'Heal',partner);self.heal(u,65+12*u.level)
                if partner!=u:self.heal(partner,65+12*u.level)
        if hp<.55 and self.ready(u,'Exhaust'):
            target=min(enemies,key=lambda v:distance(v.pos,u.pos))
            if distance(u.pos,target.pos)<=map_range(650):
                self.use_summoner(u,'Exhaust',target);target.buffs['exhaust']=self.t+3;target.effects['slow']=(self.t+3,.3)
        if hp<.36 and self.ready(u,'Haste'):
            self.use_summoner(u,'Haste');u.buffs['ghost']=self.t+10
        if hp<.22 and u.rootuntil<=self.t and self.ready(u,'Flash') and self.t-u.lastdamage<2:
            enemy=min(enemies,key=lambda v:distance(v.pos,u.pos));radius=map_range(400)
            candidates=[(u.pos[0]+math.cos(i*math.tau/16)*radius,u.pos[1]+math.sin(i*math.tau/16)*radius) for i in range(16)]
            legal=[p for p in candidates if self.terrain.legal(p)]
            if not legal:return
            best=max(legal,key=lambda p:distance(p,enemy.pos))
            if distance(best,enemy.pos)>distance(u.pos,enemy.pos)+5:
                self.use_summoner(u,'Flash');u.pos=best;u.path=[];u.decision=0

    def result(self):return dict(seed=self.seed,time=self.t,winner=self.winner,finished=self.winner is not None,events=dict(Counter(e['type'] for e in self.events)),players=[dict(name=u.name,role=u.role,team=u.team,player_id=getattr(u,'player_id',None),player_name=getattr(u,'player_name',None),kda=[u.kills,u.deaths,u.assists],cs=u.cs,items=u.items,gold=round(u.earned),damage=round(u.damage)) for u in self.players()])
