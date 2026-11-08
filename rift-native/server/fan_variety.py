"""Deterministic, event-grounded NPC fan voice library.

The headline and factual event summary always come from recorded game actions.
A 12 x 12 x 10 phrase lattice supports 1,440 distinct discussion styles for
each of three sentiments: 4,320 fan post variations, not fabricated results.
"""
POSITIVE = (
    '이건 칭찬할 수밖에 없지', '와 이 소식 마음에 든다', '오늘은 진짜 인정',
    '팬으로서 행복하다', '이건 박수 쳐야 함', '이 맛에 응원하지',
    '진심으로 잘했다고 생각함', '분위기가 확 달라진다', '좋은 방향 같은데',
    '우리도 이런 소식 기다렸음', '긍정적인 변화 인정', '오늘 커뮤니티 훈훈하네',
)
NEGATIVE = (
    '아니 ㅅㅂ 이게 뭐냐', '진짜 속 터져서 글 쓴다', '이건 좀 아니지 않냐',
    '계속 이렇게 하면 욕 나옴', '하... 이러니까 화나지', '팬들 화나는 건 이해해라',
    '뭔가 답답한데', '누가 좀 설명해 줬으면', '이건 비판받을 만하다',
    '아쉽다는 말로도 부족함', '이 상황 실화냐', '제발 좀 달라졌으면',
)
NEUTRAL = (
    '이 소식 보고 한마디', '다들 반응 어떻게 봄?', '나만 궁금한 건가',
    '일단 정보부터 정리해보자', '팬 입장에서 생각해봄', '여기 의견 갈리네',
    '아직 판단은 보류', '한 가지 짚고 가자', '다음 전개가 궁금하다',
    '오늘 게시판 조용할 줄 알았는데', '자료 보고 옴', '일단 지켜보자는 쪽',
)
PERSPECTIVES = (
    '당장 반응보다 다음 선택이 중요할 듯.',
    '한쪽 의견만 듣기보다 여러 팬 생각을 모아보자.',
    '지금까지 나온 기록과 앞으로의 흐름을 구분해야 함.',
    '기대치가 높은 만큼 평가도 엄격해지는 것 같다.',
    '해당 팀을 오래 지켜본 팬은 다르게 느낄 수도 있음.',
    '소문과 확정된 사실은 구분해야 한다.',
    '오늘만 보고 결론 내리기에는 정보가 부족할 수 있다.',
    '이런 이야기가 계속 나오는 이유는 따져볼 필요가 있다.',
    '선수 개인과 팀 전체의 문제는 나눠서 봐야 한다.',
    '감독 판단과 프런트 결정은 서로 다른 문제일 수 있다.',
    '팬들이 어떤 부분에 반응하는지 보는 것도 흥미롭다.',
    '지금보다 이후 대응이 평가를 바꿀 수 있다.',
)
CLOSINGS = (
    '다른 팬들 생각은 어떰?',
    '댓글에서 반대 의견도 들어보고 싶다.',
    '다음 결과 나올 때 다시 얘기하자.',
    '이건 한동안 계속 화제겠네.',
    '확정되지 않은 얘기는 단정하지 말자.',
    '일단 응원은 하되 지켜보겠음.',
    '지금부터가 진짜 중요할 듯.',
    '결국 결과와 과정이 답하겠지.',
    '서로 의견 다를 수 있다는 건 인정.',
    '기록과 후속 소식 나오면 다시 판단할게.',
)
STYLES_PER_SENTIMENT = len(POSITIVE)*len(PERSPECTIVES)*len(CLOSINGS)
TOTAL_STYLES = STYLES_PER_SENTIMENT * 3

def voice(index, sentiment, headline, event_summary):
    """Create one uniquely indexed human-style reaction to a real game event."""
    if type(index) is not int or not 0 <= index < STYLES_PER_SENTIMENT:
        raise ValueError('invalid fan style index')
    if sentiment > 0:
        openings = POSITIVE
    elif sentiment < 0:
        openings = NEGATIVE
    else:
        openings = NEUTRAL
    opening = openings[index % len(openings)]
    perspective = PERSPECTIVES[(index // len(openings)) % len(PERSPECTIVES)]
    closing = CLOSINGS[index // (len(openings)*len(PERSPECTIVES))]
    return (
        opening+' · '+headline,
        opening+'. '+event_summary+' '+perspective+' '+closing,
    )

REPLIES = {
    'analyst': (
        '느낌보다 기록을 먼저 보자.',
        '경기 기록과 실제로 확정된 내용이 중요해.',
        '오늘 언급된 내용과 추측은 구분해야지.',
    ),
    'optimist': (
        '난 다음 경기에서 더 좋은 모습 나올 거라 기대함.',
        '좋은 흐름이 이어졌으면 좋겠다.',
        '앞으로도 이런 이야기가 더 들리면 좋겠네.',
    ),
    'critic': (
        '아니 솔직히 이 부분은 비판할 수 있지.',
        '답답한 건 답답하다고 말해야 한다.',
        '좋게만 볼 수 없는 문제라고 생각함.',
    ),
    'loyal': (
        '응원하는 팀이라도 잘못한 건 말할 수 있음.',
        '그래도 다음 경기는 챙겨본다.',
        '좋을 때나 안 좋을 때나 지켜봐야지.',
    ),
    'skeptic': (
        '일단 확정된 소식부터 보자.',
        '이걸로 모든 걸 판단하긴 이르다.',
        '과장된 해석은 거르는 게 맞다.',
    ),
    'patient': (
        '차분하게 지켜보면 판단할 근거가 더 나오겠지.',
        '시간 두고 평가해보자.',
        '서두른 결론은 피하는 게 좋겠어.',
    ),
}

def reply(seed_number, trait):
    options = REPLIES.get(trait, REPLIES['analyst'])
    return options[seed_number % len(options)]
