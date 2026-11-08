"""Custom domestic leagues with one series per team per round."""
import hashlib
import random
import secrets

def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS league_games(
        career_id INTEGER NOT NULL REFERENCES careers(id),
        season INTEGER NOT NULL, week INTEGER NOT NULL CHECK(week BETWEEN 1 AND 150),
        home TEXT NOT NULL, away TEXT NOT NULL, fixture_id INTEGER UNIQUE REFERENCES fixtures(id),
        home_wins INTEGER, away_wins INTEGER,
        PRIMARY KEY(career_id,season,week,home,away))""")

def rounds(teams):
    ring = list(teams)
    if len(ring) % 2:
        ring.append(None)
    for index in range(len(ring)-1):
        pairs = []
        for slot in range(len(ring)//2):
            first, second = ring[slot], ring[-slot-1]
            if first is not None and second is not None:
                pairs.append((first,second) if (index+slot)%2==0 else (second,first))
        yield pairs
        ring = [ring[0],ring[-1],*ring[1:-1]]

def create(db, career, season, first_week, opponents):
    if not isinstance(opponents,list) or not 3 <= len(opponents) <= 15:
        raise ValueError('league requires 4–16 clubs')
    if any(not isinstance(name,str) or not 1<=len(name.strip())<=40 for name in opponents):
        raise ValueError('invalid club name')
    row = db.execute('SELECT name,season,week FROM careers WHERE id=?',(career,)).fetchone()
    if not row or season < row[1] or season == row[1] and first_week <= row[2]:
        raise ValueError('league must start in a future week')
    club = row[0]
    league_row=db.execute('SELECT league FROM club_profiles WHERE career_id=?',(career,)).fetchone()
    league_name=league_row[0] if league_row else 'domestic'
    teams = [club,*(name.strip() for name in opponents)]
    if len({name.casefold() for name in teams}) != len(teams):
        raise ValueError('duplicate clubs')
    schedule = list(rounds(teams))
    schedule += [[(away,home) for home,away in games] for games in schedule]
    if first_week < 1 or first_week+len(schedule)-1 > 150:
        raise ValueError('league exceeds season')
    if db.execute('SELECT 1 FROM league_games WHERE career_id=? AND season=?',(career,season)).fetchone():
        raise ValueError('league already exists')
    for offset, games in enumerate(schedule):
        week = first_week+offset
        for home,away in games:
            fixture = None
            if club in (home,away):
                fixture = db.execute(
                    'INSERT INTO fixtures(career_id,season,week,opponent,seed,competition,stage) VALUES(?,?,?,?,?,?,?)',
                    (career,season,week,away if home==club else home,secrets.randbits(31), league_name, 'regular')).lastrowid
            db.execute('INSERT INTO league_games VALUES(?,?,?,?,?,?,NULL,NULL)',
                       (career,season,week,home,away,fixture))
    return len(schedule)

def simulate_ai(db, career, season, week):
    games = db.execute("""SELECT home,away FROM league_games WHERE career_id=? AND season=? AND week=?
        AND fixture_id IS NULL AND home_wins IS NULL""",(career,season,week)).fetchall()
    for home,away in games:
        seed = hashlib.sha256(repr((career,season,week,home,away)).encode()).digest()
        rng = random.Random(seed)
        score = [0,0]
        while max(score)<2:
            score[rng.randrange(2)] += 1
        db.execute("""UPDATE league_games SET home_wins=?,away_wins=?
            WHERE career_id=? AND season=? AND week=? AND home=? AND away=?""",
            (*score,career,season,week,home,away))

def standings(db, career, season):
    rows = db.execute("""SELECT g.home,g.away,g.home_wins,g.away_wins,g.fixture_id,f.result,c.name
        FROM league_games g JOIN careers c ON c.id=g.career_id LEFT JOIN fixtures f ON f.id=g.fixture_id
        WHERE g.career_id=? AND g.season=?""",(career,season))
    import json
    table = {}
    for home,away,hw,aw,fixture,result,club in rows:
        for team in (home,away):
            table.setdefault(team,dict(team=team,wins=0,losses=0,sets_won=0,sets_lost=0))
        if fixture is not None and result:
            score = json.loads(result).get('score')
            if score is not None:
                hw,aw = score if home==club else reversed(score)
        if hw is None or aw is None:
            continue
        for team, wins, losses in ((home,hw,aw),(away,aw,hw)):
            record = table[team]
            record['wins'] += int(wins>losses)
            record['losses'] += int(wins<losses)
            record['sets_won'] += wins
            record['sets_lost'] += losses
    return sorted(table.values(),key=lambda r:(-r['wins'],r['sets_lost']-r['sets_won'],r['team']))
