"""Shared, ID-based people and club browsing. Preserve imported provenance."""
import json
import os
from collections import defaultdict
import nationality
import leadership
import academy_clubs
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
    # Identity and profession corrections are shared by every feature,
    # not just the club profile: imported staff never become players.
    staff_groups=defaultdict(list)
    for person in people:
        staff_groups[(person.get('league') or '',person.get('team') or '')].append(nationality.enrich(person))
    people[:]=[
        item for (league,team),members in sorted(staff_groups.items())
        for item in leadership.annotate_verified_staff(league,team,members)
    ]
    # Repair only generic *league buckets* in the game view. A bucket is not
    # a real club. The chosen destination is fictional game placement.
    aliases={'LCK 2군':'LCK CL','LCK CL 2군':'LCK CL','LDL 2군':'LDL'}
    # Only confirmed academy clubs; no arbitrary AI placeholder teams.
    destinations={dest:list(academy_clubs.teams(dest)) for dest in set(aliases.values())}
    if any(not names for names in destinations.values()):
        raise ValueError('missing verified academy club roster')
    used=defaultdict(set)
    for person in sorted((p for p in people if p.get('team') in aliases),
                         key=lambda p:(str(p.get('role') or ''),p['id'])):
        original=person['team']
        dest=aliases[original]
        names=destinations[dest]
        role=person.get('role')
        selected=min(names,key=lambda team:(role in used[(dest,team)],len(used[(dest,team)]),team))
        used[(dest,selected)].add(role)
        person['original_team_bucket']=original
        person['team']=selected
        person['league']=dest
        person['assignment_origin']='fictional-game-placement'
    if len({person['id'] for person in people})!=len(people):
        raise ValueError('duplicate person IDs in catalog')
    return data

def display(person):
    return person.get('nickname') or person.get('nickname_ko') or person.get('name') or person.get('display_name_ko') or '닉네임 확인 중'

def game_clubs(db):
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='club_roster'").fetchone(): return {}
    changes={}
    for pid,team,league,role,squad in db.execute('''SELECT r.person_id,c.name,p.league,r.role,r.assignment FROM club_roster r
        JOIN careers c ON c.id=r.career_id JOIN club_profiles p ON p.career_id=c.id WHERE r.assignment!='departed' '''):
        changes[pid]=(team,league,role,squad)
    if db.execute("SELECT 1 FROM sqlite_master WHERE name='person_ownership'").fetchone():
        for pid, in db.execute("SELECT person_id FROM person_ownership WHERE career_id IS NULL AND club_key='free-agent'"):
            changes[pid]=('','',None,None)
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

def display_academy_affiliation(person,changes=None):
    """Display a registered LCK academy member under their genuine LCK CL team.

    Preserve base ownership: top-division team and academy share one roster
    internally, but public competitive affiliation is the verified academy.
    A real transfer/club override takes precedence over affiliation.
    """
    if changes and person.get('id') in changes and person.get('assignment') not in ('academy',):
        return person
    if person.get('league')=='LCK' and person.get('squad')=='academy':
        mapped=academy_clubs.child_of('LCK',person.get('team'))
        if mapped:
            return dict(person,league=mapped[0],team=mapped[1],
                        parent_league='LCK',parent_team=person['team'],
                        academy_affiliation=True)
    return person

def detail(db,career,person_id):
    data=load()
    person=next((p.copy() for p in data['people'] if p['id']==person_id),None)
    if person is None:
        row=db.execute('SELECT payload,assignment FROM generated_people WHERE id=?',(person_id,)).fetchone()
        if row: person=nationality.enrich(dict(json.loads(row[0]),assignment=row[1]))
    if person is None and db.execute("SELECT 1 FROM sqlite_master WHERE name='solo_people'").fetchone():
        row=db.execute('SELECT payload FROM solo_people WHERE person_id=?',(person_id,)).fetchone()
        if row: person=json.loads(row[0])
    if person is None: raise KeyError(person_id)
    person=display_academy_affiliation(apply_game_club(person,game_clubs(db)),game_clubs(db))
    person['display_name']=display(person)
    person['catalog_retrieved']=data.get('retrieved')
    override=db.execute('SELECT value FROM person_overrides WHERE career_id=? AND person_id=?',(career,person_id)).fetchone()
    person['game_evaluation']=json.loads(override[0]) if override else person.get('game_evaluation')
    # Global operator-edited detailed stats also update six core game/scout
    # ratings across every career. Source roster files remain untouched.
    import player_attributes
    player_attributes.apply_to_game_evaluation(db,person)
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
    generated=[nationality.enrich(dict(json.loads(raw),assignment=assignment)) for raw,assignment in db.execute('SELECT payload,assignment FROM generated_people')]
    amateurs=[json.loads(raw) for raw, in db.execute('SELECT payload FROM solo_people')] if db.execute("SELECT 1 FROM sqlite_master WHERE name='solo_people'").fetchone() else []
    unique={p['id']:p for p in amateurs+generated+data['people']}
    for raw_person in unique.values():
        p=display_academy_affiliation(apply_game_club(raw_person,changes),changes)
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
        # Generic roster buckets are not clubs and must never appear as selectable teams.
        if not key[1] or key[1].strip().casefold() in ('ldl 2군','lck 2군','lck cl 2군','ldl reserves','lck reserves'): continue
        group=groups.setdefault(key,dict(league=key[0],team=key[1],players=0,staff=0,unclassified=0))
        group['players' if p.get('kind')=='player' else 'staff' if p.get('kind') in ('coach','staff') else 'unclassified']+=1
    for entry in academy_clubs.entries():
        key=(entry['league'],entry['team'])
        groups.setdefault(key,dict(league=key[0],team=key[1],players=0,staff=0,unclassified=0,
                                   parent_team=entry['parent_team'],parent_league=entry['parent_league'],
                                   source=entry['source'],verified_academy=True))
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
