"""One club page: roster, coaches, money and results that actually exist."""
import json
from pathlib import Path
import catalog
import clubs
import dashboard
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
    """Public roles are not player records. Unknown identities stay unfilled."""
    entries=[]
    if owner:
        entries.append(dict(name=owner,role='구단주',role_key='OWNER',source='game'))
    if manager:
        entries.append(dict(name=manager,role='감독',role_key='MANAGER',source='game'))
    for person in staff:
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
            role=label,role_key=key,source='real' if person.get('real_person') else 'generated'))
    order={'OWNER':0,'MANAGER':1,'HEAD_COACH':2,'COACH':3,'GM':4,'ANALYST':5,'DOCTOR':6,'COMMUNITY':7}
    return sorted(entries,key=lambda item:(order.get(item['role_key'],9),item['name']))

def view(db, user, league, team):
    import online_world
    rows = people_for(db, league, team)
    career = find_career(db, league, team)
    if career:
        import recruitment
        rows=recruitment.view(db,career['id'])['people']
        rows=[dict(p,display_name=catalog.display(p)) for p in rows if p.get('assignment') not in ('candidate','departed')]
    def academy_player(p):return p.get('assignment')=='academy' if p.get('assignment') else p.get('squad')=='academy'
    players=[p for p in rows if p.get('kind')=='player' and not academy_player(p)]
    academy=[p for p in rows if p.get('kind')=='player' and academy_player(p)]
    staff=[p for p in rows if p.get('kind') in ('coach','staff')]
    other=[p for p in rows if p not in players and p not in academy and p not in staff]
    season=online_world.clock(db)['season']
    standings=dashboard.league_table(db,league,season)
    ranking=next((row for row in standings if row['team']==team),None)
    # A head coach is not automatically the club manager.
    manager_name=None
    body=dict(identity=identity(league,team),players=players,academy=academy,staff=staff,other=other,
              manager=manager_name,owner=None,front_office=front_office(staff),season=season,standing=ranking,news=[],cash_history=[],
              career=None,finances=None,standings=standings,recent=dashboard.last_five(db,team))
    if not career:
        return body
    member = db.execute('SELECT role FROM members WHERE career_id=? AND user_id=?', (career['id'], user)).fetchone()
    operator = online_world.operator(db, user)
    career['role'] = member[0] if member else ('operator' if operator else '')
    body['career'] = career
    manager_row=db.execute('SELECT name FROM manager_profiles WHERE career_id=?',(career['id'],)).fetchone()
    if manager_row:body['manager']=manager_row[0]
    body['front_office']=front_office(staff,body['manager'])
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
