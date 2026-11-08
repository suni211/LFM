"""Local authoritative career service. Bind to loopback; use TLS proxy for deployment."""
import hashlib, hmac, json, os, secrets, sqlite3, time
from contextlib import closing
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
import fixtures
import league
import news
import competition_rules
import qualification
import catalog
import club_messages
import recruitment
import clubs
import online_world
import management
import manager_identity
import analytics
import transfers
import fan_community as community
import staffing
import search
import dashboard
import solo
import player_departures
import scouting
import career_rules
import rookie_offers
import promotion
import club_history
import sponsorship
import series_state
import manual_draft
from highlight_recording import clip_path

DB = Path(os.environ.get('RIFT_DB', Path(__file__).with_name('server.db')))
def connect():
    db = sqlite3.connect(DB, timeout=10, isolation_level=None)
    db.execute('PRAGMA foreign_keys=ON')
    return db

def init():
    with closing(connect()) as db:
        db.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, salt BLOB NOT NULL, password BLOB NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id), expires INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS careers(id INTEGER PRIMARY KEY, name TEXT NOT NULL, week INTEGER NOT NULL DEFAULT 1, season INTEGER NOT NULL DEFAULT 1, version INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS members(career_id INTEGER NOT NULL REFERENCES careers(id), user_id INTEGER NOT NULL REFERENCES users(id), role TEXT NOT NULL, PRIMARY KEY(career_id,user_id));
        CREATE TABLE IF NOT EXISTS settings(career_id INTEGER NOT NULL REFERENCES careers(id), key TEXT NOT NULL, value TEXT NOT NULL, PRIMARY KEY(career_id,key));
        CREATE TABLE IF NOT EXISTS votes(career_id INTEGER NOT NULL, user_id INTEGER NOT NULL, season INTEGER NOT NULL, week INTEGER NOT NULL, PRIMARY KEY(career_id,user_id,season,week));''')
        fixtures.init(db)
        league.init(db)
        news.init(db)
        competition_rules.init(db)
        qualification.init(db)
        catalog.init(db)
        club_messages.init(db)
        recruitment.init(db)
        clubs.init(db)
        online_world.init(db)
        management.init(db)
        manager_identity.init(db)
        clubs.refresh_catalog(db)
        recruitment.repair_generated_handles(db)
        transfers.init(db)
        community.init(db)
        staffing.init(db)
        search.init(db)
        solo.init(db)
        player_departures.init(db)
        scouting.init(db)
        career_rules.init(db)
        rookie_offers.init(db)
        club_history.init(db)
        promotion.init(db)
        sponsorship.init(db)
        solo.repair_legacy_handles(db)
        recruitment.repair_initial_pool(db)
        import training
        training.init(db)
        db.execute('''CREATE TABLE IF NOT EXISTS user_preferences(
            user_id INTEGER PRIMARY KEY REFERENCES users(id), dashboard TEXT NOT NULL)''')
        import rumors
        rumors.init(db)

def derive(password, salt): return hashlib.scrypt(password.encode(), salt=salt, n=16384, r=8, p=1)
class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass
    def reply(self, status, value):
        if status>=400:
            print(json.dumps({'event':'api_error','method':self.command,'path':urlsplit(self.path).path,
                'status':status,'error':value.get('error','')},ensure_ascii=False),flush=True)
        body=json.dumps(value,ensure_ascii=False).encode(); self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store'); self.send_header('Content-Length',str(len(body))); self.end_headers(); self.wfile.write(body)
    def input(self):
        n=int(self.headers.get('Content-Length','0'))
        limit=131072 if self.path in ('/community-create','/community-edit','/careers','/club-logo','/operator/club-identity') else 16384
        if n<=0 or n>limit: raise ValueError('invalid body')
        value=json.loads(self.rfile.read(n));
        if not isinstance(value,dict): raise ValueError('invalid body')
        return value
    def user(self,db):
        auth=self.headers.get('Authorization','')
        if not auth.startswith('Bearer '): return None
        token=hashlib.sha256(auth[7:].encode()).hexdigest()
        row=db.execute('SELECT user_id FROM sessions WHERE token_hash=? AND expires>?',(token,int(time.time()))).fetchone()
        return row[0] if row else None
    def normalize_path(self):
        url=urlsplit(self.path);path=url.path
        if path.startswith('/rift/api/'):path=path[len('/rift/api'):]
        self.path=(path.rstrip('/') or '/')+('?' + url.query if url.query else '')
    def do_GET(self):
        self.normalize_path()
        if self.public(): return
        try:self.get()
        except (ValueError,TypeError,KeyError):self.reply(400,{'error':'invalid request'})
        except FileNotFoundError:self.reply(503,{'error':'game data unavailable'})
        except Exception:
            import traceback
            traceback.print_exc();self.reply(500,{'error':'server processing error'})
    def get(self):
        with closing(connect()) as db:
            uid=self.user(db)
            if urlsplit(self.path).path=='/health':
                _,web=self.roots()
                fingerprints={filename:hashlib.sha256((web/filename).read_bytes()).hexdigest()[:16]
                    if (web/filename).is_file() else None
                    for filename in ('index.html','app.js','app.css')}
                return self.reply(200,{'status':'ok','revision':'rift-ui-fresh-20261108',
                    'web_sha256':fingerprints,'capabilities':['clubs','dashboard','search','community','draft-swap','management','fearless','response-timeout-180','manual-draft','fountain-defense','backdoor-protection','six-slot-builds','competitions','account-errors','tactics','phase-orders','personal-training','champion-pool','solo-ladder','prospect-debut','operator-desk','stove-leaks','easter-academy','client-updates','web'],'champion_abilities':'partial'})
            if urlsplit(self.path).path.startswith('/updates/'):
                import updates
                return updates.serve(self, urlsplit(self.path).path)
            if not uid: return self.reply(401,{'error':'unauthorized'})
            url = urlsplit(self.path)
            if url.path=='/operator/world':
                if not online_world.operator(db,uid):return self.reply(403,{'error':'forbidden'})
                world=online_world.clock(db)
                games=[dict(zip(('id','season','week','team','opponent','state','competition','stage','best_of'),r)) for r in db.execute('SELECT f.id,f.season,f.week,c.name,f.opponent,f.state,f.competition,f.stage,f.best_of FROM fixtures f JOIN careers c ON c.id=f.career_id WHERE f.season=? ORDER BY f.week,f.id',(world['season'],))]
                return self.reply(200,dict(world=world,clubs=clubs.directory(db),fixtures=games,accounts=db.execute('SELECT COUNT(*) FROM users').fetchone()[0],qualification=qualification.snapshot(db,world['season'])))
            if url.path=='/qualification':
                season=int(parse_qs(url.query).get('season',[online_world.clock(db)['season']])[0])
                if not 1<=season<=10000:raise ValueError('invalid season')
                return self.reply(200,qualification.snapshot(db,season))
            if url.path=='/manager-profile': return self.reply(200,manager_identity.view(db,uid))
            if url.path=='/club-brandings':
                # Public club visual identity only. Uploaded game-club images are
                # display assets, while emblem and acronym are fallback details.
                brandings={}
                for league,name,short,color,emblem,logo_data in db.execute(
                    """SELECT p.league,c.name,b.short,b.color,b.emblem,b.logo_data
                    FROM club_branding b JOIN careers c ON c.id=b.career_id
                    JOIN club_profiles p ON p.career_id=c.id"""):
                    brandings[league+'\n'+name]=dict(
                        short=short,color=color,emblem=emblem,logo_data=logo_data)
                for league,team,display_name,logo_data,short,color in db.execute(
                    """SELECT league,canonical_team,display_name,logo_data,short,color
                      FROM club_public_identity"""):
                    key=league+'\n'+team
                    current=brandings.setdefault(key,{})
                    if display_name:current['display_name']=display_name
                    if logo_data:current['logo_data']=logo_data
                    if short:current['short']=short
                    if color and color!='#17324d':current['color']=color
                import academy_clubs
                parent_logos={
                    item['league']+'\n'+item['team']:item['parent_league']+'\n'+item['parent_team']
                    for item in academy_clubs.entries() if item['parent_team'] and item['parent_league']
                }
                return self.reply(200,{'brandings':brandings,'academy_parents':parent_logos})
            if url.path=='/club-identity':
                query=parse_qs(url.query)
                league_name=query.get('league',[''])[0]
                team=query.get('team',[''])[0]
                if not club_history.exists(db,league_name,team):
                    return self.reply(404,{'error':'구단을 찾지 못했습니다.'})
                return self.reply(200,dict(league=league_name,team=team,
                    display_name=club_history.display(db,league_name,team),
                    branding=club_history.visual(db,league_name,team),
                    history=club_history.history(db,league_name,team),
                    can_manage_name=online_world.operator(db,uid),
                    can_manage_logo=online_world.operator(db,uid)))
            if url.path=='/sponsor-offers':
                cid=int(parse_qs(url.query)['id'][0])
                if not news.member(db,uid,cid):return self.reply(404,{'error':'not found'})
                return self.reply(200,sponsorship.proposals(db,cid))
            if url.path=='/rookie-offers':
                if not manager_identity.view(db,uid)['complete']:
                    return self.reply(409,{'error':'감독 프로필을 먼저 설정하세요.'})
                if online_world.operator(db,uid):
                    return self.reply(403,{'error':'운영자는 신인 감독 부임 대상이 아닙니다.'})
                if db.execute('SELECT 1 FROM members WHERE user_id=? LIMIT 1',(uid,)).fetchone():
                    return self.reply(200,{'offers':[],'already_managing':True})
                return self.reply(200,{'offers':rookie_offers.list_offers(db,uid),'already_managing':False})
            if url.path=='/clubs':
                directory=clubs.directory(db)
                for club in directory:
                    club['eligible']=career_rules.takeover_allowed(club['league'],club['team'])
                    club['ineligible_reason']=career_rules.takeover_reason(club['league'],club['team'])
                    club['power']=round(career_rules.club_power(club['league'],club['team']))
                return self.reply(200,{'clubs':directory,'leagues':career_rules.creation_leagues(db)})
            if url.path=='/world': return self.reply(200,online_world.status(db,uid))
            if url.path=='/departure-requests':
                cid=int(parse_qs(url.query)['id'][0])
                if not transfers.can_manage(db,uid,cid): return self.reply(403,{'error':'forbidden'})
                return self.reply(200,{'requests':player_departures.pending(db,cid)})
            if url.path=='/solo-ladder':
                query=parse_qs(url.query)
                try:
                    cid=int(query['id'][0])
                    if not 1<=cid<=2**63-1: raise ValueError()
                    if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                    return self.reply(200,solo.ladder(db,cid,query.get('role',[''])[0],
                        query.get('region',['KR'])[0],query.get('scope',['all'])[0]))
                except ValueError: return self.reply(400,{'error':'invalid request'})
            if url.path=='/league-overview':
                league_name=parse_qs(url.query).get('league',[''])[0]
                if not league_name or len(league_name)>80:
                    return self.reply(400,{'error':'invalid league'})
                clock=online_world.clock(db)
                season=clock['season']
                standings=dashboard.league_table(db,league_name,season)
                clubs_in_league=[c for c in clubs.directory(db) if c['league']==league_name]
                fixtures_rows=[dict(season=sn,week=wk,home=home,away=away,
                                    competition=competition,stage=stage,state=state,
                                    score=json.loads(raw).get('score') if raw else None)
                    for sn,wk,home,away,competition,stage,state,raw in db.execute(
                    """SELECT f.season,f.week,c.name,f.opponent,f.competition,f.stage,f.state,f.result
                       FROM fixtures f JOIN careers c ON c.id=f.career_id
                       WHERE f.season=? AND f.competition=? ORDER BY f.week,f.id LIMIT 160""",
                    (season,league_name))]
                changes=[dict(season=sn,old_team=old,new_team=new,headline=head)
                    for sn,old,new,head in db.execute(
                      """SELECT season,departing,arriving,headline FROM franchise_announcements
                         WHERE league=? ORDER BY season DESC LIMIT 12""",(league_name,))]
                return self.reply(200,dict(league=league_name,season=season,week=clock['week'],
                    standings=standings,clubs=clubs_in_league,fixtures=fixtures_rows,
                    franchise_news=changes))
            if url.path=='/dashboard':
                try:
                    cid=int(parse_qs(url.query)['id'][0])
                    if not 1<=cid<=2**63-1:raise ValueError()
                    if not news.member(db,uid,cid):return self.reply(404,{'error':'not found'})
                    db.execute('BEGIN IMMEDIATE');data=dashboard.snapshot(db,cid,uid);db.execute('COMMIT')
                    return self.reply(200,data)
                except (KeyError,ValueError):return self.reply(400,{'error':'invalid dashboard request'})
            if url.path=='/competitions':
                query=parse_qs(url.query);cid=int(query['id'][0])
                if not online_world.operator(db,uid) and not news.member(db,uid,cid):return self.reply(404,{'error':'career not found'})
                season=int(query.get('season',[online_world.clock(db)['season']])[0])
                profile=clubs.profile(db,cid)
                if cid==0 and online_world.operator(db,uid):profile['league']='LCK'
                leagues=sorted({p['league'] for p in catalog.load()['people'] if p.get('league')}|{r[0] for r in db.execute('SELECT league FROM club_profiles')})
                selected=query.get('league',[profile['league']])[0]
                if selected not in leagues:raise ValueError('unknown league')
                games=fixtures.list_for_member(db,uid,cid) or []
                return self.reply(200,dict(league=selected,leagues=leagues,season=season,
                    standings=dashboard.league_table(db,selected,season),
                    fixtures=[game for game in games if game['season']==season and game['competition']==selected],rules=competition_rules.list_rules(db,cid)))
            if url.path in ('/search','/entity'):
                query=parse_qs(url.query)
                try:
                    if url.path=='/search':return self.reply(200,search.suggest(db,query.get('query',[''])[0]))
                    entity_id=int(query['entity'][0])
                    if not 1<=entity_id<=2**63-1:raise ValueError()
                    return self.reply(200,search.entity(db,query['kind'][0],entity_id))
                except KeyError:return self.reply(404,{'error':'entity not found'})
                except ValueError:return self.reply(400,{'error':'invalid search query'})
            if url.path in ('/community','/community-post'):
                query=parse_qs(url.query)
                try:
                    if url.path=='/community':
                        return self.reply(200,community.board(db,query.get('league',['LCK'])[0],query.get('category',['all'])[0],int(query.get('page',['0'])[0]),query.get('query',[''])[0]))
                    return self.reply(200,{'post':community.get(db,uid,int(query['post'][0])),'user_id':0,'operator':False,'read_only':True})
                except KeyError:return self.reply(404,{'error':'post not found'})
                except ValueError:return self.reply(400,{'error':'invalid community request'})
            if url.path in ('/transfer-offers','/transfer-activity'):
                query=parse_qs(url.query)
                try:
                    cid=int(query['id'][0])
                    if not 1<=cid<=2**63-1: raise ValueError()
                    if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                    if url.path=='/transfer-activity': return self.reply(200,{'events':transfers.activity(db,query.get('kind',[''])[0])})
                    return self.reply(200,{'offers':transfers.offers(db,cid)})
                except (KeyError,ValueError): return self.reply(400,{'error':'invalid transfer request'})
            if url.path=='/analytics':
                query=parse_qs(url.query)
                try:
                    cid=int(query['id'][0]); season=int(query['season'][0])
                    if not 1<=cid<=2**63-1: raise ValueError()
                    if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                    return self.reply(200,analytics.hub(db,cid,season))
                except (KeyError,ValueError):return self.reply(400,{'error':'invalid analytics request'})
            if url.path=='/management':
                try:
                    cid=int(parse_qs(url.query)['id'][0])
                    if not 1<=cid<=2**63-1: raise ValueError()
                    if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                    db.execute('BEGIN IMMEDIATE');management.ensure(db,cid);db.execute('COMMIT')
                    return self.reply(200,management.snapshot(db,cid))
                except (ValueError,KeyError): return self.reply(400,{'error':'invalid management request'})
            if url.path=='/recruitment':
                try:
                    cid=int(parse_qs(url.query)['id'][0])
                    if not 1<=cid<=2**63-1: raise ValueError()
                    if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                    return self.reply(200,recruitment.view(db,cid))
                except (KeyError,ValueError): return self.reply(400,{'error':'invalid career'})
            if url.path in ('/inbox','/shortlist'):
                query=parse_qs(url.query)
                try:
                    cid=int(query['id'][0])
                    if not 1<=cid<=2**63-1: raise ValueError()
                    if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                    if url.path=='/shortlist': return self.reply(200,{'people':club_messages.shortlist(db,cid,uid)})
                    before=int(query['before'][0]) if 'before' in query else None
                    return self.reply(200,{'messages':club_messages.inbox(db,cid,uid,before)})
                except KeyError: return self.reply(404,{'error':'not found'})
                except ValueError: return self.reply(400,{'error':'invalid request'})
            if url.path=='/player-comparisons':
                query=parse_qs(url.query)
                cid=int(query['id'][0])
                if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                person=catalog.detail(db,cid,query['person'][0])
                return self.reply(200,{'comparisons':scouting.compare(db,cid,person)})
            if url.path in ('/people','/person','/teams'):
                query=parse_qs(url.query)
                try:
                    cid=int(query['id'][0])
                    if not (cid==0 and online_world.operator(db,uid)):
                        if not 1<=cid<=2**63-1: raise ValueError()
                        if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                    if url.path=='/teams': return self.reply(200,{'teams':catalog.teams()})
                    if url.path=='/person':
                        person=catalog.detail(db,cid,query['person'][0])
                        report=scouting.report(db,cid,person)
                        return self.reply(200,{'person':person,'scouting':report})
                    return self.reply(200,catalog.search(db,cid,int(query.get('page',['0'])[0]),
                        *[query.get(key,[''])[0] for key in ('query','team','kind','league')],origin=query.get('origin',['all'])[0]))
                except FileNotFoundError:
                    return self.reply(503,{'error':'people catalog unavailable'})
                except KeyError:
                    return self.reply(404,{'error':'not found'})
                except ValueError:
                    return self.reply(400,{'error':'invalid people request'})
            if url.path == '/highlight':
                query = parse_qs(url.query)
                try:
                    fixture = int(query['id'][0])
                    index = int(query['clip'][0])
                    if not 1 <= fixture <= 2**63-1 or index < 0:
                        raise ValueError()
                except (KeyError, ValueError):
                    return self.reply(400, {'error':'invalid highlight'})
                row = db.execute("""SELECT f.result,s.state FROM fixtures f
                    LEFT JOIN match_series s ON s.fixture_id=f.id
                    JOIN members m ON m.career_id=f.career_id
                    WHERE f.id=? AND m.user_id=? AND f.state IN ('queued','finished')""",(fixture,uid)).fetchone()
                if not row:
                    return self.reply(404, {'error':'not found'})
                if row[0]:
                    count = len(json.loads(row[0]).get('highlights',[]))
                elif row[1]:
                    count = sum(len(game.get('highlights',[])) for game in json.loads(row[1])['sets'])
                else:
                    count = 0
                if index >= count:
                    return self.reply(404, {'error':'not found'})
                path = clip_path(DB.parent / 'highlights',fixture,index)
                try:
                    replay = path.open('rb')
                except FileNotFoundError:
                    return self.reply(404, {'error':'not found'})
                with replay:
                    self.send_response(200)
                    self.send_header('Content-Type','application/json; charset=utf-8')
                    self.send_header('Content-Encoding','gzip')
                    self.send_header('Content-Length',str(os.fstat(replay.fileno()).st_size))
                    self.send_header('Cache-Control','no-store')
                    self.end_headers()
                    import shutil
                    shutil.copyfileobj(replay,self.wfile)
                return
            if url.path=='/competition-rules':
                try:
                    cid=int(parse_qs(url.query)['id'][0])
                    if not 1<=cid<=2**63-1: raise ValueError()
                except (KeyError,ValueError):
                    return self.reply(400,{'error':'invalid career'})
                if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                return self.reply(200,{'rules':competition_rules.list_rules(db,cid)})
            if url.path in ('/news','/follows'):
                query=parse_qs(url.query)
                try:
                    cid=int(query['id'][0])
                    if not 1<=cid<=2**63-1: raise ValueError()
                    if url.path=='/follows':
                        return self.reply(200,{'follows':news.preferences(db,uid,cid)})
                    before=int(query['before'][0]) if 'before' in query else None
                    return self.reply(200,{'news':news.feed(db,uid,cid,query.get('competition',[''])[0],
                        query.get('scope',['home'])[0],before)})
                except PermissionError:
                    return self.reply(404,{'error':'not found'})
                except (KeyError,ValueError):
                    return self.reply(400,{'error':'invalid news request'})
            if url.path == '/league':
                query = parse_qs(url.query)
                try:
                    cid,season = (int(query[key][0]) for key in ('id','season'))
                    if not 1 <= cid <= 2**63-1 or not 1 <= season <= 2**63-1:
                        raise ValueError()
                except (KeyError,ValueError):
                    return self.reply(400,{'error':'invalid league'})
                if not db.execute('SELECT 1 FROM members WHERE career_id=? AND user_id=?',(cid,uid)).fetchone():
                    return self.reply(404,{'error':'not found'})
                return self.reply(200,{'standings':league.standings(db,cid,season)})
            if url.path == '/fixtures':
                try:
                    cid = int(parse_qs(url.query)['id'][0])
                except (KeyError, ValueError):
                    return self.reply(400,{'error':'invalid career'})
                games = fixtures.list_for_member(db,uid,cid)
                return self.reply(200,{'fixtures':games}) if games is not None else self.reply(404,{'error':'not found'})
            if self.path=='/careers':
                if online_world.operator(db,uid):return self.reply(200,{'careers':[]})
                rows=db.execute('SELECT c.id,c.name,c.week,c.season,c.version,m.role FROM careers c JOIN members m ON m.career_id=c.id WHERE m.user_id=?',(uid,)).fetchall()
                if not online_world.operator(db,uid): rows=sorted(rows,key=lambda r:r[0])[:1]
                careers = []
                for row in rows:
                    item = dict(zip(('id','name','week','season','version','role'),row))
                    item['settings'] = dict(db.execute('SELECT key,value FROM settings WHERE career_id=?',(item['id'],)))
                    item['club_profile']=clubs.profile(db,item['id'])
                    item['branding']=career_rules.brand(db,item['id'])
                    item['league_operator']=online_world.operator(db,uid)
                    item['world']=online_world.status(db,uid)
                    manager=db.execute('SELECT name FROM manager_profiles WHERE career_id=?',(item['id'],)).fetchone()
                    if manager:item['manager']=manager[0]
                    careers.append(item)
                return self.reply(200,{'careers':careers})
            if url.path in ('/plan','/training','/preferences','/club-dossier','/champions'):
                query=parse_qs(url.query)
                if url.path=='/champions':
                    import training
                    kits=training._rules()
                    return self.reply(200,{'champions':[{'name':name,'roles':list(kit.roles)} for name,kit in sorted(kits.items())]})
                if url.path=='/preferences':
                    row=db.execute('SELECT dashboard FROM user_preferences WHERE user_id=?',(uid,)).fetchone()
                    return self.reply(200,{'dashboard':json.loads(row[0]) if row else ['news','standings','budget']})
                if url.path=='/club-dossier':
                    import dossier
                    league_name=query.get('league',[''])[0]
                    team=query.get('team',[''])[0]
                    result=dossier.view(db,uid,league_name,team)
                    result['display_name']=club_history.display(db,league_name,team)
                    result['history']=club_history.history(db,league_name,team)
                    return self.reply(200,result)
                try: cid=int(query['id'][0])
                except (KeyError,ValueError): return self.reply(400,{'error':'invalid request'})
                if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                if url.path=='/plan':
                    import tactics
                    return self.reply(200,{'plan':tactics.load(db,cid),'catalog':tactics.catalog()})
                import training
                return self.reply(200,{'players':training.roster(db,cid,recruitment.view(db,cid)['people'])})
            return self.reply(404,{'error':'endpoint not found'})
    def roots(self):
        here=Path(__file__).resolve().parent
        assets=here/'assets' if (here/'assets').exists() else here.parent/'assets'
        web=here/'web' if (here/'web').exists() else here.parent/'web'
        return assets,web
    def send_file(self,path,cache=True):
        kind={'.png':'image/png','.jpg':'image/jpeg','.jpeg':'image/jpeg','.webp':'image/webp','.svg':'image/svg+xml',
              '.json':'application/json; charset=utf-8','.css':'text/css; charset=utf-8','.js':'text/javascript; charset=utf-8',
              '.html':'text/html; charset=utf-8','.woff2':'font/woff2','.ttf':'font/ttf'}.get(path.suffix.lower(),'application/octet-stream')
        data=path.read_bytes()
        self.send_response(200)
        self.send_header('Content-Type',kind)
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','public, max-age=86400' if cache else 'no-store')
        self.end_headers()
        self.wfile.write(data)
    def public(self):
        path=urlsplit(self.path).path
        assets,web=self.roots()
        if path.startswith('/media/'):
            rel=path[len('/media/'):]
            if '..' in rel.split('/') or not (rel.startswith(('portraits/','clubs/')) or rel in ('club-assets.json','club-colors.json','league-logos.json')):
                self.reply(404,{'error':'not found'}); return True
            target=assets/rel
            if not target.is_file():
                self.reply(404,{'error':'not found'}); return True
            self.send_file(target); return True
        if path.startswith('/static/'):
            rel=path[len('/static/'):]
            target=web/rel
            if '..' in rel.split('/') or not target.is_file() or web.resolve() not in target.resolve().parents:
                self.reply(404,{'error':'not found'}); return True
            self.send_file(target,cache=False); return True
        if path=='/' or path.startswith('/app'):
            page=web/'index.html'
            if page.is_file():
                self.send_file(page,cache=False); return True
        return False
    def do_POST(self):
        self.normalize_path()
        try: self.post()
        except ValueError as error:
            public={'at most three coaches','select exactly one player per role',
                    'five players, one per role, and at most three coaches required',
                    'initial recruitment already finalized','competition stage format has not been configured',
                    'account name must be 1 to 30 characters','password must be 10 to 128 characters','invalid request',
                    'amateurs and prospects cannot be signed','already a pro player','player has retired',
                    'another club is developing this player','already your prospect','this player is in another club tryout',
                    'prospect list is full','talk again later','not your prospect','not ready for pro debut',
                    'debut the prospect before the pro roster','operators choose a team',
                    '닉네임과 이름을 각각 1~30자로 입력하세요.','감독 닉네임은 영문 2~20자만 사용할 수 있습니다.','이미 사용 중인 감독 닉네임입니다.','감독 능력치는 각각 1~20, 합계 60으로 설정하세요.','감독 국적을 목록에서 선택해 주세요.','invalid shotcallers','오더 담당은 현재 1군 주전 선수 중에서 선택하세요.'}
            message=str(error)
            self.reply(400,{'error':message if message in public else 'invalid request'})
        except (TypeError,KeyError): self.reply(400,{'error':'invalid request'})
        except sqlite3.IntegrityError:
            self.reply(409,{'error':'account name already exists' if urlsplit(self.path).path=='/register' else 'conflict'})
        except Exception:
            import traceback
            traceback.print_exc();self.reply(500,{'error':'server processing error'})
    def post(self):
        data=self.input()
        with closing(connect()) as db:
            if self.path in ('/register','/login'):
                name=data.get('name',''); password=data.get('password','')
                if not isinstance(name,str) or not isinstance(password,str): raise ValueError('invalid request')
                name=name.strip()
                if not 1<=len(name)<=30 or any(ord(c)<32 or ord(c)==127 for c in name):
                    raise ValueError('account name must be 1 to 30 characters')
                if not 10<=len(password)<=128 or any(ord(c)<32 or ord(c)==127 for c in password):
                    raise ValueError('password must be 10 to 128 characters')
                if self.path=='/register':
                    if db.execute('SELECT 1 FROM users WHERE name=? COLLATE NOCASE',(name,)).fetchone():
                        return self.reply(409,{'error':'account name already exists'})
                    salt=secrets.token_bytes(16); digest=derive(password,salt)
                    db.execute('INSERT INTO users(name,salt,password) VALUES(?,?,?)',(name,salt,digest))
                    # New accounts always begin as managers, never automatic operators.
                    user_id=db.execute('SELECT id FROM users WHERE name=?',(name,)).fetchone()[0]
                else:
                    row=db.execute('SELECT id,salt,password FROM users WHERE name=?',(name,)).fetchone()
                    if not row or not hmac.compare_digest(derive(password,row[1]),row[2]): return self.reply(401,{'error':'invalid credentials'})
                    user_id=row[0]
                token=secrets.token_urlsafe(32); db.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),user_id,int(time.time())+86400*7))
                return self.reply(200,{'token':token})
            uid=self.user(db)
            if not uid: return self.reply(401,{'error':'unauthorized'})
            if online_world.operator(db,uid) and self.path not in ('/competition-rules','/person-evaluation','/fixtures','/league','/preferences','/operator/club-identity'):
                return self.reply(403,{'error':'운영자는 구단을 운영하거나 선수단·전술을 변경할 수 없습니다.'})
            if self.path=='/operator/club-identity':
                if not online_world.operator(db,uid):
                    return self.reply(403,{'error':'구단 이름 수정은 운영자만 가능합니다.'})
                league_name=data.get('league','')
                team=data.get('team','')
                if not isinstance(league_name,str) or not isinstance(team,str) or len(league_name)>80 or len(team)>80:
                    return self.reply(400,{'error':'invalid club'})
                clock=online_world.clock(db)
                db.execute('BEGIN IMMEDIATE')
                result={}
                if 'name' in data:
                    result=club_history.rename(db,league_name,team,data['name'],
                                                clock['season'],clock['week'])
                if 'logo_data' in data:
                    club_history.update_logo(db,league_name,team,data['logo_data'],
                                             clock['season'],clock['week'],'operator')
                db.execute('COMMIT')
                return self.reply(200,dict(result,updated=True))
            if self.path=='/club-logo':
                # Once an account selects or founds a club, its identity is
                # locked. Only the operator's audited editor may change it.
                return self.reply(403,{'error':'구단 선택·창단 후 이름과 로고는 변경할 수 없습니다. 운영자에게 문의하세요.'})
            if self.path=='/sponsor-accept':
                cid=data.get('id')
                if type(cid)!=int or not transfers.can_manage(db,uid,cid):
                    return self.reply(403,{'error':'forbidden'})
                if type(data.get('offer'))!=int:
                    return self.reply(400,{'error':'invalid sponsor offer'})
                db.execute('BEGIN IMMEDIATE')
                result=sponsorship.accept(db,cid,data['offer'])
                db.execute('COMMIT')
                return self.reply(200,result)
            if self.path=='/manager-profile':
                db.execute('BEGIN IMMEDIATE')
                result=manager_identity.save(db,uid,data)
                db.execute('COMMIT');return self.reply(200,result)
            if self.path.startswith('/community-'):
                return self.reply(403,{'error':'AI fans create community content from game events'})
            if self.path=='/careers':
                if not manager_identity.view(db,uid)['complete']:
                    return self.reply(409,{'error':'먼저 감독 닉네임, 이름과 능력치를 설정하세요.'})
                mode=data.get('mode','create')
                if online_world.operator(db,uid):
                    if mode!='enter': raise ValueError('operators choose a team')
                    team_key=data.get('team_key')
                    if not isinstance(team_key,str): raise ValueError('unknown real club')
                    if team_key.startswith('career:'):
                        try: cid=int(team_key.split(':',1)[1])
                        except ValueError: raise ValueError('unknown real club')
                        if not 1<=cid<=2**63-1 or not db.execute('SELECT 1 FROM careers WHERE id=?',(cid,)).fetchone():
                            raise ValueError('unknown real club')
                        db.execute('BEGIN IMMEDIATE')
                        role=clubs.grant(db,uid,cid)
                        db.execute('COMMIT'); return self.reply(200,{'id':cid,'role':role})
                    selected=next((club for club in clubs.available(db) if club['team_key']==team_key),None)
                    if not selected: raise ValueError('unknown real club')
                    existing=db.execute('SELECT career_id FROM club_profiles WHERE team_key=?',(team_key,)).fetchone()
                    if existing:
                        db.execute('BEGIN IMMEDIATE')
                        role=clubs.grant(db,uid,existing[0])
                        db.execute('COMMIT'); return self.reply(200,{'id':existing[0],'role':role})
                    mode,name='takeover',selected['team']
                else:
                    if db.execute('SELECT 1 FROM members WHERE user_id=?',(uid,)).fetchone():
                        return self.reply(403,{'error':'구단 전환은 운영자만 사용할 수 있습니다.'})
                    selected=None
                    if mode=='takeover':
                        selected=next((club for club in clubs.available(db) if club['team_key']==data.get('team_key')),None)
                        if not selected: raise ValueError('unknown real club')
                        if not career_rules.takeover_allowed(selected['league'],selected['team']):
                            return self.reply(403,{'error':career_rules.takeover_reason(selected['league'],selected['team'])})
                        if not rookie_offers.invited(db,uid,selected['team_key']):
                            return self.reply(403,{'error':'해당 구단의 신인 감독 부임 제안을 받지 않았습니다.'})
                        name=selected['team']
                    elif mode=='create': name=data.get('name','')
                    else: raise ValueError('invalid club mode')
                if not isinstance(name,str) or not 1<=len(name.strip())<=40: raise ValueError()
                if mode=='create' and any(club['team'].casefold()==name.strip().casefold() for club in clubs.available(db)):
                    raise ValueError('choose real club takeover')
                db.execute('BEGIN IMMEDIATE')
                if not online_world.operator(db,uid) and db.execute('SELECT 1 FROM members WHERE user_id=?',(uid,)).fetchone():
                    db.execute('ROLLBACK');return self.reply(403,{'error':'이미 맡은 구단이 있습니다.'})
                if mode=='takeover':
                    existing=db.execute('SELECT career_id FROM club_profiles WHERE team_key=?',(data.get('team_key'),)).fetchone()
                    if existing:
                        if clubs.human_owner(db,existing[0]):
                            db.execute('ROLLBACK');return self.reply(409,{'error':'이미 다른 감독이 맡고 있는 구단입니다.'})
                        role=clubs.grant(db,uid,existing[0]);identity=manager_identity.view(db,uid)
                        management.ensure(db,existing[0])
                        db.execute('UPDATE manager_profiles SET name=?,stats=? WHERE career_id=?',(identity['name'],json.dumps(identity['stats'],ensure_ascii=False),existing[0]))
                        if not online_world.operator(db,uid):rookie_offers.accept(db,uid,selected['team_key'])
                        db.execute('COMMIT');return self.reply(201,{'id':existing[0],'role':role})
                world=online_world.clock(db)
                cur=db.execute('INSERT INTO careers(name,season,week,version) VALUES(?,?,?,?)',(name.strip(),world['season'],world['week'],world['version'])); cid=cur.lastrowid
                if db.execute('SELECT 1 FROM careers WHERE lower(name)=lower(?) AND id!=?',(name.strip(),cid)).fetchone():
                    return self.reply(409,{'error':'club name already exists'})
                requested_league=data.get('league','LCK CL')
                if mode=='create' and requested_league not in career_rules.creation_leagues(db):
                    db.execute('ROLLBACK');return self.reply(400,{'error':'등록된 리그를 선택하세요.'})
                if mode=='create':
                    short=data.get('short','')
                    color=data.get('color','#254A7A')
                    emblem=data.get('emblem','shield')
                    career_rules.valid_brand(name,short,color)
                    career_rules.store_brand(db,cid,short,color,emblem,data.get('logo_data',''))
                clubs.create(db,cid,mode,data.get('team_key'),requested_league)
                if mode=='create':
                    club_history.record(db,requested_league,name.strip(),world['season'],world['week'],
                        'club-founded','구단 창단… '+name.strip()+' 출범',
                        '구단명·약자·대표 로고를 창단 시 확정했습니다. 이후 운영자만 수정할 수 있습니다.',
                        'game-user-action')
                db.execute('INSERT INTO members VALUES(?,?,?)',(cid,uid,'admin'))
                manager=manager_identity.view(db,uid)['name']
                news.appointment(db,cid,manager,name.strip(),selected['league'] if selected else requested_league,'KR',0,80 if selected else 0)
                club_messages.publish(db,cid,'welcome',world['season'],world['week'],'감독 부임 안내',manager+' 감독님, '+name.strip()+' 온라인 구단 운영이 시작됐습니다.')
                if mode=='create': recruitment.generate(db,cid,name.strip())
                management.ensure(db,cid)
                identity=manager_identity.view(db,uid)
                db.execute('UPDATE manager_profiles SET name=?,stats=? WHERE career_id=?',(identity['name'],json.dumps(identity['stats'],ensure_ascii=False),cid))
                community.appointment(db,cid,manager)
                try:
                    career_rules.seed_league(db,cid,selected['league'] if selected else requested_league,world['season'],world['week'])
                except (ValueError,sqlite3.IntegrityError):
                    # An occupied schedule is not fatal to club creation; other leagues remain available.
                    pass
                if mode=='takeover' and not online_world.operator(db,uid):rookie_offers.accept(db,uid,selected['team_key'])
                db.execute('COMMIT'); return self.reply(201,{'id':cid,'role':'admin'})
            if self.path in ('/transfer-offer','/transfer-response'):
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                if not transfers.can_manage(db,uid,cid): return self.reply(403,{'error':'forbidden'})
                db.execute('BEGIN IMMEDIATE')
                if self.path=='/transfer-offer':
                    offer=transfers.quote(db,cid,data['person'],data['annual_salary'],data['fee'],data['years'],data['pitch'])
                else:
                    offer=data['offer']
                    try: transfers.respond(db,uid,cid,offer,data['choice'],data.get('counter_fee'))
                    except PermissionError: return self.reply(403,{'error':'forbidden'})
                db.execute('COMMIT')
                return self.reply(200,{'id':offer,'offers':transfers.offers(db,cid)})
            if self.path=='/departure-decision':
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                if not transfers.can_manage(db,uid,cid): return self.reply(403,{'error':'forbidden'})
                db.execute('BEGIN IMMEDIATE')
                decision=player_departures.resolve(db,cid,data['person'],data['approve'])
                db.execute('COMMIT')
                return self.reply(200,decision)
            if self.path=='/management':
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                if not transfers.can_manage(db,uid,cid):
                    return self.reply(403,{'error':'forbidden'})
                db.execute('BEGIN IMMEDIATE');result=management.action(db,cid,data);db.execute('COMMIT')
                return self.reply(200,result)
            if self.path=='/staff-role':
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1:raise ValueError()
                if not transfers.can_manage(db,uid,cid):return self.reply(403,{'error':'forbidden'})
                db.execute('BEGIN IMMEDIATE');staffing.assign(db,cid,data['person'],data['staff_role']);db.execute('COMMIT')
                return self.reply(200,recruitment.view(db,cid))
            if self.path=='/staff-candidates':
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1:raise ValueError()
                if not transfers.can_manage(db,uid,cid):return self.reply(403,{'error':'forbidden'})
                db.execute('BEGIN IMMEDIATE');staffing.generate_candidates(db,cid);db.execute('COMMIT')
                return self.reply(200,{'saved':True})
            if self.path=='/club-lineup':
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                if not transfers.can_manage(db,uid,cid):
                    return self.reply(403,{'error':'forbidden'})
                db.execute('BEGIN IMMEDIATE')
                busy=db.execute("SELECT s.state FROM fixtures f JOIN match_series s ON s.fixture_id=f.id WHERE f.career_id=? AND f.state='queued'",(cid,)).fetchall()
                if any(json.loads(row[0])['phase']=='ready' for row in busy):
                    return self.reply(409,{'error':'finish the current series before changing lineup'})
                clubs.assign(db,cid,data['person'],data['assignment'],data['role'])
                db.execute('COMMIT')
                return self.reply(200,recruitment.view(db,cid))
            if self.path in ('/recruitment-select','/recruitment-finalize','/recruitment-start'):
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                if not transfers.can_manage(db,uid,cid):
                    return self.reply(403,{'error':'forbidden'})
                db.execute('BEGIN IMMEDIATE')
                if self.path=='/recruitment-start':
                    if clubs.profile(db,cid)['mode']=='takeover': raise ValueError('real clubs use their registered roster')
                    club=db.execute('SELECT name FROM careers WHERE id=?',(cid,)).fetchone()[0]
                    recruitment.generate(db,cid,club)
                elif self.path=='/recruitment-select':
                    if clubs.profile(db,cid)['mode']=='takeover': raise ValueError('real clubs use their registered roster')
                    recruitment.select(db,cid,data['person'],data['enabled'])
                else:
                    recruitment.finalize(db,cid)
                    management.ensure(db,cid)
                db.execute('COMMIT')
                return self.reply(200,recruitment.view(db,cid))
            if self.path in ('/solo-talk','/solo-debut'):
                cid=data['id']; person=data['person']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                if not transfers.can_manage(db,uid,cid): return self.reply(403,{'error':'forbidden'})
                db.execute('BEGIN IMMEDIATE')
                result=solo.talk(db,cid,person) if self.path=='/solo-talk' else solo.debut(db,cid,person)
                db.execute('COMMIT')
                return self.reply(200,result)
            if self.path in ('/shortlist','/read-mail'):
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                if not news.member(db,uid,cid): return self.reply(404,{'error':'not found'})
                db.execute('BEGIN IMMEDIATE')
                if self.path=='/shortlist':
                    if not transfers.can_manage(db,uid,cid): return self.reply(403,{'error':'forbidden'})
                    club_messages.set_shortlist(db,cid,uid,data['person'],data['enabled'])
                else: club_messages.mark_read(db,cid,uid,data['mail'])
                db.execute('COMMIT')
                return self.reply(200,{'saved':True})
            if self.path=='/person-evaluation':
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                if not online_world.operator(db,uid):
                    return self.reply(403,{'error':'forbidden'})
                value=catalog.evaluate(db,cid,data['person'],data['ratings'],data['form'],data['note'])
                return self.reply(200,{'evaluation':value})
            if self.path=='/competition-rules':
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                if not online_world.operator(db,uid):
                    return self.reply(403,{'error':'forbidden'})
                competition_rules.configure(db,cid,data['competition'],data['stage'],data['best_of'])
                return self.reply(200,{'rules':competition_rules.list_rules(db,cid)})
            if self.path=='/follows':
                cid=data['id']
                if type(cid) is not int or not 1<=cid<=2**63-1: raise ValueError()
                try:
                    news.follow(db,uid,cid,data['kind'],data['entity'],data['enabled'])
                except PermissionError:
                    return self.reply(404,{'error':'not found'})
                return self.reply(200,{'follows':news.preferences(db,uid,cid)})
            if self.path=='/league':
                cid, season, week = (data[key] for key in ('id','season','week'))
                if any(type(value) is not int or not 1 <= value <= 2**63-1 for value in (cid,season,week)):
                    raise ValueError()
                db.execute('BEGIN IMMEDIATE')
                if not online_world.operator(db,uid):
                    return self.reply(403,{'error':'forbidden'})
                length = league.create(db,cid,season,week,data['opponents'])
                db.execute('COMMIT')
                return self.reply(201,{'rounds':length})
            if self.path=='/fixtures':
                cid, season, week, opponent = (data[key] for key in ('id','season','week','opponent'))
                if any(type(value) is not int for value in (cid,season,week)) or not isinstance(opponent,str):
                    raise ValueError()
                if not online_world.operator(db,uid):
                    return self.reply(403,{'error':'forbidden'})
                competition,stage=data.get('competition','practice'),data.get('stage','practice')
                best_of=competition_rules.resolve(db,cid,competition,stage)
                fixture = fixtures.add(db,cid,season,week,opponent,best_of,competition,stage)
                return self.reply(201,{'id':fixture})
            if self.path in ('/draft-choice','/set-feedback','/draft-swap','/draft-action','/draft-auto'):
                fixture = data['id']
                if type(fixture) is not int or not 1 <= fixture <= 2**63-1:
                    raise ValueError()
                db.execute('BEGIN IMMEDIATE')
                row = db.execute("""SELECT f.seed,s.state FROM fixtures f JOIN match_series s ON s.fixture_id=f.id
                    JOIN members m ON m.career_id=f.career_id
                    WHERE f.id=? AND f.state='queued' AND m.user_id=? AND m.role='admin'""",
                    (fixture,uid)).fetchone()
                if not row:
                    return self.reply(404,{'error':'not found'})
                seed, raw = row
                state = json.loads(raw)
                if self.path in ('/draft-action','/draft-auto'):
                    if state['phase']!='draft':return self.reply(409,{'error':'draft is not active'})
                    if type(data.get('version')) is not int or data['version']!=state.get('draft_version'):
                        return self.reply(409,{'error':'stale draft version'})
                    if time.time()>=state['response_until']:
                        series_state.tick(state,seed,time.time());series_state.put(db,fixture,state);db.execute('COMMIT')
                        return self.reply(409,{'error':'response period expired; automatic draft is running'})
                    kits,roles=manual_draft.engine_rules()
                    if self.path=='/draft-auto':manual_draft.bot(state,seed,kits,roles,time.time(),all_teams=True)
                    else:
                        if manual_draft.order(state['first'])[len(state['draft'])][1]!=0:
                            return self.reply(409,{'error':'wait for opponent turn'})
                        if not isinstance(data.get('champion'),str):raise ValueError()
                        try:manual_draft.submit(state,data['champion'],kits,roles,time.time(),data['version'])
                        except ValueError as error:return self.reply(409,{'error':str(error)})
                elif self.path=='/draft-swap':
                    try:series_state.swap(state,data['first'],data['second'],data['version'],time.time())
                    except ValueError as error:return self.reply(409,{'error':str(error)})
                elif self.path == '/draft-choice':
                    game=db.execute('SELECT career_id,season,week FROM fixtures WHERE id=?',(fixture,)).fetchone()
                    if management.readiness(db,game[0],(game[1]-1)*104+game[2]):
                        return self.reply(409,{'error':'select healthy contracted players before draft'})
                    if state['phase']=='feedback' and time.time()>=state['feedback_until']:
                        series_state.next_choice(state,seed)
                    category,value = data['category'],data['value']
                    if not isinstance(category,str) or not isinstance(value,str):
                        raise ValueError()
                    if not series_state.submit_choice(state,seed,category,value):
                        return self.reply(409,{'error':'choice unavailable'})
                    state['manual_draft']=bool(data.get('manual',False))
                else:
                    note = data['note']
                    if not isinstance(note,str) or not 1 <= len(note.strip()) <= 300:
                        raise ValueError()
                    if state['phase'] != 'feedback' or time.time() >= state['feedback_until']:
                        return self.reply(409,{'error':'feedback closed'})
                    number = len(state['sets'])
                    state['feedback'] = [item for item in state['feedback'] if item['set'] != number]
                    state['feedback'].append({'set':number,'note':note.strip()})
                series_state.put(db,fixture,state)
                db.execute('COMMIT')
                return self.reply(200,{'series':state})
            if self.path=='/settings':
                cid, key, value = data['id'], data['key'], data['value']
                options = {'tactics': {'균형','오브젝트 중심','한타 중심','사이드 압박'},
                           'training': {'기본기','라인 관리','시야와 합류','휴식'}}
                if type(cid) is not int or not isinstance(key,str) or not isinstance(value,str) or value not in options.get(key,()):
                    raise ValueError()
                result = db.execute('''INSERT INTO settings(career_id,key,value)
                    SELECT career_id,?,? FROM members WHERE career_id=? AND user_id=? AND role='admin'
                    ON CONFLICT(career_id,key) DO UPDATE SET value=excluded.value''',(key,value,cid,uid))
                return self.reply(200,{'value':value}) if result.rowcount else self.reply(403,{'error':'forbidden'})
            if self.path=='/advance':
                cid=data['id']; version=data['version']
                if type(cid)!=int or type(version)!=int: raise ValueError()
                db.execute('BEGIN IMMEDIATE')
                row=db.execute('SELECT c.week,c.season,c.version,m.role FROM careers c JOIN members m ON c.id=m.career_id WHERE c.id=? AND m.user_id=?',(cid,uid)).fetchone()
                if not row: db.execute('ROLLBACK'); return self.reply(404,{'error':'not found'})
                week,season,current,role=row
                world=online_world.clock(db)
                if (season,week,current)!=(world['season'],world['week'],world['version']):
                    return self.reply(409,{'error':'online clock migration required'})
                if current!=version: db.execute('ROLLBACK'); return self.reply(409,{'error':'stale version'})
                setup=db.execute('SELECT complete FROM recruitment_state WHERE career_id=?',(cid,)).fetchone()
                if setup and not setup[0]:
                    db.execute('ROLLBACK')
                    return self.reply(409,{'error':'finalize the five-player lineup before advancing'})
                if setup:
                    lineup=recruitment.view(db,cid)['roster']
                    if len(lineup)!=5 or {p['role'] for p in lineup}!=set(recruitment.ROLES):
                        return self.reply(409,{'error':'finalize the five-player lineup before advancing'})
                pending = db.execute(
                    "SELECT 1 FROM fixtures WHERE state='queued'").fetchone()
                if pending:
                    db.execute('ROLLBACK')
                    return self.reply(409,{'error':'finish the current series before advancing'})

                readiness=online_world.vote(db,uid)
                votes,members=readiness['ready_count'],readiness['member_count']
                advanced=online_world.operator(db,uid) or votes>members//2
                if advanced:
                    if week==104:
                        # The outgoing season's results are reviewed privately.
                        promotion.year_end(db,season)
                        sponsorship.year_end(db,season)
                        week=1
                        season+=1
                        promotion.apply_new_season(db,season)
                    else:week+=1
                    current+=1
                    for (club_id,) in db.execute('SELECT id FROM careers').fetchall():
                        management.advance(db,club_id,season,week)
                        fixtures.enqueue(db,club_id,season,week)
                        league.simulate_ai(db,club_id,season,week)
                        club_messages.publish(db,club_id,'week:'+str(current),season,week,'온라인 리그 주차 진행',str(season)+'시즌 '+str(week)+'주차로 함께 진행했습니다.')
                    db.execute('UPDATE careers SET week=?,season=?,version=?',(week,season,current))
                    db.execute('UPDATE online_clock SET season=?,week=?,version=? WHERE id=1',(season,week,current))
                    solo.weekly(db,season,week)
                    import rumors
                    rumors.weekly(db,season,week)
                db.execute('COMMIT'); return self.reply(200,{'advanced':advanced,'week':week,'season':season,'version':current,'votes':votes,'members':members})
            if self.path=='/plan':
                cid=data.get('id')
                if type(cid) is not int or not transfers.can_manage(db,uid,cid): return self.reply(403,{'error':'forbidden'})
                import tactics
                return self.reply(200,{'plan':tactics.save(db,cid,data.get('plan'))})
            if self.path=='/training':
                cid=data.get('id')
                if type(cid) is not int or not transfers.can_manage(db,uid,cid): return self.reply(403,{'error':'forbidden'})
                import training
                people=recruitment.view(db,cid)['people']
                if data.get('person') in ('*','all'):
                    for person in people:
                        if person.get('role') in recruitment.ROLES and person.get('kind') not in ('coach','staff'):
                            training.set_focus(db,cid,catalog.detail(db,cid,person['id']),'auto')
                else:
                    training.set_focus(db,cid,catalog.detail(db,cid,data.get('person')),data.get('focus'))
                return self.reply(200,{'players':training.roster(db,cid,recruitment.view(db,cid)['people'])})
            if self.path=='/preferences':
                slots=data.get('dashboard')
                allowed={'news','inbox','standings','next','squad','budget','wages','schedule','staff','medical','board','form'}
                if not isinstance(slots,list) or len(slots)!=3 or any(item not in allowed for item in slots) or len(set(slots))!=3:
                    raise ValueError('invalid dashboard')
                db.execute('''INSERT INTO user_preferences(user_id,dashboard) VALUES(?,?)
                    ON CONFLICT(user_id) DO UPDATE SET dashboard=excluded.dashboard''',(uid,json.dumps(slots,ensure_ascii=False)))
                return self.reply(200,{'dashboard':slots})
            return self.reply(404,{'error':'endpoint not found'})
if __name__=='__main__':
    port=int(os.environ.get('RIFT_PORT','8770'))
    init(); print(f'R/M local server: http://127.0.0.1:{port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()


