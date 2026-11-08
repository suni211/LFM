"""League-scoped NPC fan boards, grounded in recorded game events.

Authors, reactions and readership are simulated; real users do not post here.
"""
import hashlib
import itertools
import json
import random
import time
from datetime import datetime,timezone,timedelta
import catalog
import fan_variety

CATEGORIES={'general':'잡담','manager':'감독평가','player':'선수평가','team':'팀평가',
    'tactics':'전술/밴픽','transfer':'이적','praise':'칭찬','rant':'불만·욕설',
    'cheers':'응원','meme':'밈·드립','analysis':'심층토론',
    'prediction':'예상·토론','notice':'공지'}
KST=timezone(timedelta(hours=9))

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS fan_authors(
        id INTEGER PRIMARY KEY,league TEXT NOT NULL,name TEXT NOT NULL UNIQUE,
        trait TEXT NOT NULL,level INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS fan_posts(
        id INTEGER PRIMARY KEY,league TEXT NOT NULL,author INTEGER NOT NULL REFERENCES fan_authors(id),
        event_key TEXT NOT NULL,category TEXT NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,
        season INTEGER NOT NULL,week INTEGER NOT NULL,created_at INTEGER NOT NULL,
        likes INTEGER NOT NULL,dislikes INTEGER NOT NULL,views INTEGER NOT NULL,
        subjects TEXT NOT NULL,sentiment INTEGER NOT NULL,UNIQUE(league,event_key));
        CREATE TABLE IF NOT EXISTS fan_comments(
        id INTEGER PRIMARY KEY,post_id INTEGER NOT NULL REFERENCES fan_posts(id),
        author INTEGER NOT NULL REFERENCES fan_authors(id),body TEXT NOT NULL,created_at INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS fan_board ON fan_posts(league,id DESC);''')

def leagues(db):
    values={p.get('league','') for p in catalog.load()['people']}
    values.update(row[0] for row in db.execute('SELECT DISTINCT league FROM club_profiles'))
    return sorted(v for v in values if v)

def seed(value):return int.from_bytes(hashlib.sha256(str(value).encode()).digest()[:8],'big')

def ensure_authors(db,league):
    rows=db.execute('SELECT id,name,trait,level FROM fan_authors WHERE league=? ORDER BY id',(league,)).fetchall()
    if rows:return rows
    roots=('라인','바텀','정글','미드','탑','드래곤','바론','차분한','매운맛','오늘의','깐깐한','침착한','푸른','노을빛','초록','은빛','작은','빛나는','새벽','한타')
    middles=('관찰','전략','분석','응원','시야','운영','설계','교전','기록','복기','연구','메모','해설','전술','합류','막타','동선','승부','리그','현장')
    tails=('노트','일지','수첩','연구실','관객','정류장')
    used={row[0] for row in db.execute('SELECT name FROM fan_authors')}
    names=[''.join(p) for p in itertools.product(roots,middles,tails) if ''.join(p) not in used]
    rng=random.Random(seed(league));rng.shuffle(names)
    if len(names)<12:raise ValueError('fan identity pool exhausted')
    traits=('analyst','optimist','critic','loyal','skeptic','patient')
    for i,name in enumerate(names[:12]):db.execute('INSERT INTO fan_authors(league,name,trait,level) VALUES(?,?,?,?)',(league,name,traits[i%6],1+i%5))
    return db.execute('SELECT id,name,trait,level FROM fan_authors WHERE league=? ORDER BY id',(league,)).fetchall()

def author(db,uid):
    name,trait,level=db.execute('SELECT name,trait,level FROM fan_authors WHERE id=?',(uid,)).fetchone()
    return dict(id=uid,name=name,level=level,trait=trait,npc=True)

def publish(db,league,key,category,title,body,season,week,subjects,sentiment=0,
            discussion=True,fan_reactions=True):
    existing=db.execute('SELECT id FROM fan_posts WHERE league=? AND event_key=?',(league,key)).fetchone()
    if existing:return existing[0]
    writers=ensure_authors(db,league);rng=random.Random(seed((league,key)))
    preferred='critic' if sentiment<0 else 'optimist' if sentiment>0 else 'analyst'
    writer=rng.choice([w for w in writers if w[2]==preferred] or writers)
    audience=rng.randint(18,95)*(3 if league in ('LCK','LPL','LEC','LCS') else 1)
    now=int(time.time())
    pid=db.execute('''INSERT INTO fan_posts(league,author,event_key,category,title,body,season,week,created_at,likes,dislikes,views,subjects,sentiment)
        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(league,writer[0],key,category,title,body,season,week,now,rng.randint(0,max(1,audience//6)),rng.randint(0,max(1,audience//18)),audience,json.dumps(subjects,ensure_ascii=False),sentiment)).lastrowid
    if discussion:
        responses={
            'analyst':'감정적인 결론보다는 밴픽과 실제 교전 기록부터 같이 봐야 한다고 생각함.',
            'optimist':'다음 경기에서 준비한 내용이 더 잘 나오길 기대합니다.',
            'critic':'프로 경기라면 결과에 대한 설명은 필요하지. 감독과 선수 모두 복기했으면.',
            'loyal':'응원은 계속하지만 잘한 점과 아쉬운 점은 나눠서 보자.',
            'skeptic':'한 경기만으로 다 판단하긴 이르고, 같은 문제가 반복되는지 보겠음.',
            'patient':'선수 호흡과 감독의 운영이 자리 잡을 시간도 필요하다고 봅니다.'}
        commenters=[w for w in writers if w[0]!=writer[0]];rng.shuffle(commenters)
        for i,commenter in enumerate(commenters[:rng.randint(3,5)]):
            varied=fan_variety.reply(seed((league,key,commenter[0],i)),commenter[2])
            # Preserve a seed comment as context; vary its actual phrasing per fan.
            text=varied+' '+(responses[commenter[2]] if i==0 else '')
            db.execute('INSERT INTO fan_comments(post_id,author,body,created_at) VALUES(?,?,?,?)',(pid,commenter[0],text.strip(),now+i+1))
    # Recorded results, signings and rumors anchor the discussion. Each event
    # gets distinct positive, critical and neutral fan perspectives, without
    # inventing a new match result, person, or transfer confirmation.
    if fan_reactions and discussion and category!='notice':
        tones=(1,1,0,-1) if sentiment>0 else (-1,-1,0,1) if sentiment<0 else (0,-1,1,0)
        base_style=seed((league,key,'fan-voices')) % fan_variety.STYLES_PER_SENTIMENT
        for i,tone in enumerate(tones):
            style=(base_style+i*349) % fan_variety.STYLES_PER_SENTIMENT
            name,post_body=fan_variety.voice(style,tone,title,body)
            kind=('praise','cheers')[i%2] if tone>0 else ('analysis','rant')[i%2] if tone<0 else ('general','meme')[i%2]
            publish(db,league,key+':fan:'+str(i),kind,name,post_body,season,week,
                    subjects,sentiment=tone,discussion=True,fan_reactions=False)
    trim(db,league)
    return pid

def trim(db,league,limit=2000):
    extra=[row[0] for row in db.execute("SELECT id FROM fan_posts WHERE league=? AND category!='notice' ORDER BY id DESC LIMIT -1 OFFSET ?",(league,limit))]
    for start in range(0,len(extra),400):
        chunk=extra[start:start+400]
        marks=','.join('?'*len(chunk))
        db.execute(f'DELETE FROM fan_comments WHERE post_id IN ({marks})',chunk)
        db.execute(f'DELETE FROM fan_posts WHERE id IN ({marks})',chunk)

def uproar(db,league,key,title,body,season,week,subjects):
    pid=publish(db,league,key,'transfer',title,body,season,week,subjects,sentiment=1)
    if db.execute('SELECT 1 FROM fan_comments WHERE post_id=? AND body LIKE ?',(pid,'%유출%')).fetchone(): return pid
    writers=ensure_authors(db,league);rng=random.Random(seed((league,key,'uproar')))
    names=[item.get('entity','') for item in subjects if item.get('kind')=='team']
    player=next((item.get('entity','') for item in subjects if item.get('kind')=='player'),'')
    club=names[0] if names else league
    lines=[
        club+' 이야기 나오자마자 댓글이 터졌다. 확정은 아닌데 이미 난리네.',
        '스토브에 이런 찌라시 안 나오면 이상하지. 조용히 끝나는 접촉이 없다.',
        '유출 속도 봐라. 대화하자마자 기사 뜨고 게시판이 먼저 끓는다.',
        player+' 이름만 나와도 댓글창이 갈라진다. 조건은 아직 모른다.',
        '관계자 입 한번 열리면 웬만하면 다 샌다. 이번에도 그대로네.',
        'AI 구단끼리 만나도, 사람 구단이 끼어도 바로 여기로 온다.',
        '아직 사인이 아니니까 단정은 말자. 근데 무시하기도 어렵다.',
        '훈련장 목격이든 식사든 사진이 도는 순간 커뮤니티는 이미 끝났다.',
        '재계약이든 이적이든 올해 스토브는 찌라시가 본편이다.',
        '댓글 새로고침이 기사보다 빠르다. 판이 이렇게 시끄러워도 되나.']
    rng.shuffle(lines);now=int(time.time())
    for i,line in enumerate(lines):
        db.execute('INSERT INTO fan_comments(post_id,author,body,created_at) VALUES(?,?,?,?)',(pid,writers[i%len(writers)][0],line,now+20+i))
    db.execute('UPDATE fan_posts SET likes=likes+?,views=views+? WHERE id=?',(rng.randint(80,220),rng.randint(900,3200),pid))
    publish(db,league,key+':reaction','general','댓글창 난리 · '+title[:48],
            '기사가 나오자마자 '+league+' 게시판이 시끄럽다. 확정 소식이 아니라 유출이라 말들이 갈리지만, 조용히 넘어가는 반응은 없다.',
            season,week,subjects,sentiment=1)
    return pid

def ensure_board(db,league):
    if league not in leagues(db):raise ValueError('unknown league board')
    publish(db,league,'welcome','notice',league+' 팬 커뮤니티',
            '이곳에서는 게임 속 AI 팬들이 해당 리그의 팀·감독·선수와 경기를 평가합니다. 게시글과 닉네임, 댓글, 조회·추천은 게임 내 팬 반응입니다.',1,1,[],discussion=False)

def public(db,row):
    pid,league,uid,category,title,body,season,week,stamp,up,down,views,raw=row
    created=datetime.fromtimestamp(stamp,KST)
    return dict(id=pid,league=league,author=author(db,uid),category=category,category_name=CATEGORIES[category],title=title,body=body,
                season=season,week=week,created_at=stamp,display_time=created.strftime('%H:%M' if created.date()==datetime.now(KST).date() else '%m.%d'),
                full_time=created.strftime('%Y.%m.%d %H:%M'),game_time=str(season)+'시즌 '+str(week)+'주',
                up=up,down=down,score=up-down,views=views,comments=db.execute('SELECT COUNT(*) FROM fan_comments WHERE post_id=?',(pid,)).fetchone()[0],
                subjects=json.loads(raw),pinned=category=='notice',source='simulated-fan-community',read_only=True,version=1,my_vote=0)

SELECT='SELECT id,league,author,category,title,body,season,week,created_at,likes,dislikes,views,subjects FROM fan_posts'

def board(db,league,category='all',page=0,query=''):
    if category not in (*CATEGORIES,'all','popular') or type(page) is not int or not 0<=page<=100000 or not isinstance(query,str) or len(query)>100:
        raise ValueError('invalid community filter')
    ensure_board(db,league)
    sql=SELECT+' WHERE league=?';params=[league]
    if category in CATEGORIES:sql+=' AND category=?';params.append(category)
    if category=='popular':sql+=' AND likes-dislikes>=10'
    if query.strip():sql+=' AND (instr(lower(title),lower(?))>0 OR instr(lower(body),lower(?))>0)';params.extend([query.strip()]*2)
    total=db.execute('SELECT COUNT(*) FROM ('+sql+')',params).fetchone()[0];page=min(page,max(0,(total-1)//30))
    posts=[public(db,row) for row in db.execute(sql+" ORDER BY (category='notice') DESC,id DESC LIMIT 30 OFFSET ?",[*params,page*30])]
    for post in posts:post.pop('body')
    return dict(posts=posts,total=total,page=page,page_size=30,categories=CATEGORIES,league=league,leagues=leagues(db),read_only=True,source='simulated-fan-community')

def get(db,uid,pid):
    if type(pid) is not int or not 1<=pid<=2**63-1:raise ValueError('invalid post')
    row=db.execute(SELECT+' WHERE id=?',(pid,)).fetchone()
    if not row:raise KeyError(pid)
    post=public(db,row)
    post['comments_list']=[dict(id=cid,author=author(db,writer),body=body,parent=None,full_time=datetime.fromtimestamp(created,KST).strftime('%Y.%m.%d %H:%M'))
        for cid,writer,body,created in db.execute('SELECT id,author,body,created_at FROM fan_comments WHERE post_id=? ORDER BY id',(pid,))]
    return post

def appointment(db,career,manager):
    club,season,week=db.execute('SELECT name,season,week FROM careers WHERE id=?',(career,)).fetchone()
    import clubs
    profile=clubs.profile(db,career);league=profile['league'];actual=profile['mode']=='takeover'
    title=(club+' 새 감독 '+manager+', 어떤 경기 보여줄지 궁금하다')
    body=(manager+' 감독이 '+club+' 운영을 맡았음. '+('등록 선수단을 어떻게 쓰고 어떤 밴픽을 보여줄지 보겠음. 이름값보다 준비와 결과로 평가해야 한다고 봄.' if actual else '새 팀이 '+league+'에서 출발한다는데 초기 선수 구성과 팀워크부터 지켜볼 생각. 처음부터 무리한 성적보다 방향이 있어야 할 듯.'))
    publish(db,league,'appointment:'+str(career),'manager',title,body,season,week,[dict(kind='team',entity=club),dict(kind='manager',entity=manager)],-1 if actual else 0)

def match(db,career,fixture,result):
    import clubs
    club,season,week,opponent=db.execute('SELECT c.name,f.season,f.week,f.opponent FROM fixtures f JOIN careers c ON c.id=f.career_id WHERE f.id=?',(fixture,)).fetchone()
    league=clubs.profile(db,career)['league'];won=result.get('winner')==0;score=':'.join(map(str,result.get('score',[])))
    manager=db.execute('SELECT name FROM manager_profiles WHERE career_id=?',(career,)).fetchone();manager=manager[0] if manager else club+' 감독'
    subjects=[dict(kind='team',entity=club),dict(kind='manager',entity=manager)]
    publish(db,league,'match:'+str(fixture),'team',club+' '+opponent+'전 '+score+' '+('승리, 오늘 준비 괜찮았음' if won else '패배… 운영 복기가 필요해 보임'),
            club+'이 '+opponent+'와의 시리즈에서 '+score+'로 '+('이겼다. 교전 이후 오브젝트와 마무리까지 연결한 부분을 좋게 봤음.' if won else '졌다. 감독의 준비와 선수들의 판단을 함께 돌아봐야 할 듯. 결과 하나로 모든 선수를 탓하기보다 실제 장면을 보겠음.'),season,week,subjects,1 if won else -1)
    publish(db,league,'manager-match:'+str(fixture),'manager',manager+' 감독, '+('이번 승리는 준비가 보였다' if won else '다음 경기에는 설명이 필요하다'),
            manager+' 감독의 '+club+'이 이번 시리즈에서 '+('승리했다. 다음 상대에게도 같은 준비가 통할지 기대된다.' if won else '패했다. 밴픽·교전 이후 운영·선수 기용 중 무엇을 바꿀지 보고 싶다. 팬들이 납득할 개선이 필요함.'),season,week,subjects,1 if won else -1)
    totals={}
    for game in result.get('sets',[]):
        for p in game.get('players',[]):
            if not p.get('player_id') or (p.get('team')!=game.get('blue',0)):continue
            line=totals.setdefault(p['player_id'],dict(name=p.get('player_name') or p['player_id'],k=0,d=0,a=0))
            k,d,a=p.get('kda',[0,0,0]);line['k']+=k;line['d']+=d;line['a']+=a
    if totals:
        pid=sorted(totals,key=lambda x:(totals[x]['k']+totals[x]['a'])/max(1,totals[x]['d']),reverse=won)[0];p=totals[pid]
        publish(db,league,'player-match:'+str(fixture),'player',p['name']+' 이번 시리즈 '+('집중력 좋았음' if won else '다음 경기는 다시 보여줬으면'),
                '이번 시리즈 기록은 '+str(p['k'])+'킬 '+str(p['d'])+'데스 '+str(p['a'])+'어시스트. '+('좋은 장면을 다음 경기에도 이어갔으면 함.' if won else '개인 장면과 팀 구도를 같이 봐야 하지만, 다음 경기에서 판단과 합류를 개선하는 모습이 필요하다고 봄.'),season,week,subjects+[dict(kind='player',entity=pid)],1 if won else -1)

def transfer(db,career,offer,person):
    import clubs
    club,season,week=db.execute('SELECT name,season,week FROM careers WHERE id=?',(career,)).fetchone()
    name=catalog.display(person)
    publish(db,clubs.profile(db,career)['league'],'transfer:'+str(offer),'transfer',club+' '+name+' 영입, 선수단 구성이 달라지네',
            club+'이 '+name+' 영입을 확정했다. 기존 선수와의 역할 분담, 팀워크, 출전 기회를 어떻게 정리할지 지켜볼 생각. 이름만으로 성공을 단정하긴 이르고 실제 경기와 구단 운영을 보겠음.',season,week,[dict(kind='team',entity=club),dict(kind='player',entity=person['id'])])
