"""150-week career season structure. Scheduling windows are in-game rules,
not claims about real-world 2026 tournament dates."""
WEEKS=150
REGIONAL_START=11
REGIONAL_END=125
WORLD_REST=(126,130)
WORLD_SWISS=(131,136)
WORLD_PLAYOFFS=(137,144)

# League-specific playable weeks, leaving room for international breaks.
# A real calendar import or administrator-created fixture overrides these slots.
WINDOWS={
    'LCK': ((11,27,'LCK CUP'),(36,55,'LCK Circuit 1'),(65,88,'LCK Circuit 2'),(97,125,'LCK Finals')),
    'LCK CL': ((11,27,'LCK CL'),(36,55,'LCK CL'),(65,88,'LCK CL'),(97,125,'LCK CL')),
    'LPL': ((11,27,'LPL Split 1'),(36,55,'LPL Split 2'),(65,88,'LPL Split 3'),(97,125,'LPL Playoffs')),
    'LDL': ((11,27,'LDL'),(36,55,'LDL'),(65,88,'LDL'),(97,125,'LDL')),
}
DEFAULT_WINDOWS=((11,27,'regional'),(36,55,'regional'),(65,88,'regional'),(97,125,'regional'))
INTERNATIONAL=((28,35,'international'),(56,64,'international'),(89,96,'international'))

def absolute_turn(season,week):
    if type(season) is not int or type(week) is not int or season<1 or not 1<=week<=WEEKS:
        raise ValueError('invalid season/week')
    return (season-1)*WEEKS+week

def decode_turn(turn):
    if type(turn) is not int or turn<1:raise ValueError('invalid turn')
    return (turn-1)//WEEKS+1,(turn-1)%WEEKS+1

def following(season,week):
    absolute_turn(season,week)
    return (season+1,1) if week==WEEKS else (season,week+1)

def phase(week):
    if not 1<=week<=WEEKS: raise ValueError('invalid week')
    if week<=10:return 'preseason-transfer'
    if week<=125:
        if any(start<=week<=end for start,end,_ in INTERNATIONAL):return 'international'
        return 'regional'
    if week<=130:return 'worlds-break'
    if week<=136:return 'worlds-swiss'
    if week<=144:return 'worlds-playoffs'
    return 'postseason-transfer'

def league_windows(league):
    return WINDOWS.get(league,DEFAULT_WINDOWS)

def round_slots(league):
    """Distinct regional weeks; never schedule weekly fixtures in all 115 weeks."""
    return [(week,label) for start,end,label in league_windows(league)
            for week in range(start,end+1)]

def migrate_legacy_schema(db):
    """Upgrade old 104-week saves and fixture constraints without losing history.

    Must be called with foreign_keys=OFF, before database init completes.
    If migration fails, SQLite rolls back its transaction.
    """
    import re
    db.execute("""CREATE TABLE IF NOT EXISTS season_schema_migrations(
        version INTEGER PRIMARY KEY,applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)""")
    if db.execute('SELECT 1 FROM season_schema_migrations WHERE version=150').fetchone():
        return False
    db.execute('BEGIN IMMEDIATE')
    try:
        for table in ('fixtures','league_games'):
            row=db.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
            if not row or not row[0] or 'BETWEEN 1 AND 104' not in row[0]:
                continue
            sql=row[0]
            name='__fm_150_'+table
            body=sql[sql.index('('):].replace('BETWEEN 1 AND 104','BETWEEN 1 AND 150')
            indexes=[r[0] for r in db.execute(
                "SELECT sql FROM sqlite_master WHERE type='index' AND tbl_name=? AND sql IS NOT NULL",(table,))]
            triggers=[r[0] for r in db.execute(
                "SELECT sql FROM sqlite_master WHERE type='trigger' AND tbl_name=? AND sql IS NOT NULL",(table,))]
            db.execute('CREATE TABLE "'+name+'" '+body)
            cols=[r[1] for r in db.execute('PRAGMA table_info("'+table+'")')]
            names=','.join('"'+c+'"' for c in cols)
            db.execute('INSERT INTO "'+name+'"('+names+') SELECT '+names+' FROM "'+table+'"')
            db.execute('DROP TABLE "'+table+'"')
            db.execute('ALTER TABLE "'+name+'" RENAME TO "'+table+'"')
            for sql in indexes+triggers:
                db.execute(sql)
        transforms={
            'club_contracts':('end_turn',),
            'contract_signings':('start_turn',),
            'club_health':('injury_until',),
            'management_turns':('turn',),
            'club_relationships':('last_mediation',),
            'transfer_offers':('created_turn',),
        }
        for table,fields in transforms.items():
            if not db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():continue
            actual={row[1] for row in db.execute('PRAGMA table_info("'+table+'")')}
            for column in fields:
                if column not in actual:continue
                db.execute('UPDATE "'+table+'" SET "'+column+'" = '
                           '((("'+column+'"-1)/104)*150 + (("'+column+'"-1)%104) + 1) '
                           'WHERE "'+column+'">0')
        db.execute('INSERT INTO season_schema_migrations(version) VALUES(150)')
        db.execute('COMMIT')
        return True
    except BaseException:
        db.execute('ROLLBACK')
        raise
