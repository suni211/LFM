"""Versioned series formats. Unknown stages never silently become BO3."""
SOURCE='https://lolesports.com/en-US/news/season-start-2026-lol-esports'
DEFAULTS=(('First Stand','group',5,SOURCE),('First Stand','knockout',5,SOURCE),
          ('First Stand','final',5,SOURCE),
          ('MSI','play_in',5,'https://lolesports.com/en-US/lolesports/news/msi-and-worlds-updates'),
          ('MSI','bracket',5,SOURCE),('MSI','upper_final',5,SOURCE),('MSI','lower_final',5,SOURCE),('MSI','final',5,SOURCE),
          ('Worlds','play_in',5,SOURCE),('Worlds','quarterfinal',5,SOURCE),('Worlds','semifinal',5,SOURCE),('Worlds','final',5,SOURCE),
          ('practice','practice',3,'game-rule'))

def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS competition_rules(
        career_id INTEGER NOT NULL REFERENCES careers(id),
        competition TEXT NOT NULL, stage TEXT NOT NULL,
        best_of INTEGER NOT NULL CHECK(best_of IN (3,5)),
        source TEXT NOT NULL,
        PRIMARY KEY(career_id,competition,stage))''')

def validate(competition,stage,best_of):
    if (not isinstance(competition,str) or not 1<=len(competition.strip())<=120 or
        not isinstance(stage,str) or not 1<=len(stage.strip())<=80 or
        type(best_of) is not int or best_of not in (3,5)):
        raise ValueError('invalid competition rule')

def configure(db,career,competition,stage,best_of):
    validate(competition,stage,best_of)
    db.execute('''INSERT INTO competition_rules VALUES(?,?,?,?,?)
        ON CONFLICT(career_id,competition,stage) DO UPDATE SET best_of=excluded.best_of,source=excluded.source''',
        (career,competition.strip(),stage.strip(),best_of,'game-rule:admin'))

def list_rules(db,career):
    rules={(c,s):dict(competition=c,stage=s,best_of=b,source=src) for c,s,b,src in DEFAULTS}
    for c,s,b,src in db.execute('SELECT competition,stage,best_of,source FROM competition_rules WHERE career_id=?',(career,)):
        rules[c,s]=dict(competition=c,stage=s,best_of=b,source=src)
    return sorted(rules.values(),key=lambda rule:(rule['competition'],rule['stage']))

def resolve(db,career,competition,stage):
    for rule in list_rules(db,career):
        if (rule['competition'],rule['stage'])==(competition,stage):
            return rule['best_of']
    raise ValueError('competition stage format has not been configured')
