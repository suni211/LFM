"""Hidden 3–5-year fictional franchise review. Not Riot's real promotion rules.

No public eligibility endpoint or thresholds: users see only resulting
franchise news and club-history events. Historical season form is persisted.
"""
import hashlib
import random

FEEDERS={'LCK':('LCK CL',),'LPL':('LDL',),'LCS':('NACL',),
         'LEC':('LFL','LES','PRM','TCL')}

def init(db):
    db.executescript("""CREATE TABLE IF NOT EXISTS franchise_history(
        league TEXT NOT NULL,team TEXT NOT NULL,season INTEGER NOT NULL,
        position INTEGER NOT NULL,entrant_count INTEGER NOT NULL,
        source TEXT NOT NULL,PRIMARY KEY(league,team,season));
    CREATE TABLE IF NOT EXISTS franchise_exits(
        league TEXT NOT NULL,team TEXT NOT NULL,season INTEGER NOT NULL,
        replacement TEXT NOT NULL,reason TEXT NOT NULL,PRIMARY KEY(league,team));
    CREATE TABLE IF NOT EXISTS franchise_promotions(
        career_id INTEGER PRIMARY KEY REFERENCES careers(id),
        previous_league TEXT NOT NULL,new_league TEXT NOT NULL,
        season INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'approved');
    CREATE TABLE IF NOT EXISTS franchise_announcements(
        id INTEGER PRIMARY KEY,season INTEGER NOT NULL,league TEXT NOT NULL,
        departing TEXT NOT NULL,arriving TEXT NOT NULL,headline TEXT NOT NULL,
        UNIQUE(season,league,departing,arriving));""")

def active(db,league,team,season=None):
    row=db.execute('SELECT season FROM franchise_exits WHERE league=? AND team=?',
                   (league,team)).fetchone()
    return not row or (season is not None and season<=row[0])

def _random(*parts):
    return random.Random(int.from_bytes(hashlib.sha256(
        '|'.join(map(str,parts)).encode()).digest()[:8],'big'))

def _yearly(db,league,season):
    """One real scored match overrides estimated AI strength where available."""
    import catalog, career_rules, dashboard
    names={r['team'] for r in catalog.teams() if r['league']==league}
    names.update(name for name, in db.execute(
        """SELECT c.name FROM careers c JOIN club_profiles p ON p.career_id=c.id
           WHERE p.league=?""",(league,)))
    names={name for name in names if active(db,league,name,season)}
    played={r['team']:r for r in dashboard.league_table(db,league,season)}
    scores=[]
    for name in names:
        result=played.get(name)
        if result and result['played']>=5:
            score=60*result['wins']/max(1,result['played'])+min(
                15,(result['sets_won']-result['sets_lost'])*2)
            source='in-game-match-results'
        else:
            score=career_rules.club_power(league,name)*.60+_random(
                'franchise',season,league,name).uniform(-14,14)
            source='game-AI-estimate'
        scores.append((score,name,source))
    scores.sort(key=lambda item:(-item[0],item[1]))
    for index,(_,name,source) in enumerate(scores,1):
        db.execute("""INSERT OR IGNORE INTO franchise_history
            (league,team,season,position,entrant_count,source) VALUES(?,?,?,?,?,?)""",
            (league,name,season,index,len(scores),source))

def _under_review(db,league,season):
    """Only genuinely sustained bottom finishes can trigger review."""
    names=[t for t, in db.execute(
        'SELECT DISTINCT team FROM franchise_history WHERE league=? AND season=?',
        (league,season))]
    flagged=[]
    for team in names:
        if not active(db,league,team,season):continue
        history=db.execute("""SELECT season,position,entrant_count FROM franchise_history
            WHERE league=? AND team=? AND season<=? ORDER BY season DESC LIMIT 5""",
            (league,team,season)).fetchall()
        if len(history)<3 or any(history[i][0]!=season-i for i in range(min(3,len(history)))):
            continue
        bad=0
        for year,place,size in history:
            if size>=5 and place>=max(3,(size*7+9)//10):bad+=1
            else:break
        if bad<3:continue
        # A repeatable game-board review cycle between years three and five.
        review_at=3+_random('review',league,team).randrange(3)
        if bad>=review_at:flagged.append((bad,history[0][1],team))
    flagged.sort(reverse=True)
    return [item[-1] for item in flagged]

def _best_lower(db,league,season):
    import dashboard
    choices=[]
    for lower in FEEDERS[league]:
        for row in dashboard.league_table(db,lower,season):
            if row['played']<6 or row['wins']/row['played']<.5:continue
            career=db.execute("""SELECT c.id FROM careers c JOIN club_profiles p
                ON p.career_id=c.id WHERE p.league=? AND c.name=?""",
                (lower,row['team'])).fetchone()
            if not career:continue
            cid=career[0]
            if db.execute('SELECT 1 FROM franchise_promotions WHERE career_id=?',(cid,)).fetchone():
                continue
            finances=db.execute('SELECT cash FROM club_finances WHERE career_id=?',(cid,)).fetchone()
            if not finances or finances[0]<0:continue
            ratio=row['wins']/row['played']
            choices.append((ratio,row['wins'],row['sets_won']-row['sets_lost'],cid,lower,row['team']))
    choices.sort(reverse=True)
    return choices[0] if choices else None

def year_end(db,season):
    """Run once inside shared season-boundary transaction, before next year."""
    import club_history
    for major in FEEDERS:
        _yearly(db,major,season)
        departed=_under_review(db,major,season)
        candidate=_best_lower(db,major,season) if departed else None
        if not candidate:continue
        _,_,_,cid,former,arriving=candidate
        outgoing=departed[0]
        # One new place per region/year. The real league is never modified.
        result=db.execute("""INSERT OR IGNORE INTO franchise_exits
            (league,team,season,replacement,reason) VALUES(?,?,?,?,?)""",
            (major,outgoing,season,arriving,'fictional-game-franchise-review'))
        if not result.rowcount:continue
        db.execute("""INSERT OR REPLACE INTO franchise_promotions
            (career_id,previous_league,new_league,season,status)
            VALUES(?,?,?,?,?)""",(cid,former,major,season+1,'approved'))
        headline=major+' 프랜차이즈 지각변동… '+outgoing+' 퇴장, '+arriving+' 입성'
        db.execute("""INSERT OR IGNORE INTO franchise_announcements
            (season,league,departing,arriving,headline) VALUES(?,?,?,?,?)""",
            (season+1,major,outgoing,arriving,headline))
        club_history.record(db,major,arriving,season+1,1,'promotion',
                            headline,'시뮬레이션으로 발생한 프랜차이즈 교체')
    return True

def apply_new_season(db,season):
    from career_rules import seed_league
    import club_history
    demotions=db.execute("""SELECT league,team FROM franchise_exits
        WHERE season=?""",(season-1,)).fetchall()
    for major,team in demotions:
        feeder=FEEDERS.get(major,())
        if not feeder:continue
        lower=feeder[0]
        incumbents=db.execute("""SELECT c.id FROM careers c
            JOIN club_profiles p ON p.career_id=c.id
            WHERE c.name=? AND p.league=?""",(team,major)).fetchall()
        for cid, in incumbents:
            db.execute('UPDATE club_profiles SET league=? WHERE career_id=?',
                       (lower,cid))
            club_history.record(db,major,team,season,1,'license-lost',
              '프랜차이즈 참가권 변동… '+team+' 하부 리그 재출발',
              '게임 내 가상 프랜차이즈 재심사 결과')
            try:seed_league(db,cid,lower,season,1)
            except (ValueError,KeyError):pass
    rows=db.execute("""SELECT career_id,previous_league,new_league FROM franchise_promotions
        WHERE season=? AND status='approved'""",(season,)).fetchall()
    for cid,old,new in rows:
        db.execute('UPDATE club_profiles SET league=? WHERE career_id=?',(new,cid))
        db.execute('UPDATE franchise_promotions SET status=? WHERE career_id=?',
                   ('applied',cid))
        try:seed_league(db,cid,new,season,1)
        except (ValueError,KeyError):pass
    return len(rows)
