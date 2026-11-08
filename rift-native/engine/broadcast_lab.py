"""Manual draft front end on the recovered original SDL spectator, not a new renderer."""
import hashlib,time,multiprocessing as mp,queue,bisect
from pathlib import Path
import pygame as pg
from legacy_viewer import App,ASSETS,HOME,W,H,BG,BLUE,RED,GOLD,TEXT,MUTED,LINE,KO_ROLE
from legacy_replay import worker,clips
from data import KITS,ROLES,KEYSTONES,RUNE_NAMES
from champion_catalog import CATALOG,display_name
import series_state,manual_draft

class BroadcastLab(App):
    def __init__(self):
        self.best_of=3;self.query='';self.filter='ALL';self.pool_page=0;self.selection=None;self.swap_first=None
        self.mode='draft';self.action_error='';self.portraits={};self.draft_thread=None;self.draft_loaded=None
        self.rune_choices={role:None for role in ROLES};self.rune_edit=None;self.finished_stream=False;self.waiting_index=0
        super().__init__(int(time.time())%100000000)
        pg.display.set_caption('RIFT MANAGER · 매치엔진 / 직접 밴픽')
        for path in (ASSETS/'loading').glob('*.jpg'):self.portraits[path.stem]=pg.image.load(str(path)).convert()
        pg.key.start_text_input()

    def start(self,seed):
        if self.proc and self.proc.is_alive():self.proc.terminate();self.proc.join(2)
        self.seed=seed;self.data=None;self.loaded=None;self.error=None;self.frame=None;self.time=0;self.progress=0
        self.phase='draft';self.mode='draft';self.camera=[256.,256.,1.];self.players=[];self.states={};self.positions={}
        self.series=dict(score=[0,0],sets=[],chooser=0,feedback=[],best_of=self.best_of,fearless=True,autoplay=False)
        series_state.next_choice(self.series,self.seed)
        self.selection=None;self.swap_first=None;self.query='';self.pool_page=0;self.action_error='';self.bot_due=0
        self.mail=None;self.proc=None;self.result_recorded=False
        self.rune_choices={role:None for role in ROLES};self.rune_edit=None;self.finished_stream=False;self.waiting_index=0

    def choose_initial(self,category,value):
        if series_state.submit_choice(self.series,self.seed,category,value):
            manual_draft.start(self.series);self.selection=None;self.pool_page=0;self.bot_due=time.monotonic()+.7

    def legal_choice(self,name):
        return manual_draft.legal(self.series,name,KITS,ROLES)

    def draft_action(self,name):
        try:
            manual_draft.submit(self.series,name,KITS,ROLES,time.time(),self.series['draft_version'])
            self.selection=None;self.action_error='';self.bot_due=time.monotonic()+.7
        except ValueError as error:self.action_error=str(error)

    def auto_remaining(self):
        try:
            manual_draft.bot(self.series,self.seed,KITS,ROLES,time.time(),all_teams=True)
            self.selection=None
        except ValueError as error:self.action_error=str(error)

    def launch_set(self):
        self.mode='watch';self.phase='loading';self.frame=None;self.data=None;self.loaded=None;self.paused=False;self.overview=False
        self.players=[];self.states={};self.positions={};self.camera=[256.,256.,1.];self.result_recorded=False
        self.time=0;self.progress=0;self.load_error=None;self.error=None
        self.finished_stream=False;self.waiting_index=0
        (HOME/'runs').mkdir(parents=True,exist_ok=True)
        roster=self.series['roster'];key=hashlib.sha256(repr(roster).encode()).hexdigest()[:12]
        rune_key=hashlib.sha256(repr(self.rune_choices).encode()).hexdigest()[:8]
        path=HOME/'runs'/f'{self.seed}-{len(self.series["sets"])}-{key}-{rune_key}.json.gz'
        self.current_roster=roster
        if path.exists():self.load_async(path)
        else:self.spawn(path)

    def spawn(self,path):
        self.mail=mp.get_context('spawn').Queue()
        runes={str(self.series['blue'])+':'+role:key for role,key in self.rune_choices.items() if key}
        self.proc=mp.get_context('spawn').Process(target=worker,args=(self.seed+len(self.series['sets']),str(path),self.mail,self.current_roster,runes),daemon=True)
        self.proc.start()

    def poll(self):
        if self.load_error:self.error=self.load_error;self.load_error=None;self.phase='error'
        if self.mail:
            for _ in range(12):
                try:packet=self.mail.get_nowait()
                except queue.Empty:break
                if packet['type']=='error':self.error=packet['message'];self.phase='error'
                elif packet['type']=='done':self.load_async(packet['path'])
                elif packet['type']=='live':
                    if self.data is None:
                        self.data=dict(frames=[],events=[],meta=[],clips=[],result={'finished':False,'winner':None})
                        self.times=[];self.events=self.data['events'];self.etimes=[];self.meta={};self.base_damage={}
                    self.data['frames'].extend(packet['frames']);self.times.extend(frame['t'] for frame in packet['frames'])
                    self.data['meta'].extend(packet['meta']);self.meta.update({unit['id']:unit for unit in packet['meta']})
                    self.events.extend(packet['events']);self.etimes.extend(event['t'] for event in packet['events'])
                    if self.times:
                        self.data['clips']=clips(self.events,self.times[-1])
                        self.openend=min(90,self.data['clips'][0]['start']) if self.data['clips'] else 90
                        if self.phase=='loading':self.phase='opening';self.phase_time=0;self.time=0;self.update_frame()
        if self.loaded:
            phase,watch_time,index=self.phase,self.time,self.clip_index
            self.data=self.loaded;self.loaded=None;self.finished_stream=True
            self.meta={u['id']:u for u in self.data['meta']};self.times=[f['t'] for f in self.data['frames']]
            self.events=self.data['events'];self.etimes=[e['t'] for e in self.events]
            self.openend=min(90,self.data['clips'][0]['start']) if self.data['clips'] else 90
            if phase=='loading':self.phase='opening';self.phase_time=0;self.time=0;self.clip_index=0;self.base_damage={}
            else:self.time=watch_time;self.clip_index=index
            self.update_frame()

    def choose(self,index):
        if index>=len(self.data['clips']) and not self.finished_stream:
            self.phase='live_wait';self.waiting_index=index;return
        super().choose(index)

    def update(self,dt):
        s=self.series;now=time.time()
        if self.mode=='watch':
            self.poll()
            if self.phase=='live_wait' and self.data:
                # A still-growing clip may acquire its post-roll in the next batch.
                if self.waiting_index>0 and self.clip_index==self.waiting_index-1 and self.clip_index<len(self.data['clips']) and self.time<self.data['clips'][self.clip_index]['end']:
                    self.phase='clip'
                elif self.waiting_index<len(self.data['clips']) or self.finished_stream:self.choose(self.waiting_index)
            super().update(dt)
            if self.data and self.times and self.time>self.times[-1]:self.time=self.times[-1];self.update_frame()
            if s.get('skip_viewing') and self.data and self.finished_stream and self.phase not in ('ended','error'):self.phase='ended'
            if self.phase=='ended' and self.data and self.finished_stream and not self.result_recorded:
                from series import Draft
                result=dict(self.data['result']);result['highlights']=[{k:c[k] for k in ('start','end','label')} for c in self.data['clips']]
                draft=Draft(s['first'],s['blue'],tuple(s['draft']),tuple(tuple(row) for row in s['roster']))
                series_state.set_complete(s,result,draft,now);self.result_recorded=True
            if self.result_recorded and s['phase']=='feedback' and (s.get('autoplay') or now>=s['feedback_until']):
                series_state.next_choice(s,self.seed,now);self.mode='draft';self.phase='draft';self.selection=None
            return
        if series_state.tick(s,self.seed,now) and s['phase']=='draft_pending':
            manual_draft.start(s);self.auto_remaining()
        if s['phase']=='draft' and (s.get('autoplay') or now>=s.get('response_until',now+180)):
            s['autoplay']=True;s['skip_viewing']=True;self.auto_remaining()
        if s['phase']=='draft' and time.monotonic()>=self.bot_due:
            _,team=manual_draft.order(s['first'])[len(s['draft'])]
            if team==1:
                import random
                candidates=sorted(KITS);random.Random(self.seed+s['draft_version']*97).shuffle(candidates)
                name=next((name for name in candidates if self.legal_choice(name)),None)
                if name:self.draft_action(name)
        if series_state.finish_swap(s,now):self.launch_set()

    def card_art(self,name,rect,selected=False):
        rect=pg.Rect(rect)
        if name in self.portraits:
            key=(name,rect.w,rect.h)
            if key not in self.scaled:
                image=self.portraits[name];scale=max(rect.w/image.get_width(),rect.h/image.get_height())
                image=pg.transform.smoothscale(image,(round(image.get_width()*scale),round(image.get_height()*scale)))
                self.scaled[key]=image.subsurface(pg.Rect((image.get_width()-rect.w)//2,0,rect.w,rect.h)).copy()
            self.screen.blit(self.scaled[key],rect)
        else:
            pg.draw.rect(self.screen,(17,30,42),rect)
            if name:self.icon('champions/'+name+'.png',rect.centerx,rect.centery,72)
        if selected:pg.draw.rect(self.screen,GOLD,rect,3)

    def draft_draw(self):
        s=self.series;phase=s['phase'];self.screen.fill((8,13,22));self.buttons={}
        self.text('RIFT / MANAGER',20,16,22,GOLD)
        self.text('직접 밴픽 · 피어리스',800,19,18,TEXT,anchor='center')
        self.button('series3','새 BO3',(1350,10,108,36));self.button('series5','새 BO5',(1468,10,108,36))
        active=manual_draft.order(s.get('first',0))[len(s.get('draft',[]))] if phase=='draft' else None
        for side in (0,1):
            team=0 if s.get('blue',0)==side else 1;color=BLUE if side==0 else RED
            x0=20 if side==0 else 950
            self.text(('BLUE' if side==0 else 'RED')+(' · 우리 팀' if team==0 else ' · 상대 팀'),x0,64,18,color)
            bans=[a['champion'] for a in s.get('draft',[]) if a['action']=='ban' and a['team']==team]
            for i in range(5):
                x=x0+340+i*55;pg.draw.rect(self.screen,LINE,(x,58,46,46))
                if i<len(bans):
                    self.icon('champions/'+bans[i]+'.png',x+23,81,44)
                    pg.draw.line(self.screen,RED,(x+3,100),(x+43,61),3)
            picks=s.get('draft_picks',[[],[]])[team]
            roster=s.get('roster')
            if roster:cards=roster[side]
            else:cards=picks+['']*(5-len(picks))
            for i,name in enumerate(cards):
                x=x0+i*126;rect=pg.Rect(x,119,120,273)
                self.card_art(name,rect,self.swap_first==i and team==0)
                pg.draw.rect(self.screen,color if active and active[1]==team else LINE,rect,2)
                shade=pg.Surface((120,56),pg.SRCALPHA);shade.fill((3,9,16,225));self.screen.blit(shade,(x,336))
                self.text(display_name(name) if name else '선택 대기',x+60,344,14,TEXT,anchor='center')
                self.text(KO_ROLE[ROLES[i]] if roster else f'PICK {i+1}',x+60,370,14,color,anchor='center')
                if phase=='swap' and team==0:self.buttons['swapcard:'+str(i)]=rect
        center=pg.Rect(650,58,292,334);pg.draw.rect(self.screen,(3,8,15),center)
        self.text('SERIES BAN',796,64,16,GOLD,anchor='center')
        blocked=s.get('fearless_bans',[])
        for i,name in enumerate(blocked):self.icon('champions/'+name+'.png',670+(i%10)*28,100+(i//10)*26,24)
        if not blocked:self.text('1세트 · 이전 픽 없음',796,105,14,MUTED,anchor='center')
        self.text('BLUE    vs    RED',796,221,18,TEXT,anchor='center')
        blue=s.get('blue',0);score=s['score']
        self.text(f'{score[blue]}  :  {score[1-blue]}',796,251,28,TEXT,anchor='center')
        self.text(f"BO{s['best_of']} · SET {len(s['sets'])+1}",796,294,16,GOLD,anchor='center')
        first='우리 팀' if s.get('first',0)==0 else '상대 팀'
        if phase!='choice':self.text(first+' 선픽',796,326,14,MUTED,anchor='center')
        deadline=s.get('swap_until') if phase=='swap' else s.get('response_until')
        remaining=max(0,int((deadline or time.time())-time.time()))
        if phase=='choice':
            self.text('선픽·후픽 또는 진영을 선택하세요',800,423,22,TEXT,anchor='center')
            choice=s.get('choice')
            if choice:self.text('상대 선택 · '+choice['category']+' / '+choice['value'],800,463,16,MUTED,anchor='center')
            entries=[('priority','first','선픽'),('priority','second','후픽'),('side','blue','블루'),('side','red','레드')]
            entries=[e for e in entries if not choice or e[0]!=choice['category']]
            for i,(category,value,label) in enumerate(entries):self.button('initial:'+category+':'+value,label,(800-len(entries)*78+i*156,515,144,52))
            self.text(f'{remaining}초 · 3분 미응답 시 남은 시리즈 자동 진행',800,610,16,GOLD,anchor='center')
        elif phase=='swap':
            self.text('밴픽 완료 · 챔피언 스왑',800,449,28,GOLD,anchor='center')
            self.text(f'{remaining}초 후 경기 시작',800,503,22,TEXT,anchor='center')
            self.text('우리 팀 카드 두 개를 선택하면 포지션을 교환합니다.',800,554,18,TEXT,anchor='center')
            self.text('피어리스 금지: 이전 세트에서 양 팀이 사용한 모든 챔피언',800,610,16,MUTED,anchor='center')
            self.runes_draw()
        elif phase=='draft':self.pool_draw(active,remaining)
        if self.action_error:self.text(self.action_error[:105],20,864,14,RED)
        else:self.text('우리 차례에는 직접 선택 · 상대 차례에는 AI 선택 · 자동 밴픽은 선택 사항',20,866,14,MUTED)

    def runes_draw(self):
        own=self.series['roster'][self.series['blue']]
        self.text('우리 팀 룬 · 선수별로 변경',800,655,18,GOLD,anchor='center')
        for i,(role,name) in enumerate(zip(ROLES,own)):
            key=self.rune_choices[role] or KEYSTONES[name]
            self.button('rune:'+role,KO_ROLE[role]+' · '+RUNE_NAMES[key],(25+i*312,695,302,40),self.rune_edit==role)
        if self.rune_edit:
            for i,(key,name) in enumerate(RUNE_NAMES.items()):self.button('rune-set:'+key,name,(25+(i%6)*260,750+(i//6)*46,250,38),self.rune_choices[self.rune_edit]==key)

    def pool_draw(self,active,remaining):
        action,team=active;color=BLUE if team==self.series.get('blue',0) else RED
        self.text(('우리' if team==0 else '상대')+' 팀 '+('밴' if action=='ban' else '픽')+f" · {len(self.series['draft'])+1}/20",20,411,22,color)
        self.text(f'{remaining}초',1560,415,18,GOLD,anchor='right')
        pg.draw.rect(self.screen,(22,34,47),(20,453,365,36));self.buttons['search']=pg.Rect(20,453,365,36)
        self.text(self.query or '챔피언 검색 · 이름을 입력하세요',31,461,14,TEXT if self.query else MUTED)
        for i,role in enumerate(('ALL',)+ROLES):self.button('filter:'+role,'전체' if role=='ALL' else KO_ROLE[role],(400+i*104,453,96,36),self.filter==role)
        self.button('auto','남은 밴픽 자동',(1320,453,256,36))
        candidates=[name for name in sorted(KITS,key=display_name) if (self.filter=='ALL' or self.filter in KITS[name].roles) and (not self.query or self.query.replace(' ','').casefold() in (name+' '+KITS[name].ko).replace(' ','').casefold())]
        pages=max(1,(len(candidates)+41)//42);self.pool_page=min(self.pool_page,pages-1)
        unavailable=set(self.series.get('fearless_bans',[]))|set(self.series['draft_bans'])|set(sum(self.series['draft_picks'],[]))
        for i,name in enumerate(candidates[self.pool_page*42:(self.pool_page+1)*42]):
            x=20+(i%14)*112;y=502+(i//14)*100;rect=pg.Rect(x,y,104,93)
            pg.draw.rect(self.screen,(27,43,56) if name==self.selection else (13,24,35),rect)
            self.icon('champions/'+name+'.png',x+52,y+34,58)
            self.text(display_name(name),x+52,y+68,11,MUTED if name in unavailable else TEXT,anchor='center')
            if name in unavailable:
                dark=pg.Surface((104,93),pg.SRCALPHA);dark.fill((0,0,0,170));self.screen.blit(dark,rect)
                pg.draw.line(self.screen,RED,(x+30,y+57),(x+74,y+12),3)
            elif team==0:self.buttons['champ:'+name]=rect
            if name==self.selection:pg.draw.rect(self.screen,GOLD,rect,2)
        self.button('pool-prev','이전',(20,814,94,36));self.button('pool-next','다음',(124,814,94,36));self.text(f'{self.pool_page+1} / {pages}',242,824,14,MUTED)
        if self.selection:self.text(display_name(self.selection)+' · '+('밴' if action=='ban' else '픽')+'할 챔피언',470,824,18,GOLD)
        if team==0 and self.selection:self.button('confirm','밴 확정' if action=='ban' else '픽 확정',(1320,814,256,40),True)

    def draw(self,dt):
        if self.mode=='watch':
            super().draw(dt)
            return
        self.draft_draw()
        if self.window.get_size()==(W,H):self.window.blit(self.screen,(0,0))
        else:self.window.blit(pg.transform.smoothscale(self.screen,self.window.get_size()),(0,0))
        pg.display.flip()

    def click(self,pos):
        if self.mode=='watch':super().click(pos);return
        pos=(pos[0]*W/self.window.get_width(),pos[1]*H/self.window.get_height())
        key=next((key for key,rect in self.buttons.items() if rect.collidepoint(pos)),None)
        if key is None:return
        if key.startswith('initial:'):_,category,value=key.split(':');self.choose_initial(category,value)
        elif key.startswith('champ:'):self.selection=key[6:];self.action_error=''
        elif key=='confirm' and self.selection:self.draft_action(self.selection)
        elif key=='auto':self.auto_remaining()
        elif key.startswith('filter:'):self.filter=key[7:];self.pool_page=0
        elif key.startswith('rune:'):self.rune_edit=key[5:]
        elif key.startswith('rune-set:') and self.rune_edit:self.rune_choices[self.rune_edit]=key[9:];self.rune_edit=None
        elif key=='pool-prev':self.pool_page=max(0,self.pool_page-1)
        elif key=='pool-next':self.pool_page+=1
        elif key in ('series3','series5'):self.best_of=int(key[-1]);self.start(self.seed+1)
        elif key.startswith('swapcard:'):
            role=int(key.split(':')[1])
            if self.swap_first is None:self.swap_first=role
            else:
                try:
                    if self.swap_first!=role:series_state.swap(self.series,ROLES[self.swap_first],ROLES[role],self.series['swap_version'],time.time())
                    self.action_error=''
                except ValueError:self.action_error='해당 챔피언 조합은 두 포지션을 교환할 수 없습니다.'
                self.swap_first=None

    def run(self):
        clock=pg.time.Clock()
        while self.running:
            dt=min(.1,clock.tick(60)/1000);self.fps=clock.get_fps()
            for event in pg.event.get():
                if event.type==pg.QUIT:self.running=False
                elif event.type==pg.MOUSEBUTTONDOWN and event.button==1:self.click(event.pos)
                elif event.type==pg.TEXTINPUT and self.mode=='draft' and self.series['phase']=='draft':self.query=(self.query+event.text)[:40];self.pool_page=0
                elif event.type==pg.KEYDOWN:
                    if event.key==pg.K_F11:
                        full=not bool(self.window.get_flags()&pg.FULLSCREEN)
                        self.window=pg.display.set_mode((0,0) if full else (1280,720),pg.FULLSCREEN if full else pg.RESIZABLE)
                    elif self.mode=='draft' and event.key==pg.K_BACKSPACE:self.query=self.query[:-1];self.pool_page=0
                    elif self.mode=='draft' and event.key==pg.K_RETURN and self.selection:self.draft_action(self.selection)
                    elif self.mode=='watch':
                        if event.key==pg.K_SPACE:self.paused=not self.paused
                        elif event.key==pg.K_ESCAPE:self.overview=not self.overview
                        elif event.key in (pg.K_LEFT,pg.K_RIGHT) and self.data:self.choose(max(0,self.clip_index+(-1 if event.key==pg.K_LEFT else 1)))
            self.update(dt);self.draw(dt)

def main():
    mp.freeze_support();app=BroadcastLab()
    try:app.run()
    finally:app.close()

if __name__=='__main__':main()
