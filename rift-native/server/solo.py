"""Solo queue ladder, amateur talks, prospect development and retirement.

Pros can be signed. Amateurs cannot. A conversation can turn an amateur into
your prospect. With no results they retire sooner, unless their personality
is stubborn enough to keep queueing.
"""
import hashlib
import itertools
import json
import uuid
import catalog
import club_messages

PERSONALITIES=('독함','꾸준','조급')
PATHS=('amateur','prospect','pro','retired')
ROLES=('TOP','JUNGLE','MID','ADC','SUPPORT')
PATH_NAME={'amateur':'일반인','prospect':'유망주','pro':'프로','retired':'은퇴'}
STALL_GAIN={'독함':1,'꾸준':2,'조급':3}
STALL_LIMIT={'독함':24,'꾸준':12,'조급':6}
TALK_CHANCE={'독함':0.30,'꾸준':0.52,'조급':0.70}
DEBUT_MMR=1100
PRO_MIN_MMR=2800  # Master 0 LP floor for all professional solo-queue records
PROSPECT_LIMIT=15
MAJOR={'LCK','LPL','LEC','LCS'}

def init(db):
    db.executescript('''CREATE TABLE IF NOT EXISTS solo_ranks(
        person_id TEXT PRIMARY KEY, mmr INTEGER NOT NULL, games INTEGER NOT NULL DEFAULT 0,
        path TEXT NOT NULL, personality TEXT NOT NULL, career_id INTEGER,
        stall INTEGER NOT NULL DEFAULT 0, last_talk_turn INTEGER NOT NULL DEFAULT -1,
        nickname TEXT NOT NULL, real_name TEXT NOT NULL, role TEXT NOT NULL, club_name TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS solo_people(person_id TEXT PRIMARY KEY, payload TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS solo_weeks(season INTEGER NOT NULL, week INTEGER NOT NULL, PRIMARY KEY(season,week));
        CREATE TABLE IF NOT EXISTS solo_seed(key TEXT PRIMARY KEY, value TEXT NOT NULL);''')
    if not db.execute("SELECT 1 FROM solo_seed WHERE key='ready'").fetchone():
        backfill(db)
        db.execute("INSERT OR REPLACE INTO solo_seed VALUES('ready','1')")
    seed_easter(db)
    db.execute("UPDATE solo_ranks SET mmr=? WHERE path='pro' AND mmr<?",(PRO_MIN_MMR,PRO_MIN_MMR))

def _unit(key):
    return int.from_bytes(hashlib.sha256(key.encode()).digest()[:4],'big')/4294967295

def personality_of(person_id):
    return PERSONALITIES[int(_unit(person_id+':personality')*3)]

def describe(mmr):
    mmr=max(0,int(mmr))
    if mmr>=3400: return f'챌린저 {mmr-3400}LP'
    if mmr>=3100: return f'그랜드마스터 {mmr-3100}LP'
    if mmr>=2800: return f'마스터 {mmr-2800}LP'
    floors=((2400,'다이아몬드'),(2000,'에메랄드'),(1600,'플래티넘'),(1200,'골드'),(800,'실버'),(400,'브론즈'),(0,'아이언'))
    for floor,name in floors:
        if mmr>=floor:
            within=mmr-floor
            roman=('IV','III','II','I')[min(3,within//100)]
            return f'{name} {roman} {within%100}LP'
    return '아이언 IV 0LP'

def start_mmr(person, path):
    spread=int(_unit(person['id']+':mmr')*360)
    if path=='pro':
        league=person.get('league') or ''
        base=3220 if league in MAJOR else 2950 if ('CL' in league or 'Academy' in league or 'Challengers' in league or 'LDL' in league) else 2850
        return max(PRO_MIN_MMR,base+spread//2)
    return 280+int(_unit(person['id']+':amateur')*1050)

def public_row(row, rank=None):
    if not row: return None
    person_id,mmr,games,path,personality,career_id,stall,last_talk,nickname,real_name,role,club=row[:12]
    item=dict(id=person_id,mmr=mmr,games=games,path=path,path_name=PATH_NAME.get(path,path),
              personality=personality,career_id=career_id,stall=stall,nickname=nickname,real_name=real_name,
              role=role,club=club,label=describe(mmr),debut_ready=path=='prospect' and mmr>=DEBUT_MMR)
    if rank is not None: item['rank']=rank
    return item

def fetch(db, person_id):
    return db.execute('''SELECT person_id,mmr,games,path,personality,career_id,stall,last_talk_turn,nickname,real_name,role,club_name
        FROM solo_ranks WHERE person_id=?''',(person_id,)).fetchone()

def _insert(db, person, path, career_id=None, club=''):
    if person.get('kind') not in ('player',None) and person.get('role') not in ROLES: return None
    if person.get('kind') in ('coach','staff'): return None
    role=person.get('role') if person.get('role') in ROLES else ROLES[int(_unit(person['id']+':role')*5)]
    nickname=person.get('nickname') or person.get('display_name') or person.get('real_name') or '무명'
    real=person.get('display_name_ko') or person.get('real_name') or nickname
    mmr=start_mmr(person,path)
    db.execute('''INSERT OR IGNORE INTO solo_ranks(person_id,mmr,games,path,personality,career_id,stall,nickname,real_name,role,club_name)
        VALUES(?,?,0,?,?,?,0,?,?,?,?)''',(person['id'],mmr,path,personality_of(person['id']),career_id,nickname,real,role,club or person.get('team') or ''))
    return fetch(db, person['id'])

def ensure(db, person, path='pro', career_id=None, club=''):
    row=fetch(db, person['id'])
    if row: return row
    return _insert(db, person, path, career_id, club)

def attach(db, person):
    if not isinstance(person,dict) or person.get('kind') in ('coach','staff'): return person
    if person.get('kind') not in ('player',None) and person.get('role') not in ROLES: return person
    row=fetch(db, person.get('id',''))
    if row is None and person.get('kind')=='player' and person.get('real_person'):
        row=ensure(db, person, 'pro', club=person.get('team') or '')
    if row: person['solo']=public_row(row)
    return person

def seed_easter(db):
    """Idempotent academy prospects. The live ladder already has solo_seed ready, so this is a separate key."""
    if db.execute("SELECT 1 FROM solo_seed WHERE key='easter-academy'").fetchone(): return
    found=0
    for person in catalog.load().get('people',[]):
        if not person.get('easter_egg'): continue
        found+=1
        db.execute('INSERT OR REPLACE INTO solo_people(person_id,payload) VALUES(?,?)',(person['id'],json.dumps(person,ensure_ascii=False)))
        mmr=1120+int(_unit(person['id']+':easter')*420)
        nickname=person.get('nickname') or person.get('real_name') or '무명'
        real=person.get('display_name_ko') or person.get('real_name') or nickname
        role=person.get('role') if person.get('role') in ROLES else 'TOP'
        club=person.get('team') or ''
        if fetch(db, person['id']):
            db.execute('''UPDATE solo_ranks SET mmr=?,path='prospect',personality=?,career_id=NULL,stall=0,
                nickname=?,real_name=?,role=?,club_name=? WHERE person_id=?''',
                (mmr,personality_of(person['id']),nickname,real,role,club,person['id']))
        else:
            _insert(db, person, 'prospect', None, club)
            db.execute('UPDATE solo_ranks SET mmr=? WHERE person_id=?',(mmr,person['id']))
    if found:
        db.execute("INSERT OR REPLACE INTO solo_seed VALUES('easter-academy','1')")

def claim_club(db, career, team):
    if not isinstance(team,str) or not team: return
    db.execute('''UPDATE solo_ranks SET career_id=?,club_name=?
        WHERE path='prospect' AND club_name=? AND career_id IS NULL''',(career,team,team))

def backfill(db):
    seeded=db.execute("SELECT 1 FROM sqlite_master WHERE name='solo_ranks'").fetchone()
    if not seeded: return
    for person in catalog.load().get('people',[]):
        if person.get('kind')=='player':
            ensure(db, person, 'pro', club=person.get('team') or '')
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='generated_people'").fetchone():
        for pid,raw,career,assignment in db.execute('SELECT id,payload,career_id,assignment FROM generated_people'):
            if fetch(db,pid): continue
            person=json.loads(raw)
            if person.get('kind')!='player': continue
            path='pro' if assignment in ('first','reserve') else 'prospect' if assignment in ('academy','staff') else 'amateur'
            club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()
            _insert(db, person, path, career, club[0] if club else '')
            if path!='amateur':
                db.execute('UPDATE solo_ranks SET career_id=?,club_name=? WHERE person_id=?',(career,club[0] if club else '',pid))
    # No random unattached solo-player pool. Recruitable players must come from
    # the club recruitment system, saved prospects, or registered player data.

def is_pro(db, person_id):
    row=fetch(db, person_id)
    return bool(row and row[3]=='pro')

def require_pro(db, person_id):
    row=fetch(db, person_id)
    if row and row[3]!='pro':
        raise ValueError('amateurs and prospects cannot be signed')

def ladder(db, career, role=''):
    if role not in ('',*ROLES): raise ValueError('invalid role')
    rows=db.execute('''SELECT person_id,mmr,games,path,personality,career_id,stall,last_talk_turn,nickname,real_name,role,club_name
        FROM solo_ranks WHERE path!='retired' AND (?='' OR role=?) ORDER BY mmr DESC, nickname LIMIT 100''',(role,role)).fetchall()
    board=[public_row(row,index+1) for index,row in enumerate(rows)]
    mine_rows=db.execute('''SELECT person_id,mmr,games,path,personality,career_id,stall,last_talk_turn,nickname,real_name,role,club_name
        FROM solo_ranks WHERE career_id=? AND path IN ('amateur','prospect') ORDER BY path, mmr DESC''',(career,)).fetchall()
    return dict(role=role,rows=board,mine=[public_row(row) for row in mine_rows],
                debut_at=describe(DEBUT_MMR),personalities=list(PERSONALITIES))

def _turn(db):
    import online_world
    clock=online_world.clock(db)
    return clock,(clock['season']-1)*104+clock['week']

def _payload(db, person_id):
    row=db.execute('SELECT payload FROM solo_people WHERE person_id=?',(person_id,)).fetchone()
    if row: return json.loads(row[0])
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='generated_people'").fetchone():
        found=db.execute('SELECT payload FROM generated_people WHERE id=?',(person_id,)).fetchone()
        if found: return json.loads(found[0])
    for person in catalog.load().get('people',[]):
        if person['id']==person_id: return person
    raise KeyError(person_id)

def talk(db, career, person_id):
    if not isinstance(person_id,str): raise ValueError('invalid player')
    row=fetch(db, person_id)
    if row is None: raise KeyError(person_id)
    path,personality,owner,last_talk=row[3],row[4],row[5],row[7]
    if path=='pro': raise ValueError('already a pro player')
    if path=='retired': raise ValueError('player has retired')
    if path=='prospect':
        if owner==career: raise ValueError('already your prospect')
        raise ValueError('another club is developing this player')
    if owner not in (None,career): raise ValueError('this player is in another club tryout')
    held=db.execute("SELECT COUNT(*) FROM solo_ranks WHERE career_id=? AND path='prospect'",(career,)).fetchone()[0]
    if held>=PROSPECT_LIMIT: raise ValueError('prospect list is full')
    clock,turn=_turn(db)
    if last_talk>=0 and turn-last_talk<4: raise ValueError('talk again later')
    chance=TALK_CHANCE[personality]+(0.08 if row[1]>=DEBUT_MMR else 0)
    accepted=_unit(f'{person_id}:{career}:{turn//4}')<chance
    db.execute('UPDATE solo_ranks SET last_talk_turn=? WHERE person_id=?',(turn,person_id))
    club=db.execute('SELECT name FROM careers WHERE id=?',(career,)).fetchone()[0]
    if not accepted:
        club_messages.publish(db,career,'solo-talk:'+person_id+':'+str(turn//4),clock['season'],clock['week'],'일반인 대화',
                              row[8]+'은 이번 대화에서 유망주 제안을 받아들이지 않았습니다. '+personality+' 성격이라 다음 대화까지 시간이 필요합니다.')
        import rumors
        rumors.scout(db,career,person_id,row[8],False)
        return dict(accepted=False,player=public_row(fetch(db,person_id)))
    person=_payload(db, person_id)
    person.update(kind='player',team=club,league='LCK CL',real_person=False)
    db.execute('UPDATE solo_ranks SET path=?,career_id=?,club_name=?,stall=0 WHERE person_id=?',('prospect',career,club,person_id))
    if db.execute('SELECT 1 FROM generated_people WHERE id=?',(person_id,)).fetchone():
        db.execute("UPDATE generated_people SET career_id=?,assignment='academy',payload=? WHERE id=?",(career,json.dumps(person,ensure_ascii=False),person_id))
    else:
        db.execute('INSERT INTO generated_people(id,real_name,nickname_key,career_id,payload,assignment) VALUES(?,?,?,?,?,?)',
                   (person_id,person.get('real_name') or row[9],str(row[8]).casefold(),career,json.dumps(person,ensure_ascii=False),'academy'))
    club_messages.publish(db,career,'solo-prospect:'+person_id,clock['season'],clock['week'],'유망주 합류',
                          row[8]+'이 대화 끝에 유망주가 되기로 했습니다. 솔로랭크 성과가 없으면 은퇴가 빨라지고, 독하게 버티는 선수는 더 오래 남습니다.')
    import rumors
    rumors.scout(db,career,person_id,row[8],True)
    return dict(accepted=True,player=public_row(fetch(db,person_id)))

def debut(db, career, person_id):
    if not isinstance(person_id,str): raise ValueError('invalid player')
    row=fetch(db, person_id)
    if row is None: raise KeyError(person_id)
    if row[3]!='prospect' or row[5]!=career: raise ValueError('not your prospect')
    if row[1]<DEBUT_MMR: raise ValueError('not ready for pro debut')
    role=row[10] if row[10] in ROLES else 'TOP'
    taken=db.execute("SELECT 1 FROM solo_ranks WHERE career_id=? AND role=? AND path='pro'",(career,role)).fetchone()
    assignment='reserve' if taken else 'first'
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='generated_people'").fetchone() and db.execute('SELECT 1 FROM generated_people WHERE id=?',(person_id,)).fetchone():
        busy=db.execute("SELECT id,payload FROM generated_people WHERE career_id=? AND assignment='first'",(career,)).fetchall()
        for pid,raw in busy:
            if pid!=person_id and json.loads(raw).get('role')==role and assignment=='first':
                assignment='reserve'
        raw=json.loads(db.execute('SELECT payload FROM generated_people WHERE id=?',(person_id,)).fetchone()[0])
        raw['role']=role; raw['kind']='player'
        db.execute('UPDATE generated_people SET assignment=?,payload=? WHERE id=?',(assignment,json.dumps(raw,ensure_ascii=False),person_id))
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='club_roster'").fetchone():
        db.execute("UPDATE club_roster SET assignment=? WHERE person_id=? AND assignment='academy'",(assignment,person_id))
    db.execute("UPDATE solo_ranks SET path='pro',mmr=MAX(mmr,?),stall=0 WHERE person_id=?",(PRO_MIN_MMR,person_id))
    clock,_=_turn(db)
    club_messages.publish(db,career,'solo-debut:'+person_id,clock['season'],clock['week'],'프로 데뷔',
                          row[8]+'을 구단에서 직접 키운 뒤 프로로 데뷔시켰습니다. 이제 선발과 영입 시장에 프로로 올라갑니다.')
    import rumors
    rumors.debut(db,career,person_id,row[8])
    return public_row(fetch(db,person_id))

def _retire(db, row, season, week):
    person_id,personality,career_id,nickname=row[0],row[4],row[5],row[8]
    db.execute("UPDATE solo_ranks SET path='retired',club_name='' WHERE person_id=?",(person_id,))
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='generated_people'").fetchone():
        db.execute("UPDATE generated_people SET assignment='departed' WHERE id=?",(person_id,))
    if career_id:
        pace='독하게 버티다 결국' if personality=='독함' else '성과가 없어 빨리' if personality=='조급' else '성과 없이 시간이 지나'
        club_messages.publish(db,career_id,'solo-retire:'+person_id,season,week,'유망주 은퇴',
                              nickname+'이 '+pace+' 은퇴했습니다. 솔로랭크에서 성과가 이어지지 않았습니다.')

def weekly(db, season, week):
    if not db.execute('INSERT OR IGNORE INTO solo_weeks VALUES(?,?)',(season,week)).rowcount: return
    rows=db.execute('''SELECT person_id,mmr,games,path,personality,career_id,stall,last_talk_turn,nickname,real_name,role,club_name
        FROM solo_ranks WHERE path IN ('amateur','prospect','pro')''').fetchall()
    for row in rows:
        person_id,mmr,games,path,personality=row[0],row[1],row[2],row[3],row[4]
        roll=_unit(f'{person_id}:{season}:{week}:solo')
        if personality=='독함': roll=min(1,roll+0.12)
        elif personality=='조급': roll=max(0,roll-0.08)
        if roll<0.22: delta=-18+int(roll*20)
        elif roll<0.48: delta=-3+int((roll-0.22)*20)
        else: delta=8+int((roll-0.48)*40)
        stall=row[6]
        if delta<8: stall+=STALL_GAIN[personality]
        else: stall=max(0,stall-2)
        if path!='pro' and stall>=STALL_LIMIT[personality]:
            _retire(db,row,season,week)
            continue
        floor=PRO_MIN_MMR if path=='pro' else 0
        # These are independent weekly solo-queue simulations, not pro match results.
        db.execute('UPDATE solo_ranks SET mmr=?,games=games+1,stall=? WHERE person_id=?',(max(floor,mmr+delta),0 if path=='pro' else stall,person_id))

def _rating(player, won, team_damage):
    kills,deaths,assists=player.get('kda',[0,0,0])
    share=player.get('damage',0)/max(1,team_damage)
    expected={'TOP':.2,'JUNGLE':.18,'MID':.25,'ADC':.25,'SUPPORT':.12}.get(player.get('role'),.2)
    return max(1,min(9.9,6+min(1.4,kills*.18+assists*.08)-min(3.5,deaths*.38)+(0.5 if won else -0.3)+(share-expected)*2))

def record_result(db, result):
    """Professional match results do not change individual solo queue ratings.

    Team competition performance is recorded by management.record_match.
    Solo queue MMR is advanced only by separate solo queue simulations.
    """
    return None


def repair_legacy_handles(db):
    """Update generated amateur handle data without changing real player identities."""
    import re
    prefixes=('Aero','Ash','Blue','Cinder','Dawn','Ember','Frost','Gale','Haze','Iron','Jade','Lunar','Mist','Night','Opal','Pine','Quartz','Raven','Silver','Thorn')
    suffixes=('Arc','Bloom','Crest','Drift','Echo','Flare','Grove','Hawk','Iris','Jet','Knight','Leaf','Moon','Nova','Oath','Peak','Quill','Rise','Storm','Vale')
    used={str(n).casefold() for n, in db.execute('SELECT nickname FROM solo_ranks')}
    for pid,raw in db.execute('SELECT person_id,payload FROM solo_people').fetchall():
        p=json.loads(raw)
        if not pid.startswith('amateur-'): continue
        old=str(p.get('nickname') or '')
        if re.fullmatch(r'[A-Za-z]{2,20}',old): continue
        seed=int(hashlib.sha256(pid.encode()).hexdigest(),16)
        for offset in range(100000):
            n=seed+offset
            nick=prefixes[n%len(prefixes)]+suffixes[(n//len(prefixes))%len(suffixes)]
            if offset>=len(prefixes)*len(suffixes):
                count=offset//(len(prefixes)*len(suffixes))
                ending=''
                while count:
                    count,r=divmod(count-1,26);ending=chr(65+r)+ending
                nick+=ending
            if nick.casefold() not in used:break
        else: raise ValueError('amateur nickname space exhausted')
        used.add(nick.casefold())
        p.update(original_nickname=old,nickname=nick)
        p.pop('nickname_ko',None)
        db.execute('UPDATE solo_people SET payload=? WHERE person_id=?',(json.dumps(p,ensure_ascii=False),pid))
        db.execute('UPDATE solo_ranks SET nickname=? WHERE person_id=?',(nick,pid))
