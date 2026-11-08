"""One club page: roster, coaches, money and results that actually exist."""
import json
from pathlib import Path
import catalog
import clubs
import dashboard
import leadership
import staffing

def roots():
    here = Path(__file__).resolve().parent
    assets = here / 'assets' if (here / 'assets').exists() else here.parent / 'assets'
    return assets

def colors():
    path = roots() / 'club-colors.json'
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))

def logos():
    path = roots() / 'club-assets.json'
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding='utf-8'))

def identity(league, team):
    key = league + '\n' + team
    logo = logos().get(key, {})
    return dict(league=league, team=team, color=colors().get(key, '#17324d'),
                logo=logo.get('logo', ''), source=logo.get('source', ''))

def people_for(db, league, team):
    changes = catalog.game_clubs(db)
    rows = []
    for person in catalog.load()['people']:
        current = catalog.apply_game_club(person, changes)
        if current.get('league') == league and current.get('team') == team:
            rows.append(dict(current, display_name=catalog.display(current)))
    return rows

def find_career(db, league, team):
    team_key = clubs.key(league, team)
    row = db.execute('''SELECT c.id,c.name,c.season,c.week FROM careers c
        JOIN club_profiles p ON p.career_id=c.id
        WHERE p.team_key=? OR (c.name=? AND p.league=?) LIMIT 1''', (team_key, team, league)).fetchone()
    if not row:
        return None
    return dict(id=row[0], name=row[1], season=row[2], week=row[3])

def front_office(staff,manager=None,owner=None):
    """Owner/operator, manager, head coach and coaching staff are separate."""
    entries=[]
    if owner:
        entries.append(dict(name=owner['name'],role='구단주·운영 주체',role_key='OWNER',
            source=owner['source'],source_url=owner.get('source_url'),show_nationality=False))
        if owner.get('representative'):
            entries.append(dict(name=owner['representative'],role=owner.get('representative_role') or '운영 대표',
                role_key='EXECUTIVE',source=owner['source'],source_url=owner.get('source_url'),show_nationality=False))
    if manager:
        entries.append(dict(name=manager['name'],role='감독',role_key='MANAGER',
            source=manager.get('source','game'),person_id=manager.get('person_id'),
            nationality_name_ko=manager.get('nationality_name_ko'),
            nationality_code=manager.get('nationality_code'),source_url=manager.get('source_url')))
    for person in staff:
        if manager and person.get('id')==manager.get('person_id'):
            continue
        raw=str(person.get('raw_role') or '').casefold()
        assigned=str(person.get('staff_role') or '')
        if 'head coach' in raw or '수석' in raw or assigned=='HEAD_COACH':
            key,label='HEAD_COACH','수석코치'
        elif 'manager' in raw and 'general' not in raw or '감독' in raw:
            key,label='MANAGER','감독'
        elif assigned=='GM' or 'general manager' in raw or '단장' in raw:
            key,label='GM','단장'
        elif assigned=='ANALYST' or 'analyst' in raw or '분석' in raw:
            key,label='ANALYST','분석관'
        elif assigned=='DOCTOR' or 'doctor' in raw or '닥터' in raw:
            key,label='DOCTOR','팀 닥터'
        elif assigned=='COMMUNITY':
            key,label='COMMUNITY','홍보 담당'
        else:
            key,label='COACH','코치'
        entries.append(dict(id=person.get('id'),name=catalog.display(person),
            role=label,role_key=key,source='real' if person.get('real_person') else 'generated',
            nationality_name_ko=person.get('nationality_name_ko'),
            nationality_code=person.get('nationality_code'),nationality=person.get('nationality'),
            source_url=person.get('staff_role_source')))
    order={'OWNER':0,'EXECUTIVE':1,'MANAGER':2,'HEAD_COACH':3,'COACH':4,'GM':5,
           'ANALYST':6,'DOCTOR':7,'COMMUNITY':8}
    return sorted(entries,key=lambda item:(order.get(item['role_key'],10),item['name']))

def view(db, user, league, team):
    import online_world
    rows = people_for(db, league, team)
    career = find_career(db, league, team)
    if career:
        import recruitment
        rows=recruitment.view(db,career['id'])['people']
        rows=[dict(p,display_name=catalog.display(p)) for p in rows if p.get('assignment') not in ('candidate','departed')]
    rows=leadership.annotate_verified_staff(league,team,rows)
    def academy_player(p):return p.get('assignment')=='academy' if p.get('assignment') else p.get('squad')=='academy'
    players=[p for p in rows if p.get('kind')=='player' and not academy_player(p)]
    academy=[p for p in rows if p.get('kind')=='player' and academy_player(p)]
    staff=[p for p in rows if p.get('kind') in ('coach','staff')]
    other=[p for p in rows if p not in players and p not in academy and p not in staff]
    season=online_world.clock(db)['season']
    standings=dashboard.league_table(db,league,season)
    ranking=next((row for row in standings if row['team']==team),None)
    owner_info=leadership.owner_info(league,team,bool(career and db.execute(
        "SELECT 1 FROM club_profiles WHERE career_id=? AND mode='create'",(career['id'],)).fetchone()))
    manager_info=leadership.ai_manager(rows,league,team)
    body=dict(identity=identity(league,team),players=players,academy=academy,staff=staff,other=other,
              manager=manager_info['name'],manager_info=manager_info,
              owner=owner_info['name'],owner_info=owner_info,
              front_office=front_office(staff,manager_info,owner_info),
              season=season,standing=ranking,news=[],cash_history=[],
              career=None,finances=None,standings=standings,recent=dashboard.last_five(db,team))
    if not career:
        return body
    member = db.execute('SELECT role FROM members WHERE career_id=? AND user_id=?', (career['id'], user)).fetchone()
    operator = online_world.operator(db, user)
    career['role'] = member[0] if member else ('operator' if operator else '')
    body['career'] = career
    manager_row=db.execute('SELECT name FROM manager_profiles WHERE career_id=?',(career['id'],)).fetchone()
    human=clubs.human_owner(db,career['id'])
    if manager_row and human:
        import nationality
        own=db.execute("""SELECT a.nationality_code FROM members m
            JOIN account_managers a ON a.user_id=m.user_id
            WHERE m.career_id=? AND m.role='admin'
            AND m.user_id NOT IN (SELECT user_id FROM league_operators)
            ORDER BY m.user_id LIMIT 1""",(career['id'],)).fetchone()
        code=own[0] if own else ''
        body['manager_info']=dict(name=manager_row[0],source='user',role='감독',
              nationality_name_ko=nationality.COUNTRIES.get(code,''),
              nationality_code=code,person_id=None)
        body['manager']=manager_row[0]
    body['front_office']=front_office(staff,body['manager_info'],owner_info)
    body['news']=[dict(season=sn,week=wk,headline=headline,body=summary)
        for sn,wk,headline,summary in db.execute(
            'SELECT season,week,headline,body FROM career_news WHERE career_id=? ORDER BY season DESC,week DESC,id DESC LIMIT 8',(career['id'],))]
    if member or operator:
        try:
            money = __import__('management').snapshot(db, career['id'])
        except Exception:
            money = {'initialized': False}
        body['finances'] = dict(initialized=money.get('initialized', False), cash=money.get('cash'),
                                transfer_budget=money.get('transfer_budget'), wage_budget=money.get('wage_budget'),
                                annual_payroll=money.get('annual_payroll'), board=money.get('board'), fans=money.get('fans'),
                                ledger=(money.get('ledger') or [])[:12], staff_limits=money.get('staff_limits') or [],
                                contracts=[{'id': c['person']['id'], 'name': catalog.display(c['person']),
                                            'role': c['person'].get('role'), 'salary': c['annual_salary'],
                                            'remaining': c['remaining_turns']} for c in money.get('contracts') or []])
        season = career['season']
        body['standings'] = dashboard.league_table(db, league, season)
        body['recent'] = dashboard.last_five(db, career['name'])
        body['standing']=next((row for row in body['standings'] if row['team']==team),None)
        if money.get('initialized'):
            body['cash_history']=dashboard.cash_history(db,career['id'])
    return body
