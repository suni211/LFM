"""Verified operator/CEO records and explicit in-game leadership fallbacks.

Shareholders, operator organizations, and team head coaches are distinct
roles. Verified entries have source URLs; game fallbacks are visibly labeled.
"""
from copy import deepcopy

VERIFIED={
    ('LCP','DetonatioN FocusMe'):dict(
        name='DetonatioN Inc.',representative='Takuya Imaizumi',
        representative_role='대표이사 / 구단 운영 대표',nationality_code='JP',
        nationality_name_ko='일본',source='verified',
        source_url='https://team-detonation.net/aboutus'),
    ('LCS','Cloud9'):dict(
        name='Cloud9 Esports',representative='Jack Etienne',
        representative_role='공동 창립자 / CEO',nationality_code='US',
        nationality_name_ko='미국',source='verified',
        source_url='https://cloud9.gg/about/'),
    ('LCK','T1'):dict(
        name='T1 Entertainment & Sports',representative='Joe Marsh',
        representative_role='CEO',nationality_code='US',
        nationality_name_ko='미국',source='verified',
        source_url='https://www.t1.gg/about'),
    ('LCK','Gen.G'):dict(
        name='KSV eSports Korea Co., Ltd.',representative='Arnold Won Hur',
        representative_role='법인 대표',nationality_name_ko='',
        nationality_code='',source='verified',
        source_url='https://geng.fan/'),
}

# Staff identities below are verified against role-specific LoL sources.
VERIFIED_COACHING={
    ('LCK','T1'):{
        'Tom':('HEAD_COACH','https://liquipedia.net/leagueoflegends/T1'),
        'Mata':('COACH','https://liquipedia.net/leagueoflegends/T1'),
        'Easyhoon':('COACH','https://liquipedia.net/leagueoflegends/T1')},
    ('LCK','Gen.G'):{
        'Ryu':('HEAD_COACH','https://liquipedia.net/leagueoflegends/Gen.G_Esports'),
        'Lyn':('COACH','https://liquipedia.net/leagueoflegends/Gen.G_Esports'),
        'Nova':('COACH','https://liquipedia.net/leagueoflegends/Gen.G_Esports')},
    ('LCP','DetonatioN FocusMe'):{
        'Paz':('HEAD_COACH','https://team-detonation.net/team/leagueoflegends'),
        'TaNa':('COACH','https://team-detonation.net/team/leagueoflegends'),
        'Gismo':('ANALYST','https://team-detonation.net/team/leagueoflegends')},
}

# 2026 regular-season LCK staff roles, checked against the 2026 LCK
# press-media lineup and 2026 roster reference. Missing names are not invented.
LCK_2026_SOURCE='https://www.invenglobal.com/articles/20356/2026-lck-media-day-all-10-teams-vow-improved-performances-ahead-of-regular-season'
LCK_2026_STAFF={
    'Hanwha Life Esports':{'Homme':'HEAD_COACH','Sin':'COACH','Mowgli':'COACH','Sensation':'COACH'},
    'Dplus Kia':{'cvMax':'HEAD_COACH','PoohManDu':'COACH','Hachani':'COACH','Woong':'COACH','Sungmin':'COACH'},
    'kt Rolster':{'Score':'HEAD_COACH','Museong':'COACH','Sonstar':'COACH','Spark':'COACH','Lilac':'COACH'},
    'HANJIN BRION':{'Ssong':'HEAD_COACH','Duke':'COACH','Ssumday':'COACH'},
    'DN SOOPers':{'Ggoong':'COACH','Minit':'COACH','Millimas':'ANALYST','RapidStar':'COACH','Cube':'COACH'},
    'KRX':{'Joker':'HEAD_COACH','Naehyun':'COACH','Saroo':'ANALYST','Frozen':'COACH','Raise':'COACH','Catch':'COACH'},
    'NS REDFORCE':{'DanDy':'HEAD_COACH','Chelly':'COACH','Crazy':'COACH','bonO':'COACH'},
    'BNK FEARX':{'Edo':'HEAD_COACH','Rather':'COACH','Lira':'COACH','Key':'COACH'},
    'T1':{'kkOma':'COACH','Tom':'HEAD_COACH','Mata':'COACH','Easyhoon':'COACH','DooTi':'COACH','Nagne':'COACH'},
    'Gen.G':{'Ryu':'HEAD_COACH','Lyn':'COACH','Nova':'COACH','Jerry':'COACH'},
}
for _team,_roles in LCK_2026_STAFF.items():
    _dst=VERIFIED_COACHING.setdefault(('LCK',_team),{})
    for _nick,_role in _roles.items():
        _dst.setdefault(_nick,(_role,LCK_2026_SOURCE))

def annotate_verified_staff(league,team,people):
    """Only a game-display correction; original source data remains untouched."""
    corrections=VERIFIED_COACHING.get((league,team),{})
    names={'HEAD_COACH':'수석코치','COACH':'코치','ANALYST':'분석관'}
    result=[]
    for raw in people:
        person=dict(raw)
        item=corrections.get(str(person.get('nickname') or ''))
        if item:
            role,url=item
            person['kind']='coach' if role!='ANALYST' else 'staff'
            person['staff_role']=role
            person['staff_role_name']=names[role]
            person['raw_role']='Head Coach' if role=='HEAD_COACH' else 'Analyst' if role=='ANALYST' else 'Coach'
            person['staff_role_source']=url
        elif person.get('kind')=='unclassified':
            raw_role=str(person.get('raw_role') or '').casefold()
            if 'coach' in raw_role or '감독' in raw_role:
                person['kind']='coach'
            elif 'general manager' in raw_role or 'analyst' in raw_role or '단장' in raw_role:
                person['kind']='staff'
            elif raw_role.startswith('sub'):
                person['kind']='player'
                person['squad']='academy' if person.get('squad')=='academy' else 'reserve'
                part=raw_role.split('/',1)[-1] if '/' in raw_role else ''
                position={'jug':'JUNGLE','sup':'SUPPORT','bot':'ADC','top':'TOP','mid':'MID'}.get(part)
                if position: person['role']=position
        result.append(person)
    return result

def owner_info(league,team,created=False):
    record=VERIFIED.get((league,team))
    if record:
        # Corporate club owners and their representatives never show flags.
        result=deepcopy(record)
        result.pop('nationality_code',None)
        result.pop('nationality_name_ko',None)
        return result
    return dict(
        name='신생 구단 이사회 (게임)' if created else '구단주 정보 확인 중',
        representative='',representative_role='',
        source='simulation' if created else 'unverified',source_url='')

def head_coach(people):
    """Look up real head coach in the recorded team's LoL staff, not generic staff."""
    candidates=[]
    for p in people:
        if p.get('kind') not in ('coach','staff'):continue
        raw=str(p.get('raw_role') or '').casefold()
        score=0
        if 'head coach' in raw or '감독' in raw:score=5
        elif str(p.get('staff_role') or '')=='HEAD_COACH':score=4
        if score:
            candidates.append((-score,str(p.get('id','')),p))
    if not candidates:return None
    candidates.sort(key=lambda row:(row[0],row[1]))
    return candidates[0][2]

VERIFIED_EXTERNAL_MANAGERS={
    # The 2026 head coach was listed at LCK media day, but the imported team
    # data omitted his personnel record. This is a sourced external identity.
    ('LCK','DN SOOPers'):dict(
        name='oDin (Joo Young-dal)',source='verified',
        nationality_name_ko='대한민국',nationality_code='KR',
        person_id=None,role='감독',
        source_url='https://www.invenglobal.com/articles/20356/2026-lck-media-day-all-10-teams-vow-improved-performances-ahead-of-regular-season')
}

def ai_manager(people,league=None,team=None):
    real=head_coach(people)
    if real:
        import catalog
        return dict(name=catalog.display(real),source='registered-coach',
                    nationality_name_ko=real.get('nationality_name_ko',''),
                    nationality_code=real.get('nationality_code',''),
                    person_id=real.get('id'),role='감독',
                    source_url=real.get('staff_role_source',''))
    if league and team and (league,team) in VERIFIED_EXTERNAL_MANAGERS:
        return deepcopy(VERIFIED_EXTERNAL_MANAGERS[(league,team)])
    return dict(name='감독 정보 확인 중',source='unverified',role='감독',
                nationality_name_ko='',nationality_code='',person_id=None)
