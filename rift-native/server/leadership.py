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
        result.append(person)
    return result

def owner_info(league,team,created=False):
    record=VERIFIED.get((league,team))
    if record:return deepcopy(record)
    return dict(
        name='신생 구단 투자 이사회 (게임)' if created else '구단 운영위원회 (게임)',
        representative='',representative_role='게임 내 가상 운영 주체',
        nationality_name_ko='',nationality_code='',
        source='simulation',source_url='')

def head_coach(people):
    """Look up real head coach in the recorded team's LoL staff, not generic staff."""
    candidates=[]
    for p in people:
        if p.get('kind') not in ('coach','staff'):continue
        raw=str(p.get('raw_role') or '').casefold()
        score=0
        if 'head coach' in raw or '감독' in raw:score=5
        elif str(p.get('staff_role') or '')=='HEAD_COACH':score=4
        elif raw=='coach' or 'coach' in raw:score=1
        if score:
            candidates.append((-score,str(p.get('id','')),p))
    if not candidates:return None
    candidates.sort(key=lambda row:(row[0],row[1]))
    return candidates[0][2]

def ai_manager(people):
    real=head_coach(people)
    if real:
        import catalog
        return dict(name=catalog.display(real),source='registered-coach',
                    nationality_name_ko=real.get('nationality_name_ko',''),
                    nationality_code=real.get('nationality_code',''),
                    person_id=real.get('id'),role='감독',
                    source_url=real.get('staff_role_source',''))
    return dict(name='임시 감독 (게임 AI)',source='simulation',role='감독',
                nationality_name_ko='',nationality_code='',person_id=None)
