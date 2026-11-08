"""Persistent local club career and native management dashboard."""
import json,random,math
from pathlib import Path
import pygame as pg

PAGES=('대시보드','뉴스 사이트','우편함','전술','훈련','스탭','1군','2군 · 3군','달력',
       '선수간 관계','의료 센터','선수 데이터베이스','이적 활동','영입 명단','영입 예산',
       '스탭 검색','스탭 이적 활동','재정','대회','데이터 허브','구단 비전','내 프로필','챔피언 도감','운영자')
PHASES=((10,'스토브'),(60,'정규리그'),(70,'세계대회'),(72,'결산'))

ROLES=('TOP','JUNGLE','MID','ADC','SUPPORT')
ATTRIBUTES=('라인전','교전','운영','시야','협동','멘탈')
MANAGER_STATS=('전술','훈련','협상','동기부여','선수관리','스카우팅')

RESERVED_NICKS={n.casefold() for n in (
    'Ambition','Score','Bengi','MaRin','Bang','Wolf','Mata','MadLife','PraY','GorillA',
    'Uzi','Clearlove','MLXG','DanDy','Dade','imp','PawN','Deft','Rookie','TheShy',
    'Faker','Doublelift','Bjergsen','Sneaky','Rekkles','xPeke','Soaz','Yellowstar',
    'Diamondprox','Alex Ich','Froggen','Toyz','Stanley','Looper','inSec','Dyrus','Hai'
)}

def candidates(used_names=(),used_nicks=()):
    rng=random.SystemRandom()
    surnames=('김','이','박','최','정','강','조','윤','장','임','한','오','서','신','권','황','안','송','유','홍')
    first=('민','서','도','시','지','예','준','현','하','태','수','건','진','성','재','우','승','정','찬','영')
    last=('준','윤','우','호','빈','혁','성','현','훈','원','민','진','환','겸','찬','율','영','재','수','석')
    roots=('Ash','Blue','Cinder','Dawn','Ember','Frost','Gale','Haze','Iron','Jade','Lunar','Mist','Night','Opal','Pine','Quartz','Raven','Silver','Thorn','Violet')
    tails=('Arc','Bloom','Crest','Drift','Echo','Flare','Glade','Heart','Iris','Jet','Kite','Leaf','Moon','Nova','Orbit','Peak','Rune','Sky','Tide','Vale')
    names=[a+b+c for a in surnames for b in first for c in last if a+b+c not in used_names]
    excluded={v.casefold() for v in used_nicks}|RESERVED_NICKS
    nicks=[a+b+c for a in roots for b in tails for c in ('','Wind','Light','Stone','Wing','Rush') if (a+b+c).casefold() not in excluded]
    if len(names)<60 or len(nicks)<60:raise ValueError('고유 이름 후보 부족')
    chosen_names=rng.sample(names,60);chosen_nicks=rng.sample(nicks,60)
    players=[]
    for index in range(50):
        role=ROLES[index//10]
        stats={name:rng.randint(35,78) for name in ATTRIBUTES}
        nickname=chosen_nicks[index]
        from data import KITS
        eligible=[name for name,kit in KITS.items() if role in kit.roles]
        pool={name:rng.randint(35,90) for name in rng.sample(eligible,rng.randint(min(2,len(eligible)),len(eligible)))}
        players.append(dict(id=f'{role}-{index%10}',name=nickname,nickname=nickname,
                            real_name=chosen_names[index],champion_pool=pool,role=role,age=rng.randint(17,23),stats=stats,
                            salary=round((sum(stats.values())/6)**2*500),contract=52,
                            contract_start='2026-11-04',contract_end='2027-11-04',contract_estimated=True,
                            real_person=False,agent='지역 에이전트',form_year=2026,form=None,
                            personality=rng.choice(('신중함','공격적','협력적')),
                            bio='지역 공개 테스트 참가자 · 가상 선수'))
    coaches=[dict(id=f'coach-{i}',name=chosen_nicks[50+i],nickname=chosen_nicks[50+i],
                  real_name=chosen_names[50+i],real_person=False,
                  specialty=('전술','육성','분석')[i%3],ability=rng.randint(45,80),
                  salary=rng.randrange(100,251)*10000) for i in range(10)]
    return players,coaches

def import_club_logo(source,destination):
    """Normalize supported logos without changing the saved logo on failure."""
    from PIL import Image
    import io
    source=Path(source)
    if source.suffix.lower() not in ('.jpg','.jpeg','.png','.svg'):
        raise ValueError('JPG, JPEG, PNG, SVG 파일을 선택하세요.')
    if source.suffix.lower()=='.svg':
        raw=source.read_bytes()
        surface=pg.image.load(io.BytesIO(raw),'logo.svg')
        image=Image.frombytes('RGBA',surface.get_size(),pg.image.tobytes(surface,'RGBA'))
    else:
        from PIL import ImageOps
        with Image.open(source) as original:
            image=ImageOps.exif_transpose(original).convert('RGBA')
    image.thumbnail((512,512),Image.Resampling.LANCZOS)
    destination=Path(destination)
    destination.parent.mkdir(parents=True,exist_ok=True)
    temporary=destination.with_suffix('.tmp')
    try:
        image.save(temporary,format='PNG')
        temporary.replace(destination)
    finally:
        temporary.unlink(missing_ok=True)
    return str(destination)

class Career:
    def __init__(self,path):
        self.path=Path(path)
        self.state=None
        if self.path.exists():
            self.state=json.loads(self.path.read_text(encoding='utf-8'))
            players,coaches=candidates()
            for key,value in dict(candidates=players,coach_candidates=coaches,coaches=[],
                                  manager_stats=dict.fromkeys(MANAGER_STATS,10),logo='',setup_complete=False).items():
                self.state.setdefault(key,value)
            if len(self.state['coaches'])>3:raise ValueError('코치 최대 3명')

    def create(self,name,mode,manager='새 감독',stats=None,logo=''):
        used_names=set();used_nicks=set()
        files=list(self.path.parent.glob('*.json'))+list((self.path.parent/'ai-teams').glob('*.json'))
        if self.path.parent.name=='ai-teams':files+=list(self.path.parent.parent.glob('career.json'))
        for file in files:
            try:
                data=json.loads(file.read_text(encoding='utf-8'))
                for person in data.get('candidates',[])+data.get('coach_candidates',[]):
                    used_names.add(person.get('real_name',''));used_nicks.add(person.get('nickname',person.get('name','')))
            except (OSError,ValueError,AttributeError):continue
        players,coaches=candidates(used_names,used_nicks)
        self.state=dict(club=name,mode=mode,league='LCK CL' if mode=='창단' else 'LCK',
                        season=1,week=1,cash=30000000,training='기본기',tactic='균형',
                        inbox=['지역 선수 모집을 시작했습니다.','72주 시즌이 시작됐습니다.'],
                        roster=[],sponsors=[],vision='선수단 구성과 재정 안정',manager=manager,manager_stats=stats or dict.fromkeys(MANAGER_STATS,10),logo=logo,
                        candidates=players,coach_candidates=coaches,coaches=[],setup_complete=False)
        self.save()

    def sign(self,player_id):
        s=self.state
        player=next(p for p in s.get('candidates',[]) if p['id']==player_id)
        if any(p['role']==player['role'] for p in s['roster']):return False
        if len(s['roster'])>=5:return False
        s['roster'].append(dict(player))
        self.save()
        return True

    def hire_coach(self,coach_id):
        s=self.state
        if len(s.get('coaches',[]))>=3:return False
        if any(c['id']==coach_id for c in s.get('coaches',[])):return False
        coach=next(c for c in s['coach_candidates'] if c['id']==coach_id)
        s.setdefault('coaches',[]).append(dict(coach));self.save()
        return True

    def save(self):
        if len(self.state.get('coaches',[]))>3:raise ValueError('코치 최대 3명')
        self.path.parent.mkdir(parents=True,exist_ok=True)
        temporary=self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.state,ensure_ascii=False,indent=2),encoding='utf-8')
        temporary.replace(self.path)

    def advance(self):
        s=self.state
        if len(s['roster'])!=5:return False
        if s['week']==72:s['season']+=1;s['week']=1
        else:s['week']+=1
        payroll=round(sum(p['salary'] for p in s['roster']+s.get('coaches',[]))/72)
        s['cash']-=payroll
        s['inbox'].insert(0,f'이번 주 급여 {payroll:,}원 지급')
        s['inbox'].insert(0,f"{s['season']}시즌 {s['week']}주차 · {self.phase()}")
        self.save()

    def phase(self):
        return next(name for end,name in PHASES if self.state['week']<=end)

class Manager:
    def __init__(self,app):
        self.app=app
        self.career=Career(Path(__import__('app').HOME)/'career.json')
        self.page='대시보드'
        self.name=''
        self.mode='창단'
        self.input_active=False
        self.composition=''
        self.select_all=False
        self.notice=''
        self.club_picker=False
        self.club_page=0
        self.catalog_page=0
        self.manager_name='새 감독'
        self.manager_stats=dict.fromkeys(MANAGER_STATS,10)
        self.logo=''
        self.logo_surface=None
        self.logo_error=''
        self.input_field='club'
        self.role='TOP'
        self.selected=None
        self.admin_team=None
        self.database_page=0
        self.database_selected=None

    def begin_input(self,field):
        self.input_active=True;self.input_field=field
        self.select_all=True;self.composition=''
        pg.key.start_text_input()
        rect=self.app.display_rect()
        y=260 if field=='manager' else 205
        pg.key.set_text_input_rect(pg.Rect(round(rect.x+420*rect.w/1600),round(rect.y+y*rect.h/900),300,40))

    def input_label(self,field,value,placeholder):
        if not self.input_active or self.input_field!=field:return value or placeholder
        value=('['+value+']') if self.select_all else value
        return value+self.composition+(' |' if pg.time.get_ticks()%1000<600 else '')

    def text(self,value,x,y,size=16,color=(231,235,237),bold=False):
        self.app.text(value,x,y,size,color,bold)

    def panel(self,rect,title):
        pg.draw.rect(self.app.screen,(28,34,43),rect,border_radius=5)
        self.text(title,rect[0]+16,rect[1]+14,18,(185,151,235),True)

    def draw(self):
        a=self.app
        a.screen.fill((17,21,28));a.buttons={}
        pg.draw.rect(a.screen,(41,100,81),(0,0,1600,60))
        a.button('career_match','경기 일정',(1240,12,140,36))
        a.button('career_continue','계속',(1390,12,190,36),True)
        if self.notice:self.text(self.notice,250,875,14,(240,150,110))
        if not self.career.state and self.club_picker:
            from app import ASSETS
            people=json.loads((ASSETS/'people.json').read_text(encoding='utf-8'))['people']
            teams=sorted({(p['league'],p['team']) for p in people})
            self.panel((300,100,1000,720),'부임할 기존 구단 선택')
            for i,(league,team) in enumerate(teams[self.club_page*12:self.club_page*12+12]):
                a.button(f'career_choose_club_{self.club_page*12+i}',league+' / '+team,(340,160+i*46,900,38))
            a.button('career_club_prev','이전',(340,740,150,35))
            a.button('career_club_next','다음',(510,740,150,35))
            a.button('career_club_back','설정으로',(1050,740,190,35))
            return
        if not self.career.state:
            self.panel((380,105,850,700),'감독 커리어 시작')
            self.text('새 구단명 입력' if self.mode=='창단' else '선택한 구단 · 아래에서 감독 이름 입력',420,160,18)
            a.button('career_name',self.input_label('club',self.name,'여기를 눌러 구단명 입력'),(420,205,650,40),self.input_active and self.input_field=='club')
            a.button('career_create','새 구단 · LCK CL 출발',(420,315,310,40),self.mode=='창단')
            a.button('career_takeover','기존 구단 감독',(750,315,310,40),self.mode=='부임')
            a.button('career_start','커리어 시작',(420,710,640,45))
            a.button('career_manager_name',self.input_label('manager',self.manager_name,'감독 이름 입력'),(420,260,420,40),self.input_active and self.input_field=='manager')
            a.button('career_logo','구단 로고 선택',(860,260,200,40))
            self.text('감독 능력치 · 각 1~20 / 합계 60',420,390,16)
            for i,name in enumerate(MANAGER_STATS):
                y=430+i*40
                self.text(name,420,y,16)
                a.button(f'career_stat_minus_{i}','−',(650,y-5,45,32))
                self.text(self.manager_stats[name],730,y,16)
                a.button(f'career_stat_plus_{i}','+',(780,y-5,45,32))
            self.text('로고 선택됨' if self.logo else 'JPG · JPEG · PNG · SVG',860,390,14)
            if self.logo_error:self.text(self.logo_error,420,680,14,(240,110,120))
            self.text('후보는 가상 선수 50명 · 코치 10명',420,770,14)
            return
        s=self.career.state
        self.text(s['club'],24,18,22,bold=True)
        self.text(f"{s['season']}시즌 / {s['week']}주 / {self.career.phase()}",730,22)
        for i,label in enumerate(PAGES):
            a.button(f'page_{i}',label,(10,72+i*35,210,30),self.page==label)
        if not s.get('setup_complete',True) and self.page not in ('선수 후보','선수 상세','코치 후보','운영자','선수 데이터베이스','실존 인물 상세'):
            self.page='선수 후보'
        self.text(self.page,250,90,28,bold=True)
        logo=s.get('logo','')
        if logo and Path(logo).exists():
            if self.logo_surface is None:self.logo_surface=pg.image.load(logo).convert_alpha()
            a.screen.blit(pg.transform.smoothscale(self.logo_surface,(40,40)),(650,10))
        if self.page=='선수 데이터베이스':
            from app import ASSETS
            db=ASSETS/'people.json'
            people=json.loads(db.read_text(encoding='utf-8'))['people'] if db.exists() else []
            self.text(f'라이엇 GCD / {len(people)}명 / 150명 단위 · 이름을 눌러 상세 보기',270,145)
            start=self.database_page*150
            for i,person in enumerate(people[start:start+150]):
                x=255+(i//30)*265;y=185+(i%30)*21
                a.button('career_db_'+person['id'],person['name']+' · '+person['league'],(x,y,255,20))
            a.button('career_db_prev','이전',(270,832,120,30))
            a.button('career_db_next','다음',(400,832,120,30))
            return
        if self.page=='실존 인물 상세':
            from app import ASSETS,HOME
            people=json.loads((ASSETS/'people.json').read_text(encoding='utf-8'))['people']
            person=next(p for p in people if p['id']==self.database_selected)
            override_path=Path(HOME)/'people-overrides.json'
            overrides=json.loads(override_path.read_text(encoding='utf-8')) if override_path.exists() else {}
            person=dict(person,**overrides.get(person['id'],{}))
            for i,line in enumerate((person['name']+' / '+person['real_name'],person['team']+' / '+person['league'],
                                    '등록 역할 '+(person['role'] or person['raw_role'] or '미분류'),
                                    '계약 만료 '+person['contract_end']+(' / 게임용 1년 추정' if person['contract_estimated'] else ' / GCD 확인'),
                                    '원본 갱신 '+person['source_updated'],
                                    f"게임용 추정 연봉 {person.get('salary') or 1250000:,}원",
                                    '2026 폼 '+str(person.get('form') or '미확인'),
                                    '챔프폭 · 경기별 기록 미연결',
                                    '원본 역할이 없는 인물은 임의로 포지션을 배정하지 않습니다.')):
                self.text(line,270,185+i*55,16)
            a.button('career_db_back','명단으로',(270,815,200,35))
            ratings=person.get('stats') or dict.fromkeys(ATTRIBUTES,50)
            for i,name in enumerate(ATTRIBUTES):
                x=270+i*205
                self.text(f'{name} {ratings[name]}',x,720,14)
                a.button(f'career_rating_minus_{i}','−',(x,755,75,30))
                a.button(f'career_rating_plus_{i}','+',(x+85,755,75,30))
            portrait=person.get('portrait')
            if portrait and Path(portrait).exists():
                a.screen.blit(pg.transform.smoothscale(pg.image.load(portrait).convert_alpha(),(110,110)),(1320,185))
            a.button('career_person_photo','선수 사진 선택',(1170,570,280,35))
            self.text('로컬 운영자 수정 · 원본 출처는 보존',270,610)
            for i,label in enumerate(('계약 +1년','폼 +5','폼 -5','연봉 +10%','연봉 -10%')):
                a.button('career_edit_'+str(i),label,(270+i*245,650,225,35))
            return
        if self.page=='운영자':
            from app import HOME
            teams_folder=Path(HOME)/'ai-teams';teams_folder.mkdir(exist_ok=True)
            self.text('로컬 운영자 / AI 팀 커리어를 선택해 직접 운영',270,145)
            self.text('실제 선수 계약·2026 폼 데이터는 미연결',270,185)
            a.button('career_admin_add','AI 팀 추가',(270,235,260,40))
            for i,path in enumerate(sorted(teams_folder.glob('*.json'))[:9]):
                club=Career(path)
                a.button('career_admin_team_'+path.stem,f"{club.state['club']} / 선수 {len(club.state['roster'])} / 코치 {len(club.state.get('coaches',[]))}",(270,300+i*48,1000,40))
            if self.admin_team:a.button('career_admin_return','내 구단으로 복귀',(1120,235,320,40))
            return
        if self.page=='선수 후보':
            self.text('포지션별 10명 중 1명 선발 · 총 5명 / 후보 이름을 눌러 상세 보기',270,145)
            for i,role in enumerate(ROLES):
                a.button(f'career_role_{role}',role,(270+i*180,185,160,35),self.role==role)
            selected={p['id'] for p in s['roster']}
            for i,p in enumerate(p for p in s.get('candidates',[]) if p['role']==self.role):
                y=245+i*48
                label=f"{p.get('real_name','')} ({p['name']}) / {p['age']}세 / 희망 연봉 {p['salary']:,}원"
                if p['id'] in selected:label+=' / 선발됨'
                a.button('career_player_'+p['id'],label,(270,y,1050,39))
            self.text(f"선발 {len(s['roster'])}/5",270,770)
            a.button('career_coach_list','코치 후보 보기',(1050,770,270,40))
            return
        if self.page=='선수 상세':
            player=next(p for p in s.get('candidates',[])+s['roster'] if p['id']==self.selected)
            self.player_detail(player)
            return
        if self.page=='코치 후보':
            self.text(f"코치 {len(s.get('coaches',[]))}/3 · 최대 3명",270,145)
            hired={c['id'] for c in s.get('coaches',[])}
            for i,c in enumerate(s['coach_candidates']):
                y=210+i*49
                label=f"{c['name']} / {c['specialty']} {c['ability']} / 연봉 {c['salary']:,}원"
                a.button('career_coach_'+c['id'],label+(' / 영입됨' if c['id'] in hired else ''),(270,y,1020,40))
            a.button('career_candidate_list','선수 후보',(270,760,220,40))
            a.button('career_finish','선발 완료',(1100,760,220,40))
            return
        if self.page=='1군':
            for i,p in enumerate(s['roster']):
                a.button('career_player_'+p['id'],f"{p['role']} / {p['name']} / 연봉 {p['salary']:,}원",(270,190+i*65,1000,45))
            a.button('career_candidate_list','선수 후보',(270,600,220,40))
            return
        if self.page=='스탭':
            for i,c in enumerate(s.get('coaches',[])):
                self.text(f"{c['name']} / {c['specialty']} / {c['salary']:,}원",270,190+i*60)
            a.button('career_coach_list','코치 후보',(270,480,220,40))
            return
        if self.page=='대시보드':
            self.panel((250,145,420,610),'우편함')
            for i,message in enumerate(s['inbox'][:15]):self.text(message,270,200+i*33,14)
            self.panel((688,145,485,305),'구단 소식')
            self.text(s['league']+' / '+s['mode'],710,205,22,bold=True)
            self.text('시즌 목표',710,255,18)
            self.text(s['vision'],710,292)
            self.panel((688,468,485,287),'이번 주 계획')
            self.text('훈련 · '+s['training'],710,525,18)
            self.text('전술 · '+s['tactic'],710,565,18)
            self.text('선수단 · '+str(len(s['roster']))+'명',710,605)
            self.panel((1191,145,385,200),'재정')
            self.text(f"보유 현금 {s['cash']:,}원",1210,210,18)
            self.panel((1191,365,385,180),'구단 비전')
            self.text('LCK CL에서 선수단을 구성하세요',1210,425,14)
            self.panel((1191,565,385,190),'운영 상태')
            self.text('로컬 커리어 / 자동 저장',1210,625)
            self.text('온라인 과반수 투표 · 준비 중',1210,665,14)
        elif self.page in ('전술','훈련'):
            options=('균형','오브젝트 중심','사이드 압박','한타 중심') if self.page=='전술' else ('기본기','라인 관리','시야와 합류','한타 호흡','휴식')
            key='tactic' if self.page=='전술' else 'training'
            self.text('설정 저장 가능 · 경기 반영 연결은 준비 중',260,150,16)
            for i,label in enumerate(options):
                a.button(f'career_option_{i}',label,(270,210+i*65,420,45),s[key]==label)
        elif self.page=='달력':
            for i in range(72):
                x=260+(i%12)*108;y=180+(i//12)*90
                pg.draw.rect(a.screen,(44,60,63) if i+1==s['week'] else (28,34,43),(x,y,98,78))
                self.text(f'{i+1}주',x+12,y+10)
                phase=next(name for end,name in PHASES if i+1<=end)
                self.text(phase,x+8,y+42,14)
        elif self.page=='우편함':
            for i,message in enumerate(s['inbox'][:20]):self.text(message,270,170+i*32)
        elif self.page=='재정' or self.page=='영입 예산':
            self.text(f"현금 잔액 {s['cash']:,}원",270,180,22)
            self.text('실제 영입·급여·후원 거래는 아직 연결되지 않았습니다.',270,235)
        elif self.page=='내 프로필':
            self.text(s['manager']+' / '+s['club'],270,185,22)
            for i,(name,value) in enumerate(s.get('manager_stats',{}).items()):
                self.text(f'{name}  {value}/20',270,240+i*50)
        elif self.page=='챔피언 도감':
            from app import ASSETS
            catalog=ASSETS/'champion-catalog.json'
            entries=list(json.loads(catalog.read_text(encoding='utf-8'))['data'].values()) if catalog.exists() else []
            self.text(f'라이엇 16.22.1 / {len(entries)}명 · 고유 스킬 구현은 기존 17명',270,145)
            start=self.catalog_page*28
            for i,champion in enumerate(entries[start:start+28]):
                x=270+(i%4)*320;y=205+(i//4)*78
                self.panel((x,y,300,65),champion['name'])
                self.text(champion['title'],x+16,y+41,14)
            self.app.button('career_catalog_prev','이전',(270,800,130,35))
            self.app.button('career_catalog_next','다음',(420,800,130,35))
        elif self.page=='뉴스 사이트':
            self.text('실제 매체 링크 · 기사 자동 수집은 준비 중',270,160)
            for i,label in enumerate(('인벤','Sheep Esports','ESPN')):
                a.button(f'career_news_{i}',label,(270,220+i*65,420,45))
        else:
            self.panel((250,150,1325,520),self.page)
            self.text('데이터와 상세 동작을 연결할 예정입니다.',280,220,18)
            self.text('현재 커리어 데이터에 실제 선수·스탭·리그 결과는 없습니다.',280,270)
        self.text('RIFT MANAGER / 로컬 구단 운영 개발판',250,852,14,(141,155,168))

    def player_detail(self,p):
        a=self.app
        self.text(p.get('real_name','')+' ('+p['name']+') / '+p['role'],280,160,22,bold=True)
        self.text(p['bio'],280,205)
        center=(640,450);radius=170
        points=[]
        for i,name in enumerate(ATTRIBUTES):
            angle=-math.pi/2+i*math.tau/6
            end=(center[0]+math.cos(angle)*radius,center[1]+math.sin(angle)*radius)
            for ring in range(1,5):
                vertices=[(center[0]+math.cos(-math.pi/2+k*math.tau/6)*radius*ring/4,
                           center[1]+math.sin(-math.pi/2+k*math.tau/6)*radius*ring/4) for k in range(6)]
                pg.draw.polygon(a.screen,(60,75,90),vertices,1)
            pg.draw.line(a.screen,(60,75,90),center,end,1)
            value=p['stats'][name]
            points.append((center[0]+math.cos(angle)*radius*value/100,center[1]+math.sin(angle)*radius*value/100))
            self.text(f'{name} {value}',end[0]-35,end[1]-10,16)
        pg.draw.polygon(a.screen,(90,185,170),points,3)
        for i,line in enumerate((f"나이 {p['age']}세",f"희망 연봉 {p['salary']:,}원",
                                 f"계약 {p.get('contract_start') or '미확인'} ~ {p.get('contract_end') or '미확인'}",f"성격 {p['personality']}",p['agent'])):
            self.text(line,1050,270+i*65,18)
        from data import KITS
        pool=p.get('champion_pool',{})
        labels=[f"{KITS[name].ko if name in KITS else name} {value}" for name,value in sorted(pool.items(),key=lambda item:-item[1])]
        self.text('챔피언 숙련도 / 100',280,660,16)
        self.text(' · '.join(labels[:5]) or '기록 없음',280,695,14)
        signed=any(v['id']==p['id'] for v in self.career.state['roster'])
        a.button('career_sign_player','선발됨' if signed else '이 선수 선발',(1050,650,300,45),signed)
        a.button('career_candidate_list','후보 목록',(280,740,220,40))
        self.text('0~100 능력치 / 가상 선수 / 연봉은 시즌 단위',1050,740,14)

    def click(self,key):
        if key=='career_person_photo' or key.startswith('career_rating_'):
            from app import ASSETS,HOME
            person=next(p for p in json.loads((ASSETS/'people.json').read_text(encoding='utf-8'))['people'] if p['id']==self.database_selected)
            path=Path(HOME)/'people-overrides.json'
            data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            values=data.setdefault(person['id'],{})
            if key=='career_person_photo':
                from tkinter import Tk,filedialog
                from PIL import Image
                root=Tk();root.withdraw()
                try:filename=filedialog.askopenfilename(filetypes=[('이미지','*.png *.jpg *.jpeg *.webp')])
                finally:root.destroy()
                if filename:
                    folder=Path(HOME)/'people-images';folder.mkdir(exist_ok=True)
                    target=folder/(person['id']+'.png')
                    with Image.open(filename) as photo:
                        photo=photo.convert('RGBA');photo.thumbnail((512,512));photo.save(target)
                    values['portrait']=str(target)
            else:
                index=int(key.rsplit('_',1)[1]);name=ATTRIBUTES[index]
                stats=values.setdefault('stats',dict.fromkeys(ATTRIBUTES,50))
                stats[name]=max(1,min(100,stats[name]+(1 if '_plus_' in key else -1)))
            values['edited_by']='local-admin'
            tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
        elif key.startswith('career_edit_'):
            from app import ASSETS,HOME
            from datetime import date
            person=next(p for p in json.loads((ASSETS/'people.json').read_text(encoding='utf-8'))['people'] if p['id']==self.database_selected)
            path=Path(HOME)/'people-overrides.json'
            data=json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            values=data.setdefault(person['id'],{})
            action=int(key.rsplit('_',1)[1])
            if action==0:
                end=date.fromisoformat(values.get('contract_end',person['contract_end']))
                values['contract_end']=end.replace(year=end.year+1).isoformat();values['contract_estimated']=True
            elif action in (1,2):values['form']=max(1,min(100,(values.get('form') or 50)+(5 if action==1 else -5)))
            else:values['salary']=round((values.get('salary') or 1250000)*(1.1 if action==3 else .9))
            values['edited_by']='local-admin'
            tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(path)
        elif key=='career_db_prev':self.database_page=max(0,self.database_page-1)
        elif key=='career_db_next':
            from app import ASSETS
            count=len(json.loads((ASSETS/'people.json').read_text(encoding='utf-8'))['people'])
            self.database_page=min((count-1)//150,self.database_page+1)
        elif key=='career_db_back':self.page='선수 데이터베이스'
        elif key.startswith('career_db_'):
            self.database_selected=key[len('career_db_'):];self.page='실존 인물 상세'
        elif key=='career_admin_add':
            from app import HOME
            folder=Path(HOME)/'ai-teams';folder.mkdir(exist_ok=True)
            count=1
            while (folder/f'ai-{count}.json').exists():count+=1
            club=Career(folder/f'ai-{count}.json')
            club.create(f'AI 구단 {count}','창단','AI 감독')
        elif key.startswith('career_admin_team_'):
            from app import HOME
            stem=key[len('career_admin_team_'):]
            if '/' in stem or chr(92) in stem:return
            if self.admin_team is None:self.admin_team=self.career
            self.career=Career(Path(HOME)/'ai-teams'/(stem+'.json'));self.page='대시보드'
        elif key=='career_admin_return' and self.admin_team:
            self.career=self.admin_team;self.admin_team=None;self.page='대시보드'
        elif key.startswith('career_player_'):
            self.selected=key[len('career_player_'):];self.page='선수 상세'
        elif key.startswith('career_role_'):self.role=key[len('career_role_'):]
        elif key=='career_candidate_list':self.page='선수 후보'
        elif key=='career_coach_list':self.page='코치 후보'
        elif key=='career_sign_player':self.career.sign(self.selected)
        elif key.startswith('career_coach_coach-'):self.career.hire_coach(key[len('career_coach_'):])
        elif key=='career_finish':
            if len(self.career.state['roster'])==5:
                self.career.state['setup_complete']=True;self.career.save();self.page='대시보드'
        elif key=='career_manager_name':
            self.begin_input('manager')
        elif key=='career_logo':
            from tkinter import Tk,filedialog
            from app import HOME
            from PIL import Image
            root=Tk();root.withdraw()
            try:filename=filedialog.askopenfilename(title='구단 로고',filetypes=[('구단 로고','*.jpg *.jpeg *.png *.svg'),('SVG','*.svg'),('PNG','*.png'),('JPEG','*.jpg *.jpeg')])
            finally:root.destroy()
            if filename:
                import uuid
                path=Path(HOME)/'club-assets'/(uuid.uuid4().hex+'.png')
                try:
                    self.logo=import_club_logo(filename,path)
                    self.logo_surface=None;self.logo_error=''
                except (OSError,ValueError,pg.error):
                    self.logo_error='로고를 읽을 수 없습니다. 파일 형식을 확인하세요.'
        elif key.startswith('career_stat_'):
            _,_,direction,index=key.split('_')
            name=MANAGER_STATS[int(index)]
            value=self.manager_stats[name]+(1 if direction=='plus' else -1)
            if 1<=value<=20 and sum(self.manager_stats.values())-self.manager_stats[name]+value<=60:
                self.manager_stats[name]=value
        elif key=='career_catalog_prev':self.catalog_page=max(0,self.catalog_page-1)
        elif key=='career_catalog_next':
            from app import ASSETS
            catalog=ASSETS/'champion-catalog.json'
            count=len(json.loads(catalog.read_text(encoding='utf-8'))['data']) if catalog.exists() else 0
            self.catalog_page=min(max(0,(count-1)//28),self.catalog_page+1)
        elif key.startswith('page_'):self.page=PAGES[int(key[5:])]
        elif key=='career_name':
            if self.mode=='부임':self.club_picker=True
            else:self.begin_input('club')
        elif key=='career_create':self.mode='창단'
        elif key=='career_takeover':
            self.mode='부임';self.club_picker=True;self.input_active=False;pg.key.stop_text_input()
        elif key=='career_club_back':self.club_picker=False
        elif key=='career_club_prev':self.club_page=max(0,self.club_page-1)
        elif key=='career_club_next':
            from app import ASSETS
            people=json.loads((ASSETS/'people.json').read_text(encoding='utf-8'))['people']
            self.club_page=min((len({(p['league'],p['team']) for p in people})-1)//12,self.club_page+1)
        elif key.startswith('career_choose_club_'):
            from app import ASSETS
            people=json.loads((ASSETS/'people.json').read_text(encoding='utf-8'))['people']
            teams=sorted({(p['league'],p['team']) for p in people})
            self.selected_league,self.name=teams[int(key.rsplit('_',1)[1])]
            self.club_picker=False;self.notice='구단 선택 완료. 감독 이름을 입력하고 커리어 시작을 누르세요.'
        elif key=='career_start':
            if not self.name.strip():
                self.notice='구단명을 입력하거나 기존 구단을 선택하세요.';return
            if not self.manager_name.strip():
                self.notice='감독 이름을 입력하세요.';return
            self.career.create(self.name.strip(),self.mode,self.manager_name.strip() or '새 감독',dict(self.manager_stats),self.logo);self.input_active=False;pg.key.stop_text_input()
            if self.mode=='부임':
                self.career.state['league']=getattr(self,'selected_league','LCK');self.career.save()
            self.notice='커리어 생성 완료. 포지션별 후보 선발을 진행하세요.'
        elif key=='career_continue' and self.career.state:
            if len(self.career.state['roster'])<5:
                self.notice='포지션별 선수 5명을 선발하고 선발 완료를 누르세요.'
                self.page='선수 후보'
            else:
                self.career.advance();self.notice='주차 진행 완료. 현재 리그 경기 일정은 미연결입니다.'
        elif key.startswith('career_option_'):
            index=int(key.rsplit('_',1)[1])
            options=('균형','오브젝트 중심','사이드 압박','한타 중심') if self.page=='전술' else ('기본기','라인 관리','시야와 합류','한타 호흡','휴식')
            self.career.state['tactic' if self.page=='전술' else 'training']=options[index]
            self.career.save()
        elif key.startswith('career_news_'):
            import webbrowser
            webbrowser.open(('https://www.inven.co.kr/','https://www.sheepesports.com/','https://www.espn.com/esports/')[int(key.rsplit('_',1)[1])])
