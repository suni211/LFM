"""Persist simulated AI-to-AI signings separately from rumors and user offers.

A deal is official only after a roster movement has been recorded. Never move a
user-managed player or a club with an active career. Repeat calls are idempotent.
"""
import hashlib
from collections import Counter, defaultdict

import catalog
import clubs


def init(db):
    db.executescript("""CREATE TABLE IF NOT EXISTS ai_player_clubs (
        person_id TEXT PRIMARY KEY,
        league TEXT NOT NULL,
        team TEXT NOT NULL,
        moved_season INTEGER NOT NULL,
        moved_week INTEGER NOT NULL
    );
    CREATE TABLE IF NOT EXISTS ai_transfer_events (
        id INTEGER PRIMARY KEY,
        league TEXT NOT NULL,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        person_id TEXT NOT NULL,
        player_name TEXT NOT NULL,
        from_team TEXT NOT NULL,
        to_team TEXT NOT NULL,
        fee INTEGER NOT NULL,
        kind TEXT NOT NULL DEFAULT 'player',
        UNIQUE (league,season,week,person_id)
    );
    CREATE TABLE IF NOT EXISTS ai_transfer_weeks (
        league TEXT NOT NULL,
        season INTEGER NOT NULL,
        week INTEGER NOT NULL,
        PRIMARY KEY (league,season,week)
    );
    CREATE INDEX IF NOT EXISTS ai_transfer_league_date
        ON ai_transfer_events (league,season,week);
    """)


def unit(value):
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "big")


def claimed(db):
    """Any career, even one labelled AI, is managed by its own roster logic."""
    if not db.execute("SELECT 1 FROM sqlite_master WHERE name='club_profiles'").fetchone():
        return set()
    rows=db.execute("""SELECT p.league,c.name,p.team_key
        FROM careers c JOIN club_profiles p ON p.career_id=c.id""")
    blocked=set()
    for league,name,team_key in rows:
        blocked.add((league,name))
        if team_key:
            blocked.add(("key",team_key))
    return blocked


def rosters(db):
    blocked=claimed(db)
    changes=catalog.game_clubs(db)
    groups=defaultdict(lambda:defaultdict(list))
    for raw in catalog.load()["people"]:
        if raw.get("kind")!="player" or not raw.get("real_person"):
            continue
        current=catalog.apply_game_club(raw,changes)
        league,team=current.get("league"),current.get("team")
        if not league or not team or (league,team) in blocked:
            continue
        if ("key",clubs.key(league,team)) in blocked:
            continue
        groups[league][team].append(current)
    return groups


def weekly(db,season,week):
    """Make at most one genuine AI deal per eligible league per stove week."""
    if type(season) is not int or type(week) is not int:
        raise ValueError("invalid simulation date")
    if not (1 <= week <= 10):
        return 0
    completed=0
    for league, teams in sorted(rosters(db).items()):
        if db.execute("""SELECT 1 FROM ai_transfer_weeks
            WHERE league=? AND season=? AND week=?""",(league,season,week)).fetchone():
            continue
        # Deal propensity is deterministic. No fictional transfer event is
        # shown when no eligible personnel pair exists.
        if unit(f"{season}:{week}:{league}:transfer") % 4 == 0:
            candidates=[]
            for team,players in sorted(teams.items()):
                by_role=Counter(p.get("role") for p in players)
                # Do not strip the last real player for a position from the AI.
                for person in players:
                    role=person.get("role")
                    if role in ("TOP","JUNGLE","MID","ADC","SUPPORT") and by_role[role]>1:
                        candidates.append((team,person))
            if candidates and len(teams)>1:
                candidates.sort(key=lambda x:(x[0],x[1]["id"]))
                source,person=candidates[unit(f"{season}:{week}:{league}:person")%len(candidates)]
                targets=sorted(t for t in teams if t!=source)
                target=targets[unit(f"{season}:{week}:{league}:destination")%len(targets)]
                # Game fee only. No assertion that real-world clubs paid it.
                fee=(10+unit(f"{season}:{week}:{league}:fee")%90)*1_000_000
                db.execute("""INSERT INTO ai_player_clubs
                    (person_id,league,team,moved_season,moved_week) VALUES(?,?,?,?,?)
                    ON CONFLICT(person_id) DO UPDATE SET league=excluded.league,
                    team=excluded.team,moved_season=excluded.moved_season,moved_week=excluded.moved_week""",
                    (person["id"],league,target,season,week))
                if db.execute("SELECT 1 FROM sqlite_master WHERE name='person_ownership'").fetchone():
                    db.execute("""UPDATE person_ownership
                        SET club_key=? WHERE person_id=? AND career_id IS NULL""",
                        (clubs.key(league,target),person["id"]))
                db.execute("""INSERT INTO ai_transfer_events
                    (league,season,week,person_id,player_name,from_team,to_team,fee,kind)
                    VALUES(?,?,?,?,?,?,?,?,?)""",
                    (league,season,week,person["id"],catalog.display(person),source,target,fee,"player"))
                completed+=1
        db.execute("INSERT INTO ai_transfer_weeks VALUES(?,?,?)",(league,season,week))
    return completed


def official(db,league="",limit=150):
    if not isinstance(league,str) or len(league)>100:
        raise ValueError("invalid league")
    if type(limit) is not int or not 1<=limit<=500:
        raise ValueError("invalid page size")
    sql="""SELECT id,league,season,week,person_id,player_name,from_team,to_team,fee,kind
        FROM ai_transfer_events"""
    args=[]
    if league:
        sql+=" WHERE league=?"
        args.append(league)
    sql+=" ORDER BY season DESC,week DESC,id DESC LIMIT ?"
    args.append(limit)
    return [dict(zip(("id","league","season","week","person_id","player_name",
                      "from_team","to_team","fee","kind"),row),
                 origin="ai",status="official")
            for row in db.execute(sql,args)]
