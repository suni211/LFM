"""Deterministic in-game league calendar and idempotent playable club fixtures.

These are game-generated matchups, not claims about official Lolesports fixtures.
Existing manually configured fixtures are never overwritten.
"""
import hashlib
import random
import secrets
from collections import defaultdict
import catalog
import season_structure


def leagues(db):
    names={row['league'] for row in catalog.teams() if row.get('league')}
    names.update(row[0] for row in db.execute("SELECT DISTINCT league FROM club_profiles WHERE league<>''"))
    return sorted(names)


def build(db, season, league='', team=''):
    """Double round-robin spread across league-specific regional competition windows."""
    if type(season) is not int or not 1 <= season <= 10000:
        raise ValueError('invalid calendar season')
    if not isinstance(league,str) or len(league)>100 or not isinstance(team,str) or len(team)>100:
        raise ValueError('invalid calendar filter')
    groups=defaultdict(set)
    for row in catalog.teams():
        if row.get('team') and row.get('league'):
            groups[row['league']].add(row['team'])
    for club, lg in db.execute('SELECT c.name,p.league FROM careers c JOIN club_profiles p ON p.career_id=c.id'):
        if club and lg: groups[lg].add(club)
    rows=[]
    for lg in sorted(groups):
        if league and lg!=league: continue
        members=sorted(groups[lg])
        if len(members)<2: continue
        seed=int(hashlib.sha256(f'{season}:{lg}:game-calendar-v1'.encode()).hexdigest()[:16],16)
        random.Random(seed).shuffle(members)
        if len(members)%2: members.append(None)
        rotations=len(members)-1
        slots=season_structure.round_slots(lg)
        needed=rotations*2
        # If a larger league needs additional matchdays, multiple series may
        # share an active week; never create fixtures in the transfer/Worlds breaks.
        active=[slots[min(len(slots)-1,int(i*len(slots)/needed))] for i in range(needed)]
        for round_no in range(rotations):
            for leg in range(2):
                week,competition=active[round_no+leg*rotations]
                for idx in range(len(members)//2):
                    left,right=members[idx],members[-idx-1]
                    if left is None or right is None: continue
                    home,away=(left,right) if (round_no+idx+leg)%2==0 else (right,left)
                    if team and team not in (home,away): continue
                    rows.append(dict(season=season,week=week,league=lg,home=home,away=away,
                                     competition=competition,stage='regular',best_of=3,
                                     source='game-generated',state='planned'))
            # Round-robin circle rotation fixes the first team.
            members=[members[0],members[-1],*members[1:-1]]
    return sorted(rows,key=lambda row:(row['week'],row['league'],row['home'],row['away']))


def ensure_career(db, career_id):
    """Fill missing FUTURE fixtures only. Does not overwrite games or manual entries."""
    row=db.execute('''SELECT c.name,c.season,c.week,p.league FROM careers c
        JOIN club_profiles p ON p.career_id=c.id WHERE c.id=?''',(career_id,)).fetchone()
    if row is None: return 0
    name,season,current_week,league=row
    # The FM branch also has manual/seeded league_games; never override those schedules.
    if db.execute('SELECT 1 FROM league_games WHERE career_id=? AND season=? LIMIT 1',(career_id,season)).fetchone(): return 0
    created=0
    for game in build(db,season,league=league,team=name):
        if game['week']<=current_week: continue
        opponent=game['away'] if game['home']==name else game['home']
        if db.execute('SELECT 1 FROM fixtures WHERE career_id=? AND season=? AND week=?',
                      (career_id,season,game['week'])).fetchone(): continue
        db.execute('''INSERT OR IGNORE INTO fixtures(
            career_id,season,week,opponent,seed,best_of,competition,stage)
            VALUES(?,?,?,?,?,?,?,?)''',
            (career_id,season,game['week'],opponent,secrets.randbits(31),3,game['competition'],'regular'))
        created+=1
    return created
