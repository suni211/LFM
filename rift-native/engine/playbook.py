"""Team orders read by the match engine. Stored plans must stay inside these lists."""
PHASES = ('early', 'mid', 'late')
ORDERS = {
    'early': ('라인 우선', '정글 합류', '오브젝트 준비', '갱 중심', '안정 파밍'),
    'mid': ('오브젝트 중심', '한타 중심', '사이드 압박', '미드 집결', '픽오프'),
    'late': ('넥서스 공략', '바론 중심', '사이드 압박', '수비 후 역습', '한타 중심'),
}
SUBS = {
    'early': ('시야 먼저', '다이브 금지', '타워 다이브 허용', '스왑 준비', '로밍 허용'),
    'mid': ('바론 준비', '드래곤 준비', '스플릿', '한타 대기', '역이니시'),
    'late': ('슈퍼 미니언', '백도어 금지', '백도어 허용', '엘더 우선', '기지 수비'),
}
LANING = {
    'TOP': ('압박', '프리징', '슬로우 푸시', '프록시'),
    'JUNGLE': ('풀클리어', '3캠프 갱', '인베이드', '오브젝트 동선'),
    'MID': ('푸시 로밍', '라인 유지', '사이드 로밍', '정글 호응'),
    'ADC': ('푸시', '프리징', '슬로우 푸시', '타워 압박'),
    'SUPPORT': ('로밍', '라인 유지', '시야', '올인'),
}
MACRO = {'오브젝트 중심', '한타 중심', '사이드 압박', '균형'}

def default_plan():
    return {
        'callers': {'primary': '', 'secondary': ''},
        'early': {'order': '라인 우선', 'sub': '시야 먼저'},
        'mid': {'order': '오브젝트 중심', 'sub': '드래곤 준비'},
        'late': {'order': '한타 중심', 'sub': '기지 수비'},
        'laning': {'TOP': '압박', 'JUNGLE': '풀클리어', 'MID': '라인 유지', 'ADC': '푸시', 'SUPPORT': '로밍'},
    }

def plan_from_style(style):
    plan = default_plan()
    if style in ORDERS['mid']:
        plan['mid']['order'] = style
    elif style == '균형':
        plan['mid']['order'] = '미드 집결'
    return plan

def check(plan):
    if not isinstance(plan, dict):
        raise ValueError('invalid tactics')
    callers=plan.setdefault('callers',{'primary':'','secondary':''})
    if not isinstance(callers,dict) or set(callers)!={'primary','secondary'} or any(not isinstance(v,str) or len(v)>100 for v in callers.values()):
        raise ValueError('invalid shotcallers')
    if callers['primary'] and callers['primary']==callers['secondary']: raise ValueError('invalid shotcallers')
    for phase in PHASES:
        row = plan.get(phase)
        if not isinstance(row, dict) or row.get('order') not in ORDERS[phase] or row.get('sub') not in SUBS[phase]:
            raise ValueError('invalid tactics')
    laning = plan.get('laning')
    if not isinstance(laning, dict) or set(laning) != set(LANING) or any(laning[role] not in LANING[role] for role in LANING):
        raise ValueError('invalid tactics')
    return plan

def phase_at(t):
    if t < 840:
        return 'early'
    if t < 1500:
        return 'mid'
    return 'late'

def directive(plan, t):
    row = plan[phase_at(t)]
    return row['order'], row['sub']

def lane_order(plan, role):
    return plan.get('laning', {}).get(role, '')

def style_of(order, sub):
    if order in ('오브젝트 중심', '한타 중심', '사이드 압박'):
        return order
    if order in ('오브젝트 준비', '바론 중심') or sub in ('드래곤 준비', '바론 준비', '엘더 우선'):
        return '오브젝트 중심'
    if order in ('갱 중심', '픽오프', '미드 집결', '정글 합류') or sub == '한타 대기':
        return '한타 중심'
    if order in ('넥서스 공략',) or sub in ('스플릿', '백도어 허용'):
        return '사이드 압박'
    return '균형'
