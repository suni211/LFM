"""Unified autocomplete over the online world's actual entities and aliases."""
import catalog
import clubs

ALIASES={'faker':('페이커','이상혁'),'oner':('오너','문현준'),'doran':('도란','최현준'),
         'keria':('케리아','류민석'),'peyz':('페이즈','김수환'),'zeus':('제우스','최우제'),
         'chovy':('쵸비','정지훈'),'ruler':('룰러','박재혁'),'canyon':('캐니언','김건부'),
         'kiin':('기인','김기인'),'t1':('티원',),'gen.g':('젠지','젠지이스포츠'),
         'hanwha life esports':('한화','한화생명','한화생명이스포츠'),'kt rolster':('케이티','KT롤스터')}

def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS club_owners(
        id INTEGER PRIMARY KEY,career_id INTEGER REFERENCES careers(id),
        name TEXT NOT NULL,company TEXT NOT NULL,source TEXT NOT NULL)''')

def suggest(db,query,limit=12):
    if not isinstance(query,str) or len(query)>120:raise ValueError('invalid search query')
    q=query.strip().casefold()
    if not q:return dict(results=[],query=query)
    candidates=[]
    def add(item,values,priority=0):
        values=[str(v).casefold() for v in values if v]
        scores=[(0 if value==q else 2 if value.startswith(q) else 6)+priority for value in values if q in value]
        if scores:candidates.append((min(scores),item['label'],item))
    changes=catalog.game_clubs(db)
    people=catalog.load()['people']
    import json
    people+= [dict(json.loads(raw),assignment=assignment) for raw,assignment in db.execute('SELECT payload,assignment FROM generated_people')]
    for original in people:
        p=catalog.apply_game_club(original,changes);nick=p.get('nickname') or ''
        aliases=ALIASES.get(nick.casefold(),())[:1]
        name=catalog.display(p)
        label=(p.get('nickname_ko') or nick or name)+' · '+name
        if nick.casefold()=='faker':label=name+' · Faker / 페이커'
        kind='player' if p.get('kind')=='player' else 'staff'
        add(dict(kind=kind,id=p['id'],label=label,subtitle=p.get('team','')+' / '+str(p.get('raw_role') or p.get('role') or '역할 미분류')),
            (name,p.get('real_name'),p.get('nickname_ko'),nick,*aliases),-1 if nick.casefold()=='faker' else 0)
    teams={(p.get('league',''),p.get('team','')) for p in people if p.get('team')}
    teams.update((league,name) for league,name in db.execute('SELECT p.league,c.name FROM club_profiles p JOIN careers c ON c.id=p.career_id'))
    for league,name in teams:
        add(dict(kind='team',id=clubs.key(league,name),label=name,subtitle=league,team=name,league=league),(name,*ALIASES.get(name.casefold(),())))
    for cid,name,club in db.execute('SELECT p.career_id,p.name,c.name FROM manager_profiles p JOIN careers c ON c.id=p.career_id'):
        add(dict(kind='manager',id=cid,label=name,subtitle=club+' 감독'),(name,club),1)
    for oid,name,company,source in db.execute('SELECT id,name,company,source FROM club_owners'):
        add(dict(kind='owner',id=oid,label=name,subtitle=company+' / 구단주',source=source),(name,company),1)
    candidates.sort(key=lambda row:(row[0],row[1],str(row[2]['id'])))
    return dict(results=[row[2] for row in candidates[:limit]],query=query)

def entity(db,kind,entity_id):
    if kind=='owner':
        row=db.execute('SELECT name,company,source,career_id FROM club_owners WHERE id=?',(entity_id,)).fetchone()
        if row:return dict(kind=kind,name=row[0],company=row[1],source=row[2],career_id=row[3])
    elif kind=='manager':
        import json
        row=db.execute('SELECT p.name,p.stats,p.vision,c.name FROM manager_profiles p JOIN careers c ON c.id=p.career_id WHERE p.career_id=?',(entity_id,)).fetchone()
        if row:return dict(kind=kind,name=row[0],stats=json.loads(row[1]),vision=row[2],club=row[3],source='online-game-manager')
    raise KeyError(entity_id)
