"""Shared, ID-based people and club browsing. Preserve imported provenance."""
import json
import os
from pathlib import Path

PEOPLE=Path(os.environ.get('RIFT_PEOPLE',Path(__file__).resolve().parent.parent/'assets'/'people.json'))
ATTRIBUTES=('라인전','교전','운영','시야','협동','멘탈')

def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS person_overrides(
        career_id INTEGER NOT NULL REFERENCES careers(id), person_id TEXT NOT NULL,
        value TEXT NOT NULL, PRIMARY KEY(career_id,person_id))''')

def load():
    data=json.loads(PEOPLE.read_text(encoding='utf-8'))
    people=data['people']
    if len({person['id'] for person in people})!=len(people):
        raise ValueError('duplicate person IDs in catalog')
    return data

def display(person):
    return person.get('nickname_ko') or person.get('nickname') or person.get('name') or person.get('display_name_ko') or '닉네임 확인 중'

def game_clubs(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='club_roster'").fetchone(): return {}
    changes={}
    for pid,team,league,role,squad in db.execute('''SELECT r.person_id,c.name,p.league,r.role,r.assignment FROM club_roster r
        JOIN careers c ON c.id=r.career_id JOIN club_profiles p ON p.career_id=c.id WHERE r.assignment!='departed' '''):
        changes[pid]=(team,league,role,squad)
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='person_ownership'").fetchone():
        for pid,team,league in db.execute('''SELECT o.person_id,c.name,p.league FROM person_ownership o
            JOIN careers c ON c.id=o.career_id JOIN club_profiles p ON p.career_id=c.id'''):
            if pid not in changes: changes[pid]=(team,league,None,None)
    return changes

def apply_game_club(person,changes):
    if person['id'] not in changes: return person
    team,league,role,squad=changes[person['id']]
    p=dict(person,registered_team=person.get('team'),registered_league=person.get('league'),team=team,league=league)
    if role is not None:
        p['registered_role']=person.get('role');p['game_role_override']=role!=(person.get('role') or '')
        p['role']=role;p['assignment']=squad
        if role=='COACH':p['kind']='coach'
        elif role in ('TOP','JUNGLE','MID','ADC','SUPPORT'):p['kind']='player'
    return p

def detail(db,career,person_id):
    data=load()
    person=next((p.copy() for p in data['people'] if p['id']==person_id),None)
    if person is None:
        row=db.execute('SELECT payload,assignment FROM generated_people WHERE id=?',(person_id,)).fetchone()
        if row: person=dict(json.loads(row[0]),assignment=row[1])
    if person is None and db.execute("SELECT 1 FROM sqlite_master WHERE name='solo_people'").fetchone():
        row=db.execute('SELECT payload FROM solo_people WHERE person_id=?',(person_id,)).fetchone()
        if row: person=json.loads(row[0])
    if person is None: raise KeyError(person_id)
    person=apply_game_club(person,game_clubs(db))
    person['display_name']=display(person)
    person['catalog_retrieved']=data.get('retrieved')
    override=db.execute('SELECT value FROM person_overrides WHERE career_id=? AND person_id=?',(career,person_id)).fetchone()
    person['game_evaluation']=json.loads(override[0]) if override else person.get('game_evaluation')
    import solo
    solo.attach(db,person)
    return person

def search(db,career,page=0,query='',team='',kind='',league='',origin='all'):
    if type(page) is not int or not 0<=page<=100000: raise ValueError('invalid page')
    if any(not isinstance(s,str) or len(s)>120 for s in (query,team,kind,league)):
        raise ValueError('invalid filter')
    if origin not in ('all','real','generated'): raise ValueError('invalid origin')
    if kind not in ('','player','coach','staff'): raise ValueError('invalid kind')
    data=load()
    matches=[]
    query=query.casefold().strip()
    changes=game_clubs(db)
    generated=[dict(json.loads(raw),assignment=assignment) for raw,assignment in db.execute('SELECT payload,assignment FROM generated_people')]
    amateurs=[json.loads(raw) for raw, in db.execute('SELECT payload FROM solo_people')] if db.execute("SELECT 1 FROM sqlite_master WHERE name='solo_people'").fetchone() else []
    unique={p['id']:p for p in amateurs+generated+data['people']}
    for raw_person in unique.values():
        p=apply_game_club(raw_person,changes)
        if origin=='real' and not p.get('real_person') or origin=='generated' and p.get('real_person'): continue
        if team and p.get('assignment')=='candidate': continue
        if team and p.get('team')!=team or kind=='staff' and p.get('kind') not in ('coach','staff') or kind and kind!='staff' and p.get('kind')!=kind or league and p.get('league')!=league: continue
        if query and query not in ' '.join(str(p.get(k) or '') for k in ('display_name_ko','real_name_ko','real_name','nickname','nickname_ko','team')).casefold(): continue
        matches.append(dict(p,display_name=display(p)))
    matches.sort(key=lambda p:(p['display_name'],p['id']))
    return dict(people=matches[page*150:(page+1)*150],total=len(matches),page=page,page_size=150,
                retrieved=data.get('retrieved'),source=data.get('source'))

def teams():
    groups={}
    for p in load()['people']:
        if not p.get('real_person'): continue
        key=(p.get('league',''),p.get('team',''))
        if not key[1]: continue
        group=groups.setdefault(key,dict(league=key[0],team=key[1],players=0,staff=0,unclassified=0))
        group['players' if p.get('kind')=='player' else 'staff' if p.get('kind')=='coach' else 'unclassified']+=1
    return list(sorted(groups.values(),key=lambda row:(row['league'],row['team'])))

def evaluate(db,career,person_id,ratings,form,note):
    detail(db,career,person_id)
    if (not isinstance(ratings,dict) or set(ratings)!=set(ATTRIBUTES) or
        any(type(v) is not int or not 1<=v<=100 for v in ratings.values()) or
        type(form) is not int or not 1<=form<=100 or
        not isinstance(note,str) or not 1<=len(note.strip())<=1000):
        raise ValueError('invalid game evaluation')
    value=dict(ratings=ratings,form=form,note=note.strip(),origin='game-admin',year=2026)
    db.execute('''INSERT INTO person_overrides VALUES(?,?,?)
        ON CONFLICT(career_id,person_id) DO UPDATE SET value=excluded.value''',
        (career,person_id,json.dumps(value,ensure_ascii=False)))
    return value
