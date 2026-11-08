"""Player dossier statistics for LFM: 28 simulated tactical attributes + match facts.

Imported real-world rosters contain no verified per-attribute ratings. Numbers
here are explicitly deterministic in-game estimates, never real-life claims.
Official match performance is only taken from finished LFM fixture records.
"""
import hashlib
import json

import analytics

CATEGORIES=(
    ('mechanics','기술 · 라인전',(
        ('피지컬','교전'),('반응 속도','교전'),('CS 수급','라인전'),
        ('라인전 견제','라인전'),('스킬 적중','교전'),('콤보 수행','교전'),
        ('일대일 교전','교전'),('한타 포지셔닝','운영'))),
    ('macro','운영 · 시야',(
        ('맵 리딩','운영'),('오브젝트 판단','운영'),('시야 장악','시야'),
        ('로밍 타이밍','운영'),('라인 관리','라인전'),('한타 판단','운영'),
        ('오더 이해','협동'),('후반 운영','운영'))),
    ('mental','멘탈 · 팀워크',(
        ('집중력','멘탈'),('경기 멘탈','멘탈'),('침착성','멘탈'),
        ('승부욕','멘탈'),('팀워크','협동'),('압박 대응','멘탈'),
        ('꾸준함','멘탈'))),
    ('potential','성장 · 재능',(
        ('훈련 태도','협동'),('적응력','운영'),('학습 속도','라인전'),
        ('프로 의식','멘탈'),('발전 가능성','교전'))),
)
ALL_ATTRIBUTES=tuple(label for _,_,attributes in CATEGORIES for label,_ in attributes)
ROLES=('TOP','JUNGLE','MID','ADC','SUPPORT')
ROLE_NAMES={'TOP':'탑','JUNGLE':'정글','MID':'미드','ADC':'원거리 딜러','SUPPORT':'서포터'}
ROLE_BONUSES={
    'TOP':{'일대일 교전':2,'라인전 견제':1,'한타 포지셔닝':1},
    'JUNGLE':{'오브젝트 판단':2,'로밍 타이밍':2,'맵 리딩':1},
    'MID':{'스킬 적중':2,'라인 관리':1,'로밍 타이밍':1},
    'ADC':{'CS 수급':2,'한타 포지셔닝':2,'반응 속도':1},
    'SUPPORT':{'시야 장악':2,'팀워크':2,'오더 이해':1},
}

def _unit(value):
    return int.from_bytes(hashlib.sha256(str(value).encode()).digest()[:8],'big') / (2**64-1)

def _core(person):
    ev=person.get('game_evaluation') or {}
    stated=ev.get('ratings') or person.get('stats')
    if not isinstance(stated,dict):stated={}
    sources=('라인전','교전','운영','시야','협동','멘탈')
    imported=any(isinstance(stated.get(k), (float,int)) and not isinstance(stated.get(k),bool)
                 for k in sources)
    values={}
    for key in sources:
        value=stated.get(key)
        if type(value) in (float,int):
            values[key]=max(1,min(100,float(value)))
        else:
            # Model features are stable for an identity and NEVER presented
            # as verified real-world performance or private scout knowledge.
            values[key]=43+round(_unit('LFM:in-game-core:'+str(person['id'])+':'+key)*34)
    return values,'game-rating' if imported else 'simulation-estimate'

def attribute_profile(person):
    if person.get('kind')!='player':
        return dict(sections=[],count=0,role=None,source='not-player',summary='')
    core,source=_core(person)
    role=person.get('role')
    groups=[]
    flat=[]
    for key,title,attributes in CATEGORIES:
        entries=[]
        for label,basis in attributes:
            spread=round((_unit('LFM:attribute:v3:'+str(person['id'])+':'+label)-.5)*5)
            score=max(1,min(20,round(core[basis]/5)+spread+
                ROLE_BONUSES.get(role,{}).get(label,0)))
            entries.append(dict(name=label,value=score))
            flat.append((score,label))
        groups.append(dict(key=key,title=title,attributes=entries))
    best=sorted(flat,key=lambda item:(-item[0],item[1]))
    weak=sorted(flat,key=lambda item:(item[0],item[1]))
    profile=dict(
        sections=groups,count=len(flat),scale=20,
        source=source,source_label='게임 내 개별 능력치 모델',
        note=('실제 선수의 검증된 능력치가 아닙니다. 게임의 고정된 가상 평가 모델로 '
              '산출한 값이며, 실제 경기 기록과 구분됩니다.'
              if source=='simulation-estimate' else
              '게임에 등록된 기본 능력치를 바탕으로 세부 능력치를 확장했습니다. '
              '실제 선수의 검증된 능력치가 아닙니다.'),
        overall=round(sum(s for s,_ in flat)/len(flat),1),
        strengths=[name for _,name in best[:3]],
        weaknesses=[name for _,name in weak[:3]],
        role=dict(primary=role or '',primary_label=ROLE_NAMES.get(role,'미등록'),
                  secondary=[],note='등록된 주 포지션만 표시합니다. 다른 포지션 숙련도는 검증되지 않았습니다.'),
        core=core,
    )
    return profile

def season_performance(db,career,person):
    if not career or person.get('kind')!='player':
        return dict(available=False,reason='진행한 구단 경기 기록이 없습니다.',recent=[])
    row=db.execute('SELECT season FROM careers WHERE id=?',(career,)).fetchone()
    if not row:
        return dict(available=False,reason='등록된 커리어가 없습니다.',recent=[])
    season=row[0]
    hub=analytics.hub(db,career,season)
    player=next((p for p in hub.get('players',[]) if p.get('id')==person['id']),None)
    if not player:
        return dict(available=False,season=season,reason='이번 시즌에 기록된 출전 세트가 없습니다.',recent=[])
    recent=[]
    games=db.execute("""SELECT week,opponent,result FROM fixtures
        WHERE career_id=? AND season=? AND state='finished'
        ORDER BY week DESC,id DESC LIMIT 20""",(career,season)).fetchall()
    for week,opponent,payload in games:
        result=json.loads(payload)
        sets=result.get('sets',[result])
        for game in reversed(sets):
            participants=game.get('players',[])
            for pos,member in enumerate(participants):
                if member.get('player_id')!=person['id']:continue
                kills,deaths,assists=member.get('kda',[0,0,0])
                team=member.get('team',pos//5)
                won=team==game.get('winner')
                recent.append(dict(week=week,opponent=opponent,champion=member.get('name'),
                    won=bool(won),kills=kills,deaths=deaths,assists=assists,
                    cs=member.get('cs'),damage=member.get('damage')))
                break
            if len(recent)>=5:break
        if len(recent)>=5:break
    played=player['games']
    summary={key:player.get(key) for key in
             ('games','wins','kills','deaths','assists','cs','gold','damage','kda','rating','win_rate')}
    summary.update(available=True,season=season,losses=played-player['wins'],
                   avg_cs=round(player['cs']/played,1),
                   avg_damage=round(player['damage']/played),
                   avg_gold=round(player['gold']/played),
                   recent=recent,source='played-game-results',
                   note='LFM에서 실제 완료된 경기 시뮬레이션의 세트 기록입니다. 외부 프로 경기 통계가 아닙니다.')
    return summary

def report(db,career,person):
    return dict(attributes=attribute_profile(person),
                season=season_performance(db,career,person))
