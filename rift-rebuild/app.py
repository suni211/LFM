"""Native SDL broadcast. Rendering never runs match AI on its thread."""
import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT']='1'
import pygame as pg
import sys,time,math,bisect,threading,multiprocessing as mp,queue,json,traceback
from pathlib import Path
from collections import OrderedDict
from data import KITS,ITEMS,ROLES
from data import TOWER_RANGE
from data import RUNE_NAMES,SUMMONERS

PLAYER_NAMES = (('HLE ZEUS','HLE JGL','HLE MID','HLE ADC','HLE SUP'),
                ('RIV TOP','RIV JGL','RIV MID','RIV ADC','RIV SUP'))
from replay import load,worker
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).parent));ASSETS=ROOT/'assets'
HOME=Path(sys.executable).parent if getattr(sys,'frozen',False) else Path(__file__).parent
W,H=1600,900
BLUE=(63,186,239);RED=(242,96,121);GOLD=(224,196,133);TEXT=(235,239,239);MUTED=(144,161,174);LINE=(44,59,69);BG=(8,14,19)
KO_ROLE={'TOP':'탑','JUNGLE':'정글','MID':'미드','ADC':'원딜','SUPPORT':'서폿'}
ELEMENT={'infernal':'화염','ocean':'바다','mountain':'대지','cloud':'바람','hextech':'마법공학','chemtech':'화학공학','elder':'장로'}
def clock(t):t=max(0,int(t));return f'{t//60:02}:{t%60:02}'
def obj(name):return name+('을' if name and 44032<=ord(name[-1])<=55203 and (ord(name[-1])-44032)%28 else '를')
class App:
    def __init__(self,seed=1,headless=False,viewer_only=False,match_only=False):
        self.viewer_only=viewer_only
        self.match_only=match_only
        if headless:os.environ['SDL_VIDEODRIVER']='dummy';os.environ['SDL_AUDIODRIVER']='dummy'
        pg.init();pg.display.set_caption('R/M — RIFT MANAGER')
        pg.display.set_icon(pg.image.load(str(ASSETS/'rm-logo.png')))
        self.fullscreen=not headless
        self.windowed_size=(1280,720)
        self.headless=headless
        self.settings_open=False
        self.display_scale=100
        self.sharp=False
        if not headless:
            try:
                settings=json.loads((HOME/'display.json').read_text(encoding='utf-8'))
                if isinstance(settings,dict):
                    if settings.get('scale') in (70,85,100):self.display_scale=settings['scale']
                    self.sharp=settings.get('sharp') is True
            except (OSError,ValueError):
                pass
        self.window=pg.display.set_mode((W,H) if headless else (0,0),0 if headless else pg.FULLSCREEN)
        self.screen=pg.Surface((W,H)).convert();self.fonts={};self.textcache=OrderedDict();self.native_fonts={};self.text_draws=[];self.icons={};self.scaled={}
        for bold in (False,True):
            for size in (11,14,16,18,22,28):self.fonts[size,bold]=pg.font.Font(str(self.font_path(bold)),size)
        for p in ASSETS.rglob('*.png'):self.icons[p.relative_to(ASSETS).as_posix()]=pg.image.load(str(p)).convert_alpha()
        self.map=pg.transform.smoothscale(self.icons['map.png'].premul_alpha(),(2048,2048))
        self.mapcache=None;self.mapkey=None;self.buttons={};self.running=True;self.tab='items';self.overview=False;self.paused=False
        self.camera=[256.,256.,1.];self.phase='loading';self.data=None;self.loaded=None;self.mail=None;self.proc=None;self.error=None;self.load_error=None
        self.time=0.;self.phase_time=0.;self.clip_index=0;self.frame=None;self.states={};self.players=[];self.positions={};self.meta={};self.progress=0;self.seed=seed;self.render_ms=[];self.fps=60;self.selected=None
        self.flow='watch';self.draft=None;self.roster=None;self.labels=None;self.match_path=None
        self.blue_names=[f'청 {KO_ROLE[role]}' for role in ROLES];self.red_names=[f'홍 {KO_ROLE[role]}' for role in ROLES]
        if not viewer_only and not match_only:
            from manager import Manager
            self.manager=Manager(self)
        else:self.manager=None
        self.management=not headless and not viewer_only and not match_only
        if match_only:self.open_draft()
        elif headless:self.start(seed)
    def font_path(self,bold=False):
        suite=ASSETS/'fonts'/('SUITE-SemiBold.ttf' if bold else 'SUITE-Regular.ttf')
        return suite if suite.exists() else ASSETS/'fonts'/('Galmuri11-Bold.ttf' if bold else 'Galmuri11.ttf')
    def text(self,value,x,y,size=16,color=TEXT,bold=False,anchor='left'):
        if not self.headless:
            self.text_draws.append((str(value),x,y,size,color,bold,anchor,self.screen.get_clip().copy()))
            return
        key=(str(value),size,color,bold);surface=self.textcache.get(key)
        if surface is None:
            surface=self.fonts[size,bold].render(str(value),False,color);self.textcache[key]=surface
            if len(self.textcache)>2000:self.textcache.popitem(last=False)
        r=surface.get_rect();setattr(r,{'left':'topleft','right':'topright','center':'midtop'}[anchor],(int(x),int(y)));self.screen.blit(surface,r)

    def native_text(self,rect):
        scale=rect.w/W
        for value,x,y,size,color,bold,anchor,clip in self.text_draws:
            pixels=max(11,round(size*scale))
            key=(pixels,bold)
            if key not in self.native_fonts:
                self.native_fonts[key]=pg.font.Font(str(self.font_path(bold)),pixels)
            cache=('native',value,pixels,color,bold)
            surface=self.textcache.get(cache)
            if surface is None:
                surface=self.native_fonts[key].render(value,False,color)
                self.textcache[cache]=surface
                if len(self.textcache)>2000:self.textcache.popitem(last=False)
            target=surface.get_rect()
            setattr(target,{'left':'topleft','right':'topright','center':'midtop'}[anchor],(round(rect.x+x*scale),round(rect.y+y*scale)))
            native_clip=pg.Rect(round(rect.x+clip.x*scale),round(rect.y+clip.y*scale),round(clip.w*scale),round(clip.h*scale))
            self.window.set_clip(native_clip.clip(rect));self.window.blit(surface,target)
        self.window.set_clip(None)

    def icon(self,key,x,y,size=22,circle=False):
        cache=(key,size,circle)
        if cache not in self.scaled:
            if key not in self.icons:return
            s=pg.transform.smoothscale(self.icons[key],(size,size))
            if circle:
                mask=pg.Surface((size,size),pg.SRCALPHA);pg.draw.circle(mask,'white',(size//2,size//2),size//2);s.blit(mask,(0,0),special_flags=pg.BLEND_RGBA_MULT)
            self.scaled[cache]=s
        self.screen.blit(self.scaled[cache],(round(x-size/2),round(y-size/2)))
    def bar(self,x,y,w,h,value,color):
        pg.draw.rect(self.screen,(5,11,15),(int(x),int(y),w,h));pg.draw.rect(self.screen,color,(int(x),int(y),max(0,int(w*max(0,min(1,value)))),h))
    def button(self,key,label,r,active=False):
        r=pg.Rect(r);self.buttons[key]=r;pg.draw.rect(self.screen,(35,46,56) if active else (15,24,31),r,border_radius=3);pg.draw.rect(self.screen,GOLD if active else LINE,r,1,border_radius=3);self.text(label,r.centerx,r.y+9,14,GOLD if active else TEXT,active,'center')
    def start(self,seed,roster=None,names=None):
        if self.proc and self.proc.is_alive():self.proc.terminate();self.proc.join(2)
        self.seed=seed;self.roster=roster;self.labels=list(names) if names else None
        self.data=None;self.loaded=None;self.error=None;self.phase='loading';self.frame=None;self.time=0;self.progress=0;self.camera=[256.,256.,1.]
        (HOME/'runs').mkdir(exist_ok=True)
        tag=''
        if roster:
            import hashlib
            tag='-'+hashlib.sha256(repr(tuple(tuple(team) for team in roster)).encode()).hexdigest()[:8]
        path=HOME/'runs'/f'match-{seed}{tag}.json.gz';self.match_path=path
        bundled=ASSETS/'demo.json.gz'
        if path.exists():self.load_async(path)
        elif roster is None and seed==1 and bundled.exists():self.load_async(bundled)
        else:self.spawn(path)
    def spawn(self,path):
        self.mail=mp.get_context('spawn').Queue();self.proc=mp.get_context('spawn').Process(target=worker,args=(self.seed,str(path),self.mail,self.roster,self.labels),daemon=True);self.proc.start()
    def load_async(self,path):
        def job():
            try:self.loaded=load(path)
            except Exception as e:self.load_error=str(e)
        threading.Thread(target=job,daemon=True).start()
    def poll(self):
        if self.load_error:self.load_error=None;self.spawn(self.match_path or HOME/'runs'/f'match-{self.seed}.json.gz')
        if self.mail:
            for _ in range(8):
                try:m=self.mail.get_nowait()
                except queue.Empty:break
                if m['type']=='progress':self.progress=m['t']
                elif m['type']=='done':self.load_async(m['path'])
                else:self.error=m['message'];self.phase='error'
        if self.loaded:
            self.data=self.loaded;self.loaded=None;self.meta={u['id']:u for u in self.data['meta']};self.times=[f['t'] for f in self.data['frames']]
            self.events=self.data['events'];self.etimes=[e['t'] for e in self.events];self.phase='opening';self.phase_time=0.;self.time=0.;self.clip_index=0
            self.openend=min(90,self.data['clips'][0]['start']) if self.data['clips'] else 90;self.base_damage={};self.update_frame()
    def update_frame(self):
        i=max(0,min(len(self.times)-1,bisect.bisect_right(self.times,self.time)-1));self.frame=self.data['frames'][i];self.follow=self.data['frames'][min(i+1,len(self.times)-1)]
        self.states={s[0]:s for s in self.frame['units']};nextstates={s[0]:s for s in self.follow['units']};self.players=self.frame['players'];self.positions={}
        f=(self.time-self.frame['t'])/max(.001,self.follow['t']-self.frame['t'])
        for uid,s in self.states.items():
            n=nextstates.get(uid,s);lerp=s[3]>0 and n[3]>0 and math.hypot(n[1]-s[1],n[2]-s[2])<20
            self.positions[uid]=(s[1]+(n[1]-s[1])*f,s[2]+(n[2]-s[2])*f) if lerp else (s[1],s[2])
    def choose(self,index):
        if index>=len(self.data['clips']):self.phase='ended';return
        self.clip_index=max(0,index);clip=self.data['clips'][self.clip_index];self.time=clip['start'];self.phase='overview';self.phase_time=0
        self.update_frame();self.base_damage={p['id']:p['damage'] for p in self.players}
    def update(self,dt):
        if self.phase=='loading':self.poll();return
        if not self.data or self.paused:return
        self.phase_time+=dt
        if self.phase=='opening':
            self.time=min(self.openend,self.time+dt*6)
            if self.time>=self.openend:self.choose(0)
        elif self.phase=='overview':
            if self.phase_time>1:self.phase='clip';self.phase_time=0
        elif self.phase=='clip':
            c=self.data['clips'][self.clip_index];self.time=min(c['end'],self.time+dt) # always 1x
            if self.time>=c['end']:self.choose(self.clip_index+1)
        self.update_frame()
    def player_name(self,uid):
        unit=self.meta[uid]
        names=(self.data or {}).get('names') if self.data else None
        slot=unit['team']*5+ROLES.index(unit['role'])
        if names and slot<len(names) and names[slot]:return names[slot]
        return PLAYER_NAMES[unit['team']][ROLES.index(unit['role'])]
    def open_draft(self):
        from draft import Draft
        if self.proc and self.proc.is_alive():self.proc.terminate();self.proc.join(2)
        pools=None
        state=self.manager.career.state if self.manager else None
        roster=state.get('roster',[]) if state else []
        if state and len(roster)==5:
            ordered=[next(player for player in roster if player['role']==role) for role in ROLES]
            self.blue_names=[player.get('nickname') or player.get('name') or KO_ROLE[role] for role,player in zip(ROLES,ordered)]
            self.red_names=[f"AI {KO_ROLE[role]}" for role in ROLES]
            pools=([player.get('champion_pool') or {} for player in ordered],[{} for _ in ROLES])
        else:
            self.blue_names=[f'청 {KO_ROLE[role]}' for role in ROLES]
            self.red_names=[f'홍 {KO_ROLE[role]}' for role in ROLES]
        self.draft=Draft(pools);self.flow='draft';self.management=False;self.phase='draft';self.data=None
    def draw_draft(self):
        from draft import TURNS
        from data import KITS
        draft=self.draft
        self.text('밴픽',24,18,28,GOLD,True)
        self.text('팀당 밴 3회 · 포지션당 1명 · 남은 챔피언으로 양 팀 라인업이 가능해야 합니다',120,28,14,MUTED)
        turn=draft.turn()
        if turn:
            kind,team,role=turn
            side='청팀' if team==0 else '홍팀'
            player=(self.blue_names if team==0 else self.red_names)[ROLES.index(role)] if role else ''
            action='밴' if kind=='ban' else KO_ROLE[role]+' 선택'
            self.text(f'{side} {action}'+(f' · {player}' if player else ''),24,68,22,BLUE if team==0 else RED,True)
            self.text(f'{draft.index+1} / {len(TURNS)}',1480,68,16,MUTED,False,'right')
        else:
            self.text('밴픽 완료. 경기 시작을 누르면 매치엔진이 이 로스터로 계산합니다.',24,68,22,GOLD,True)
        for team,title,names,color,x in ((0,'청팀',self.blue_names,BLUE,16),(1,'홍팀',self.red_names,RED,1324)):
            pg.draw.rect(self.screen,(12,21,29),(x,110,260,620),border_radius=6)
            self.text(title,x+16,124,22,color,True)
            self.text('밴',x+16,164,14,MUTED)
            for i,champion in enumerate(draft.banned[team::2]):
                self.icon(f'champions/{champion}.png',x+36,206+i*36,28,True)
                self.text(KITS[champion].ko,x+58,196+i*36,14)
            self.text('픽',x+16,330,14,MUTED)
            for i,role in enumerate(ROLES):
                y=370+i*64
                champion=draft.picks[team][i]
                self.text(KO_ROLE[role],x+16,y,14,MUTED)
                self.text(names[i],x+70,y,14,TEXT,True)
                if champion:
                    self.icon(f'champions/{champion}.png',x+36,y+34,28,True)
                    self.text(KITS[champion].ko,x+58,y+24,16,color,True)
        for i,champion in enumerate(KITS):
            column,row=i%6,i//6
            rect=(330+column*160,150+row*120,148,108)
            allowed=draft.legal(champion)
            picked=champion in draft.taken() and champion not in draft.banned
            banned=champion in draft.banned
            if allowed:self.button(f'draft_pick_{champion}',KITS[champion].ko,rect)
            else:
                pg.draw.rect(self.screen,(10,16,22),rect,border_radius=3)
                self.text(KITS[champion].ko,rect[0]+74,rect[1]+70,14,MUTED,False,'center')
                self.text('밴' if banned else '선택됨' if picked else '불가',rect[0]+74,rect[1]+16,14,RED if banned else MUTED,False,'center')
            self.icon(f'champions/{champion}.png',rect[0]+74,rect[1]+48,36,True)
        self.button('draft_auto','남은 순서 자동',(330,790,220,40))
        if draft.done:self.button('draft_start','경기 시작',(570,790,220,40),True)
        self.button('draft_back','닫기' if self.match_only else '구단으로',(810,790,220,40))
    def draft_click(self,key):
        if key=='draft_auto':self.draft.auto()
        elif key=='draft_back':
            if self.match_only:self.running=False
            else:self.flow='career';self.management=True;self.phase='draft'
        elif key=='draft_start' and self.draft.done:
            names=list(self.blue_names)+list(self.red_names)
            self.flow='watch';self.management=False
            self.start(max(1,int(time.time())),self.draft.roster(),names)
        elif key.startswith('draft_pick_'):self.draft.choose(key[len('draft_pick_'):])
    def viewport(self):return pg.Rect(272,108,1310,470)
    def world_size(self,base):return max(2,round(base*self.camera[2]))
    def xy(self,pos):
        r=self.viewport();scale=r.h/512*self.camera[2];return(round(r.centerx+(pos[0]-self.camera[0])*scale),round(r.centery+(pos[1]-self.camera[1])*scale))
    def focus(self):
        if not self.data or self.phase!='clip' or self.overview:return(256,256,1.)
        clip=self.data['clips'][self.clip_index]
        # Prefer the next event: ten-second pre-roll must frame the coming kill,
        # not a previous unrelated event elsewhere on the map.
        future=[e for e in clip['anchors'] if e['t']>=self.time-.8];anchor=future[0] if future else clip['anchors'][-1]
        points=[self.positions[i] for i in anchor['ids'] if i in self.states and self.states[i][3]>0 and i in self.positions]
        center=anchor['p']
        if anchor.get('kind') in ('structure','victory','objective'):
            return (*center,3.5)
        if points:center=(sum(p[0] for p in points)/len(points),sum(p[1] for p in points)/len(points))
        # Include combatants who are attacking near the tracked participants.
        active=[p for p in self.players if p['hp']>0 and p['target'] in anchor['ids'] and p['id'] in self.positions and math.dist(self.positions[p['id']],center)<170]
        points += [self.positions[p['id']] for p in active]
        if points:center=(sum(p[0] for p in points)/len(points),sum(p[1] for p in points)/len(points))
        spread=max((abs(p[1]-center[1]) for p in points),default=20)
        zoom=max(1.7,min(4.5,512/max(125,spread*2+90)))
        return(center[0],center[1],zoom)
    def map_draw(self,dt):
        r=self.viewport();x,y,zoom=self.focus()
        self.camera[0:2]=x,y
        self.camera[2]+=(zoom-self.camera[2])*(1-math.exp(-dt*7))
        side=max(1,round(r.h*self.camera[2]));key=side
        if key!=self.mapkey:self.mapcache=pg.transform.smoothscale(self.map,(side,side));self.mapkey=key
        pg.draw.rect(self.screen,(9,19,21),r);self.screen.set_clip(r)
        self.screen.blit(self.mapcache,self.mapcache.get_rect(center=self.xy((256,256))),special_flags=pg.BLEND_PREMULTIPLIED)
        if self.frame:
            levels={player['id']:player['level'] for player in self.players}
            for uid,s in self.states.items():
                if s[3]<=0:continue
                u=self.meta[uid];kind=u['kind'];p=self.xy(self.positions[uid]);color=BLUE if u['team']==0 else RED if u['team']==1 else GOLD
                if not r.inflate(50,50).collidepoint(p):continue
                if kind=='minion':
                    pg.draw.circle(self.screen,color,p,4 if u['name'] in ('Cannon','Super') else 2)
                    self.bar(p[0]-5,p[1]-8,10,2,s[3]/max(1,s[4]),color)
                elif kind=='champion':
                    size=22;pg.draw.circle(self.screen,(0,0,0),p,size//2+3);pg.draw.circle(self.screen,color,p,size//2+2,2);self.icon(f'champions/{u["name"]}.png',*p,size,True)
                    width=30;height=4
                    self.bar(p[0]-width//2,p[1]-size//2-height-5,width,height,s[3]/max(1,s[4]),color)
                    badge=pg.Rect(p[0]-width//2-19,p[1]-size//2-15,17,15)
                    pg.draw.rect(self.screen,BG,badge)
                    pg.draw.rect(self.screen,color,badge,1)
                    self.text(levels.get(uid,1),badge.centerx,badge.y+1,11,TEXT,True,'center')
                    if self.camera[2]>1.4:self.text(self.player_name(uid),p[0],p[1]+size//2+4,14,TEXT,anchor='center')
                elif kind in ('tower','inhibitor','nexus'):
                    if kind=='tower' and self.camera[2]>1.4:
                        radius=round(TOWER_RANGE*r.h/512*self.camera[2])
                        pg.draw.circle(self.screen,tuple(int(c*.58) for c in color),p,radius,1)
                    icon={'tower':'icon_ui_tower_minimap','inhibitor':'inhibitor','nexus':'icon_ui_nexus_minimap_v2'}[kind]
                    size=22;pg.draw.circle(self.screen,color,p,size//2+2,2);self.icon('icons/'+icon+'.png',*p,size);self.bar(p[0]-size//2,p[1]-size//2-8,size,4,s[3]/s[4],color)
                elif kind in ('camp','boss'):
                    if not u['minor']:
                        icon='dragon_'+self.frame['element'] if u['name']=='Dragon' else 'baron' if u['name']=='Baron' else 'herald' if u['name']=='Herald' else 'grub' if u['name']=='Grub' else 'blue' if u['name']=='Blue' else 'camp'
                        size=min(self.world_size(34 if kind=='boss' else 27),52 if kind=='boss' else 38)
                        key='monsters/'+u['name']+'.png'
                        self.icon(key if key in self.icons else 'icons/'+icon+'.png',*p,size,True)
                        if s[3]<s[4]:self.bar(p[0]-size//2,p[1]-size//2-9,size,max(4,self.world_size(2)),s[3]/s[4],GOLD)
                        if self.camera[2]>1.5:self.text({'Blue':'블루','Red':'레드','Gromp':'두꺼비','Wolves':'늑대','Raptors':'칼날부리','Krugs':'돌거북','Dragon':'드래곤','Baron':'바론','Grub':'공허 유충','Herald':'협곡의 전령'}[u['name']],p[0],p[1]+size//2+4,14,GOLD,anchor='center')
                elif kind=='pet':
                    size=20;self.icon('champions/Sion.png' if u['name']=='최후의 영광' else 'champions/Annie.png',*p,size,True)
                    self.text(u['name'],p[0],p[1]+size//2+4,14,color,anchor='center')
            # Clear launch and impact cues, not anonymous dots: melee arc,
            # projectile trail, impact ring, damage value and target health.
            for e in self.frame['effects']:
                if self.meta[e['a']]['kind']=='minion':continue
                age=self.time-e['t']
                if age<0 or age>.6:continue
                p=self.xy(e['p']);kind=e['kind'];color=(197,146,248) if e['magic'] else (251,221,148)
                if kind=='impact':
                    pg.draw.circle(self.screen,color,p,round(5+age*25),2)
                    if e['value']>0 and self.camera[2]>1.4 and self.meta[e['b']]['kind'] in ('champion','boss'):
                        self.text(e['value'],p[0],p[1]-30-age*30,11,color,True,'center')
                elif kind=='melee':
                    start=self.xy(e['start']);radius=14;pg.draw.line(self.screen,color,start,p,3);pg.draw.arc(self.screen,color,pg.Rect(p[0]-radius,p[1]-radius,radius*2,radius*2),age*8,age*8+2.4,3)
                elif kind=='blink':
                    pg.draw.circle(self.screen,(143,177,248),p,round(9+age*30),2)
                elif kind=='ranged':
                    origin=self.xy(e['start']);progress=min(1,age/.28)
                    point=(round(origin[0]+(p[0]-origin[0])*progress),round(origin[1]+(p[1]-origin[1])*progress))
                    pg.draw.line(self.screen,color,(round(point[0]-(p[0]-origin[0])*.1),round(point[1]-(p[1]-origin[1])*.1)),point,2)
                    pg.draw.circle(self.screen,color,point,3)
            for p in self.frame['missiles']:
                if self.meta[p['a']]['kind']=='minion':continue
                duration=p['t']-self.frame['t']
                origin=self.xy(p['origin']);end=self.xy(p['p']);total=max(.05,math.dist(p['origin'],p['p'])/(300 if p['kind']=='attack' else 240));f=max(0,min(1,1-(p['t']-self.time)/total))
                point=(round(origin[0]+(end[0]-origin[0])*f),round(origin[1]+(end[1]-origin[1])*f));color=(230,190,113) if p['kind']=='attack' else (164,171,251)
                tail=(round(point[0]-(end[0]-origin[0])*.08),round(point[1]-(end[1]-origin[1])*.08));pg.draw.line(self.screen,color,tail,point,2);pg.draw.circle(self.screen,color,point,3)
            for a in self.frame['areas']:
                pg.draw.circle(self.screen,(159,119,195) if a['kind']=='zone' else (164,184,99),self.xy(a['p']),max(2,round(a['r']*r.h/512*self.camera[2])),1)
            if self.phase=='clip':
                start=bisect.bisect_left(self.etimes,self.time-1.2)
                end=bisect.bisect_right(self.etimes,self.time)
                for event in self.events[start:end]:
                    if event['type'] not in ('summoner','summoner_arrival'):continue
                    x,y=self.xy(event['p'])
                    self.text(SUMMONERS[event['spell']][0],x,y-45,14,GOLD,True,'center')
        self.screen.set_clip(None);pg.draw.rect(self.screen,LINE,r,1)
        label='전체 맵 · 초반 배치' if self.phase=='opening' else '전체 맵' if self.phase!='clip' or self.overview else self.data['clips'][self.clip_index]['label']+' · 1배속'
        pg.draw.rect(self.screen,(12,20,27),(r.x+10,r.y+10,430,56 if self.phase=='clip' else 33));self.text(label,r.x+21,r.y+17,14,GOLD,True)
        if self.phase=='clip':
            anchors=self.data['clips'][self.clip_index]['anchors'];anchor=next((e for e in anchors if e['t']>=self.time-.8),anchors[-1])
            names=[self.player_name(i) for i in anchor['ids'][:2] if self.meta[i]['kind']=='champion']
            context=' vs '.join(names) if names else anchor['label']
            self.text(context,r.x+21,r.y+39,14,TEXT,True)
    def objectives(self):
        self.text('주요 오브젝트',30,150,18,GOLD,True)
        for i,name in enumerate(('Dragon','Grub','Herald','Baron')):
            y=194+i*88;pg.draw.rect(self.screen,(14,24,31),(22,y,234,76),border_radius=4)
            element=self.frame['element'] if self.frame else 'infernal';icon='dragon_'+element if name=='Dragon' else 'grub' if name=='Grub' else 'herald' if name=='Herald' else 'baron'
            self.icon('icons/'+icon+'.png',47,y+33,32)
            label=ELEMENT[element]+' 드래곤' if name=='Dragon' else '공허 유충' if name=='Grub' else '협곡의 전령' if name=='Herald' else '바론 내셔';self.text(label,74,y+10,14,TEXT,True)
            units=[s for uid,s in self.states.items() if self.meta[uid]['name']==name];living=sum(s[3]>0 for s in units);nextspawn=min((s[5] for s in units if s[5]>self.time),default=0)
            state=(f'{living}/3 생존' if name=='Grub' else '등장 중') if living else '등장 '+clock(nextspawn-self.time) if nextspawn else '대기 / 종료'
            self.text(state,74,y+39,14,GOLD if living else MUTED)
        if self.frame:
            self.text('유충  '+str(self.frame['grubs'][0])+' : '+str(self.frame['grubs'][1]),32,555,14,MUTED)
    def header(self):
        self.text('RIFT / MANAGER',20,12,18,GOLD,True);self.text('REBUILD',230,17,11,MUTED)
        self.button('pause','계속' if self.paused else '일시정지',(1190,8,100,34),self.paused)
        self.text('하이라이트 1x',1000,18,14,GOLD,True)
        self.button('camera','전체 맵' if self.overview else '자동 카메라',(1300,8,130,34),self.overview);self.button('new','새 경기',(1440,8,132,34))
        pg.draw.rect(self.screen,(13,22,29),(200,48,1200,51));pg.draw.rect(self.screen,LINE,(200,48,1200,51),1)
        for team in (0,1):
            ps=[p for p in self.players if p['team']==team];color=BLUE if team==0 else RED
            self.text('BLUE' if team==0 else 'RED',222 if team==0 else 1378,58,22,color,True,'left' if team==0 else 'right')
            self.text(sum(p['k'] for p in ps),708 if team==0 else 892,52,28,color,True,'center')
            self.text(f'{sum(p["gold"] for p in ps)/1000:.1f}K G',358 if team==0 else 1240,62,16,MUTED,anchor='left' if team==0 else 'right')
            if self.frame:
                for i,e in enumerate(self.frame['dragons'][team][-5:]):self.icon(f'icons/dragon_{e}.png',540+i*25 if team==0 else 1060-i*25,74,20)
                for i,(icon,key) in enumerate((('grub','grubs'),('herald','herald'),('baron','barons'))):
                    x=(440 if team==0 else 1160)+(i*29 if team==0 else -i*29)
                    self.icon(f'icons/{icon}.png',x,63,13)
                    self.text(self.frame.get(key,[0,0])[team],x,72,11,MUTED,anchor='center')
        self.text(clock(self.time),800,59,22,TEXT,True,'center');self.text(f'{self.fps:.0f} FPS',1573,56,11,MUTED,anchor='right')
    def commentary(self):
        if self.phase=='loading':return f'새 매치엔진이 경기를 계산하고 있습니다 · {clock(self.progress)}',MUTED
        if self.phase=='opening':return '양 팀이 초반 배치를 시작합니다. 정글러는 첫 캠프, 라이너는 담당 라인으로 이동합니다.',TEXT
        if self.phase=='overview':return '다음 주요 장면으로 이동합니다. 교전 장소를 확인한 뒤 정속으로 중계합니다.',MUTED
        if self.phase=='ended':return ('넥서스가 파괴됐습니다! '+('블루' if self.data['result']['winner']==0 else '레드')+' 팀 승리.' if self.data['result']['finished'] else '저장된 장면 재생 종료'),GOLD
        if self.phase=='error':return '경기 계산 오류 · runs/error.txt 확인',RED
        clip=self.data['clips'][self.clip_index];idx=bisect.bisect_right(self.etimes,self.time)
        for e in reversed(self.events[max(0,idx-40):idx]):
            if self.time-e['t']>4:break
            if e['type']=='kill':
                a=self.meta[e['killer']];b=self.meta[e['victim']];return f'{self.player_name(e["killer"])}! {obj(self.player_name(e["victim"]))} 잡아냅니다. '+('동료들의 합류가 킬로 이어집니다.' if e['assists'] else '일대일 승부에서 승리합니다.'),BLUE if a['team']==0 else RED
            if e['type']=='objective':return ('블루' if e['team']==0 else '레드')+' 팀이 '+obj({'Dragon':ELEMENT.get(e.get('element'),'')+' 드래곤','Grub':'공허 유충','Herald':'협곡의 전령','Baron':'바론 내셔'}[e['name']])+' 확보합니다!',GOLD
            if e['type']=='structure':return ('블루' if e['team']==0 else '레드')+' 팀이 건물을 파괴합니다. 진격로가 열립니다!',GOLD
        return {'솔로 킬':'일대일 승부! 교전 중인 두 선수를 따라갑니다.','한타':'양 팀이 맞붙습니다! 진입과 후속 공격을 지켜보세요.','갱킹':'정글러가 라인에 개입합니다.','교전':'양 팀 선수가 맞붙습니다.'}.get(clip['label'],clip['label']+' 장면 · 해당 오브젝트와 공격 중인 선수들을 따라갑니다.'),TEXT
    def lower(self):
        message,color=self.commentary();pg.draw.rect(self.screen,(18,27,36),(18,588,1564,49));pg.draw.rect(self.screen,color,(18,588,4,49));self.text(clock(self.time),36,603,16,GOLD,True);self.text(message,118,601,18,color,True)
        for i,(key,label) in enumerate((('items','아이템'),('gold','골드 그래프'),('damage','한타 딜량'))):self.button(key,label,(18+i*152,645,142,35),self.tab==key)
        if self.data:self.text(f'{min(self.clip_index+1,len(self.data["clips"]))} / {len(self.data["clips"])} 주요 장면',1265,655,14,MUTED,anchor='right')
        self.button('prev','이전 장면',(1280,645,143,35));self.button('next','다음 장면',(1433,645,149,35))
        if self.phase=='ended' and self.data['clips']:
            self.button('replay','하이라이트 다시 보기',(520,645,230,35),True)
        pg.draw.rect(self.screen,(13,22,29),(18,688,1564,194));pg.draw.rect(self.screen,LINE,(18,688,1564,194),1)
        if self.tab=='items':self.table()
        elif self.tab=='gold':self.goldgraph()
        else:self.damagegraph()
    def table(self):
        mx,my=pg.mouse.get_pos()
        cursor=self.logical_pos((mx,my))
        tooltip=None
        for team in (0,1):
            x=30+team*787;color=BLUE if team==0 else RED
            for xx,label in ((0,'선수 / 포지션'),(176,'Lv'),(251,'K / D / A'),(365,'CS'),(404,'골드'),(455,'주문'),(514,'룬'),(551,'아이템')):self.text(label,x+xx,696,14,color if xx==0 else MUTED,xx==0)
            players=[p for p in self.players if p['team']==team]
            for i,p in enumerate(players):
                y=726+i*29;pg.draw.line(self.screen,LINE,(x,y+25),(x+756,y+25))
                self.icon(f'champions/{p["name"]}.png',x+13,y+10,20,True);self.text(self.player_name(p['id']),x+30,y,14,TEXT,True);self.text(KO_ROLE[p['role']],x+205,y,14,color)
                self.text(p['level'],x+176,y,14,GOLD,True)
                self.text(f'{p["k"]} / {p["d"]} / {p["a"]}',x+251,y,14);self.text(p['cs'],x+365,y,14,MUTED);self.text(f'{p["gold"]/1000:.1f}K',x+404,y,14,GOLD)
                for j,(spell,ready) in enumerate(p.get('summoners',{}).items()):
                    sx=x+463+j*24
                    self.icon(f'summoners/{spell}.png',sx,y+10,20)
                    if ready>self.time:
                        pg.draw.rect(self.screen,BG,(sx-10,y+8,20,12))
                        remaining=math.ceil(ready-self.time)
                        self.text(remaining,sx,y+8,11,TEXT,anchor='center')
                rune=p.get('rune')
                if rune:
                    self.icon(f'runes/{rune}.png',x+522,y+10,23)
                    if pg.Rect(x+510,y-2,24,24).collidepoint(cursor):
                        tooltip=(x+522,y,RUNE_NAMES[rune])
                for j in range(6):
                    pg.draw.rect(self.screen,LINE,(x+548+j*30,y-1,25,25),1)
                    if j<len(p['items']):self.icon(f'items/{p["items"][j]}.png',x+560+j*30,y+11,23)
                self.bar(x+31,y+21,140,3,p['hp']/max(1,p['maxhp']),color)
                if p['hp']<=0:self.text(clock(p['respawn']-self.time),x+755,y,11,MUTED,anchor='right')
        if tooltip:
            x,y,label=tooltip
            pg.draw.rect(self.screen,BG,(x-76,y-31,152,25),border_radius=3)
            pg.draw.rect(self.screen,GOLD,(x-76,y-31,152,25),1,border_radius=3)
            self.text(label,x,y-27,14,GOLD,anchor='center')
    def goldgraph(self):
        self.text('팀 누적 골드 차이',42,699,16,GOLD,True)
        if not self.data:return
        idx=bisect.bisect_right(self.times,self.time);frames=self.data['frames'][:idx:40]+[self.frame];values=[sum(p['gold']*(1 if p['team']==0 else -1) for p in f['players']) for f in frames];peak=max(1000,max(map(abs,values),default=1000))
        pg.draw.line(self.screen,MUTED,(80,787),(1520,787));points=[(80+1440*f['t']/max(60,self.time),787-v/peak*48) for f,v in zip(frames,values)]
        for a,b in zip(points,points[1:]):pg.draw.line(self.screen,BLUE if b[1]<787 else RED,a,b,2)
        self.text('00:00',80,850,14,MUTED);self.text(clock(self.time),1520,850,14,MUTED,anchor='right')
        if values:self.text(('블루' if values[-1]>=0 else '레드')+f' +{abs(values[-1]):,} G',1540,699,16,BLUE if values[-1]>=0 else RED,True,'right')
    def damagegraph(self):
        self.text('현재 주요 장면 · 챔피언 대상 피해량',42,699,16,GOLD,True)
        values={p['id']:max(0,p['damage']-self.base_damage.get(p['id'],p['damage'])) for p in self.players};peak=max(100,max(values.values(),default=100))
        for team in (0,1):
            x=40+team*788;color=BLUE if team==0 else RED
            for i,p in enumerate(a for a in self.players if a['team']==team):
                y=732+i*28;self.icon(f'champions/{p["name"]}.png',x+12,y+8,20,True);self.text(self.player_name(p['id']),x+30,y-2,14);self.bar(x+220,y,420,14,values[p['id']]/peak,color);self.text(f'{values[p["id"]]:,}',x+715,y-2,14,color,True,'right')
    def toggle_fullscreen(self):
        if self.headless:return
        if self.fullscreen:
            self.window=pg.display.set_mode(self.windowed_size,pg.RESIZABLE)
        else:
            self.windowed_size=self.window.get_size()
            self.window=pg.display.set_mode((0,0),pg.FULLSCREEN)
        self.fullscreen=not self.fullscreen

    def display_rect(self):
        width,height=self.window.get_size()
        scale=min(width/W,height/H)*self.display_scale/100
        rect=pg.Rect(0,0,max(1,round(W*scale)),max(1,round(H*scale)))
        rect.center=(width//2,height//2)
        return rect

    def logical_pos(self,pos):
        rect=self.display_rect()
        return ((pos[0]-rect.x)*W/rect.w,(pos[1]-rect.y)*H/rect.h)

    def save_display(self):
        if self.headless:return
        try:
            (HOME/'display.json').write_text(json.dumps(dict(scale=self.display_scale,sharp=self.sharp)),encoding='utf-8')
        except OSError:
            pass

    def display_settings(self):
        self.buttons={}
        panel=pg.Rect(500,315,600,246)
        pg.draw.rect(self.screen,BG,panel,border_radius=8)
        pg.draw.rect(self.screen,GOLD,panel,1,border_radius=8)
        self.text('화면 설정',530,337,22,GOLD,True)
        self.text('화면 크기',530,393,16)
        for i,size in enumerate((70,85,100)):
            self.button(f'size_{size}',f'{size}%',(690+i*120,382,108,35),self.display_scale==size)
        self.text('확대 방식',530,445,16)
        self.button('smooth','부드럽게',(690,434,108,35),not self.sharp)
        self.button('sharp','픽셀 유지',(810,434,108,35),self.sharp)
        self.button('close_settings','닫기',(940,501,138,36))
        self.button('exit_game','게임 종료',(530,501,138,36))

    def draw(self,dt):
        self.text_draws=[]
        started=time.perf_counter();self.screen.fill(BG);self.buttons={}
        if self.flow=='draft':
            self.draw_draft()
        elif self.management:
            self.manager.draw()
        else:
            self.map_draw(dt);self.objectives();self.header();self.lower()
            if self.phase=='loading':
                pg.draw.rect(self.screen,(12,21,29),(620,280,600,100))
                self.text('경기 준비 중',920,303,18,GOLD,True,'center')
            self.button('career_home','밴픽' if self.match_only else '테스트 메뉴' if self.viewer_only else '구단',(900,8,86,34))
        self.button('settings','설정',(1094,8,86,34))
        if self.settings_open:self.display_settings()
        rect=self.display_rect()
        self.window.fill(BG)
        resize=pg.transform.scale if self.sharp else pg.transform.smoothscale
        self.window.blit(self.screen if rect.size==(W,H) else resize(self.screen,rect.size),rect)
        if not self.headless:self.native_text(rect)
        pg.display.flip();self.render_ms.append((time.perf_counter()-started)*1000);self.render_ms=self.render_ms[-300:]
    def click(self,pos):
        pos=self.logical_pos(pos)
        for key,r in self.buttons.items():
            if not r.collidepoint(pos):continue
            if key.startswith('draft_'):self.draft_click(key)
            elif key=='career_match':
                state=self.manager.career.state
                if not state or len(state.get('roster',[]))!=5:
                    self.manager.notice='포지션별 선수 5명을 선발한 뒤 밴픽으로 경기를 시작합니다.'
                else:self.open_draft()
            elif key=='career_home':
                if self.match_only:self.open_draft()
                elif self.viewer_only:self.running=False
                else:self.flow='career';self.management=True
            elif key.startswith('career_') or key.startswith('page_'):self.manager.click(key)
            elif key=='settings':self.settings_open=True
            elif key=='close_settings':self.settings_open=False
            elif key=='exit_game':self.running=False
            elif key.startswith('size_'):
                self.display_scale=int(key.split('_')[1]);self.save_display()
            elif key in ('smooth','sharp'):
                self.sharp=key=='sharp';self.save_display()
            elif key in ('items','gold','damage'):self.tab=key
            elif key=='pause':self.paused=not self.paused
            elif key=='camera':self.overview=not self.overview
            elif key=='new':self.start(self.seed+1,self.roster,self.labels)
            elif key=='replay' and self.phase=='ended':
                self.paused=False
                self.choose(0)
            elif self.data and key in ('prev','next'):self.choose(max(0,self.clip_index+(-1 if key=='prev' else 1)))
            break
    def run(self,frames=None,screenshot=None):
        count=0;deadline=previous=time.perf_counter();samples=[]
        while self.running:
            deadline+=1/60;remaining=deadline-time.perf_counter()
            if remaining>.0006:time.sleep(remaining-.0006)
            while time.perf_counter()<deadline:pass
            now=time.perf_counter();dt=min(.1,now-previous);previous=now
            if now-deadline>.1:deadline=now
            samples.append(dt);samples=samples[-120:];self.fps=len(samples)/max(.001,sum(samples))
            for e in pg.event.get():
                if e.type==pg.QUIT:self.running=False
                elif e.type==pg.MOUSEBUTTONDOWN and e.button==1:self.click(e.pos)
                elif e.type==pg.TEXTEDITING and self.management and self.manager.input_active:
                    self.manager.composition=e.text
                elif e.type==pg.TEXTINPUT and self.management and self.manager.input_active:
                    field='manager_name' if self.manager.input_field=='manager' else 'name'
                    if self.manager.select_all:setattr(self.manager,field,'')
                    self.manager.select_all=False
                    setattr(self.manager,field,(getattr(self.manager,field)+e.text)[:30])
                    self.manager.composition=''
                elif e.type==pg.KEYDOWN:
                    if e.key==pg.K_F11:
                        self.toggle_fullscreen()
                        continue
                    if self.management and self.manager.input_active:
                        if e.key==pg.K_a and e.mod & pg.KMOD_CTRL:
                            self.manager.select_all=True
                        elif e.key==pg.K_BACKSPACE:
                            field='manager_name' if self.manager.input_field=='manager' else 'name'
                            if self.manager.select_all:setattr(self.manager,field,'')
                            elif not self.manager.composition:setattr(self.manager,field,getattr(self.manager,field)[:-1])
                            self.manager.select_all=False
                        elif e.key==pg.K_RETURN:self.manager.input_active=False;pg.key.stop_text_input()
                        continue
                    if e.key==pg.K_SPACE:self.paused=not self.paused
                    elif e.key==pg.K_ESCAPE:
                        if self.settings_open:self.settings_open=False
                        else:self.overview=not self.overview
                    elif e.key in (pg.K_LEFT,pg.K_RIGHT) and self.data:self.choose(max(0,self.clip_index+(-1 if e.key==pg.K_LEFT else 1)))
            try:
                if not self.settings_open and self.flow!='draft' and not self.management:self.update(dt)
                self.draw(dt)
            except Exception:
                self.error=traceback.format_exc();(HOME/'runs'/'error.txt').write_text(self.error,encoding='utf-8');raise
            count+=1
            if frames and count>=frames:break
        if screenshot:pg.image.save(self.screen,str(screenshot))
    def close(self):
        if self.proc and self.proc.is_alive():self.proc.terminate();self.proc.join(2)
        pg.quit()
def main():
    mp.freeze_support()
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--seed',type=int,default=1);p.add_argument('--headless',action='store_true');p.add_argument('--match',action='store_true');p.add_argument('--frames',type=int);p.add_argument('--screenshot',type=Path);a=p.parse_args();app=App(a.seed,a.headless,match_only=a.match)
    try:app.run(a.frames,a.screenshot)
    finally:app.close()
if __name__=='__main__':main()
