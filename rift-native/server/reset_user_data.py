"""Remove accounts, clubs and match history. Keep the player catalog and solo ladder."""
import catalog

def reset(db):
    db.execute('PRAGMA foreign_keys=OFF')
    keep={'solo_ranks','solo_people','solo_seed'}
    for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
        if name in keep or not name.replace('_','').isalnum(): continue
        db.execute('DELETE FROM "'+name+'"')
    db.execute('CREATE TEMP TABLE keep_ids(id TEXT PRIMARY KEY)')
    db.executemany('INSERT OR IGNORE INTO keep_ids VALUES(?)',[(person['id'],) for person in catalog.load().get('people',[])])
    db.execute("INSERT OR IGNORE INTO keep_ids SELECT person_id FROM solo_ranks WHERE person_id LIKE 'amateur-%'")
    db.execute('DELETE FROM solo_ranks WHERE person_id NOT IN (SELECT id FROM keep_ids)')
    db.execute('DELETE FROM solo_people WHERE person_id NOT IN (SELECT id FROM keep_ids)')
    db.execute('UPDATE solo_ranks SET career_id=NULL')
    db.execute("""UPDATE solo_ranks SET path='amateur', stall=0, last_talk_turn=-1, club_name=''
        WHERE path='prospect' AND person_id LIKE 'amateur-%'""")
    db.execute('DROP TABLE keep_ids')
    db.execute('INSERT INTO online_clock VALUES(1,1,1,1)')
    db.execute('PRAGMA foreign_keys=ON')
