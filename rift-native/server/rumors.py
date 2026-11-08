"""Stove-league leaks. A user touch or an AI conversation becomes news, and the board reacts."""
import hashlib
import json
import catalog
import clubs
import fan_community

YEAR=104

def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS league_rumors(
        id INTEGER PRIMARY KEY, league TEXT NOT NULL, event_key TEXT NOT NULL UNIQUE,
        season INTEGER NOT NULL, week INTEGER NOT NULL, headline TEXT NOT NULL, body TEXT NOT NULL,
        subjects TEXT NOT NULL)''')
    db.execute('CREATE TABLE IF NOT EXISTS stove_weeks(season INTEGER NOT NULL, week INTEGER NOT NULL, PRIMARY KEY(season,week))')

def _turn(season,week): return (season-1)*YEAR+week

def _unit(key): return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4],'big')

def prune(db):
    import online_world
    clock=online_world.clock(db)
    cutoff=_turn(clock['season'],clock['week'])-YEAR
    if cutoff<1: return
    db.execute('DELETE FROM career_news WHERE ((season-1)*104+week)<?',(cutoff,))
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='league_rumors'").fetchone():
        db.execute('DELETE FROM league_rumors WHERE ((season-1)*104+week)<?',(cutoff,))

def break_story(db,league,key,season,week,headline,body,subjects):
    if db.execute('SELECT 1 FROM league_rumors WHERE event_key=?',(key,)).fetchone(): return
    db.execute('''INSERT INTO league_rumors(league,event_key,season,week,headline,body,subjects)
        VALUES(?,?,?,?,?,?,?)''',(league,key,season,week,headline,body,json.dumps(subjects,ensure_ascii=False)))
    fan_community.uproar(db,league,key,headline,body,season,week,subjects)

def involve(db,career,key,headline,body,subjects):
    import club_messages,online_world
    clock=online_world.clock(db)
    league=clubs.profile(db,career)['league']
    club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    people=[dict(kind='team',entity=club),*subjects]
    break_story(db,league,'leak:'+key,clock['season'],clock['week'],headline,body,people)
    club_messages.publish(db,career,'leak:'+key,clock['season'],clock['week'],'유출',headline)

def contact(db,career,person):
    club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    name=catalog.display(person)
    involve(db,career,'contact:'+str(career)+':'+person['id'],
            club+'·'+name+' 접촉설 유출',
            club+'이 '+name+' 측과 말을 꺼내자 내용이 바로 밖으로 나왔다. 조건은 확정이 아니고, 관계자의 대화가 스토브 찌라시로 퍼진 상태다.',
            [dict(kind='player',entity=person['id'])])

def step(db,career,offer_id,choice,person):
    club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    name=catalog.display(person)
    text={'cancel':'접촉을 끊은 정황까지 유출됐다.','decline':'제안을 거절한 사실도 바로 기사에 실렸다.',
          'counter':'이적료를 되물은 대화가 커뮤니티에 먼저 퍼졌다.','approve':'구단이 이적을 허용했다는 소식이 당일 나왔다.',
          'accept':'조건을 받아들이는 자리가 유출됐다.','forward':'상대 구단으로 제안이 넘어간 사실이 유출됐다.'}.get(choice,'협상 진행이 유출됐다.')
    involve(db,career,'offer:'+str(offer_id)+':'+choice,
            club+'·'+name+' 협상 유출',
            club+'과 '+name+'의 이야기에서 '+text+' 사인 완료와는 별개의 찌라시다.',
            [dict(kind='player',entity=person['id'])])

def scout(db,career,person_id,nickname,accepted):
    club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    result='유망주로 붙잡자는 대화가 수락됐다.' if accepted else '제안은 거절됐지만 만난 사실 자체가 새 나갔다.'
    involve(db,career,'scout:'+str(career)+':'+person_id,
            club+'·'+nickname+' 솔로랭크 접촉 유출',
            club+'이 솔로랭크를 도는 '+nickname+'과 이야기했다. '+result,
            [dict(kind='player',entity=person_id)])

def debut(db,career,person_id,nickname):
    club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    involve(db,career,'debut:'+person_id,
            nickname+' 프로 데뷔설, '+club+'에서 키운 정황 유출',
            club+'이 '+nickname+'을 직접 키워 프로로 올리려는 정황이 발표 전에 퍼졌다.',
            [dict(kind='player',entity=person_id)])

def interest(db,career,person):
    club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    name=catalog.display(person)
    involve(db,career,'interest:'+str(career)+':'+person['id'],
            club+'이 '+name+'을 눈여겨본다는 메모 유출',
            club+' 내부 관심 명단에 '+name+'이 올랐고, 그 메모가 바로 찌라시로 나왔다.',
            [dict(kind='player',entity=person['id'])])

def _teams(db):
    # AI-to-AI rumors must be generated from CURRENT unclaimed rosters rather
    # than the original import sheet, especially after completed AI deals.
    import world_transfers
    return world_transfers.rosters(db)

def weekly(db,season,week):
    if not 1<=week<=10: prune(db); return
    if db.execute('SELECT 1 FROM stove_weeks WHERE season=? AND week=?',(season,week)).fetchone():
        prune(db); return
    for league,teams in _teams(db).items():
        names=sorted(teams)
        if len(names)<2: continue
        leaks=0
        for index in range(10):
            if _unit(f'{season}:{week}:{league}:{index}')%10>=8: continue
            left=names[_unit(f'{league}:{season}:{week}:a:{index}')%len(names)]
            right=names[_unit(f'{league}:{season}:{week}:b:{index}')%len(names)]
            if left==right: right=names[(names.index(left)+1)%len(names)]
            pool=teams[left] or teams[right]
            if not pool: continue
            person=pool[_unit(f'{league}:{season}:{week}:p:{index}')%len(pool)]
            name=catalog.display(person)
            break_story(db,league,f'ai:{season}:{week}:{league}:{index}',season,week,
                        f'{right}, {name} 접촉설 유출',
                        f'{left} 소속 {name}을 두고 {right}와 나눈 이야기가 스토브리그에 바로 퍼졌다. 두 구단의 대화는 확정 이적이 아니고, 웬만한 접촉은 이렇게 유출된다.',
                        [dict(kind='team',entity=left),dict(kind='team',entity=right),dict(kind='player',entity=person['id'])])
            leaks+=1
            if leaks>=8: break
        host=names[_unit(f'{league}:{season}:{week}:host')%len(names)]
        pool=teams[host]
        if pool:
            person=pool[_unit(f'{league}:{season}:{week}:sight')%len(pool)]
            name=catalog.display(person)
            break_story(db,league,f'sight:{season}:{week}:{league}',season,week,
                        f'{host} 훈련장 인근에서 {name} 측 목격',
                        f'{host} 관계자와 {name} 측이 만난 장면이 스토브 기간에 돌았다. 재계약인지 다른 구단 관심인지는 갈리고, 게시판은 이미 시끄럽다.',
                        [dict(kind='team',entity=host),dict(kind='player',entity=person['id'])])
    db.execute('INSERT OR IGNORE INTO stove_weeks VALUES(?,?)',(season,week))
    prune(db)


def feed(db,league='',limit=150):
    """Rumors are always unconfirmed; never mix with completed signings."""
    if not isinstance(league,str) or len(league)>100:
        raise ValueError('invalid league')
    if type(limit) is not int or not 1<=limit<=500:
        raise ValueError('invalid page size')
    sql='''SELECT id,league,event_key,season,week,headline,body,subjects
        FROM league_rumors WHERE headline!='' '''
    params=[]
    if league:
        sql+='AND league=? '
        params.append(league)
    sql+='ORDER BY season DESC,week DESC,id DESC LIMIT ?'
    params.append(limit)
    return [dict(zip(('id','league','event_key','season','week','headline','body','subjects'),row),
                 status='rumor',confirmed=False)
            for row in (
                (id_,comp,key,season,week,headline,body,json.loads(subjects))
                for id_,comp,key,season,week,headline,body,subjects in db.execute(sql,params)
            )]
