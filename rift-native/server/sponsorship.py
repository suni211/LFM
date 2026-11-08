"""Fictional sponsorship from real, named regional companies.

All contracts and monetary values are GAME SIMULATION; none represents an
actual endorsement, contact, partnership or financial disclosure.
"""
import hashlib
import json
import random
import club_history

REGIONS={
  'LCK':'KR','LCK CL':'KR','LPL':'CN','LDL':'CN',
  'LCS':'NA','NACL':'NA','LEC':'EU','LFL':'EU','LES':'EU',
  'PRM':'EU','TCL':'EU','CBLOL':'BR','Circuito Desafiante':'BR',
  'LCP':'APAC','PCS':'APAC','LJL':'JP','VCS':'VN'
}
COMPANIES={
  'KR':['삼성전자','SK텔레콤','현대자동차','네이버','카카오'],
  'CN':['텐센트','징둥닷컴','비야디(BYD)','레노버','샤오미'],
  'NA':['마이크로소프트','인텔','구글','델 테크놀로지스','엔비디아'],
  'EU':['SAP','아디다스','BMW','도이체텔레콤','오렌지'],
  'BR':['누뱅크','이타우 우니방코','메르카도 리브레','마가루'],
  'APAC':['소니','에이수스','에이서','에어아시아','삼성전자'],
  'JP':['소니','토요타','닌텐도','파나소닉'],
  'VN':['빈그룹','비엣텔','FPT','모모']
}
DISCLAIMER='실존 기업 이름을 사용하는 게임 내 가상 스폰서 제안입니다. 실제 후원 관계가 아닙니다.'

def init(db):
    db.executescript("""CREATE TABLE IF NOT EXISTS sponsor_offers(
        id INTEGER PRIMARY KEY,career_id INTEGER NOT NULL REFERENCES careers(id),
        season INTEGER NOT NULL,company TEXT NOT NULL,region TEXT NOT NULL,
        amount INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'offered',
        source TEXT NOT NULL DEFAULT 'fictional-game-contract',
        UNIQUE(career_id,season,company));
    CREATE TABLE IF NOT EXISTS sponsor_contracts(
        career_id INTEGER NOT NULL REFERENCES careers(id),company TEXT NOT NULL,
        region TEXT NOT NULL,start_season INTEGER NOT NULL,
        end_season INTEGER NOT NULL,amount INTEGER NOT NULL,
        PRIMARY KEY(career_id,start_season));""")

def _rng(*parts):
    digest=hashlib.sha256('|'.join(str(v) for v in parts).encode()).digest()
    return random.Random(int.from_bytes(digest[:8],'big'))

def offer(db,career,season,why='team-performance'):
    """At most one unaccepted annual offer; called on sustained success."""
    row=db.execute('SELECT c.name,p.league FROM careers c JOIN club_profiles p ON p.career_id=c.id WHERE c.id=?',
                   (career,)).fetchone()
    if not row:return None
    team,league=row
    region=REGIONS.get(league,'APAC')
    companies=COMPANIES[region]
    rng=_rng('sponsor',career,season,region)
    company=companies[rng.randrange(len(companies))]
    amount=rng.randrange(4,15)*10000000
    db.execute("""INSERT OR IGNORE INTO sponsor_offers
        (career_id,season,company,region,amount) VALUES(?,?,?,?,?)""",
        (career,season,company,region,amount))
    return dict(company=company,amount=amount,source='fictional-game-contract')

def year_end(db,season):
    """Generate 1 offer after strong results; promoted clubs also qualify."""
    import dashboard
    from promotion import FEEDERS
    major=set(FEEDERS)
    for cid,name,league in db.execute("""SELECT c.id,c.name,p.league
        FROM careers c JOIN club_profiles p ON p.career_id=c.id""").fetchall():
        table=dashboard.league_table(db,league,season)
        team=next((x for x in table if x['team']==name),None)
        if not team or team['played']<6:continue
        if team['wins']/team['played']<.62:continue
        existing=db.execute('SELECT 1 FROM sponsor_offers WHERE career_id=? AND season=?',(cid,season)).fetchone()
        if existing:continue
        offer(db,cid,season+1)

def proposals(db,career):
    rows=db.execute("""SELECT id,season,company,region,amount,status,source
        FROM sponsor_offers WHERE career_id=?
        ORDER BY season DESC,id DESC LIMIT 30""",(career,)).fetchall()
    offers=[dict(zip(('id','season','company','region','amount','status','source'),row)) for row in rows]
    active=[dict(zip(('company','region','start_season','end_season','amount'),row))
        for row in db.execute("""SELECT company,region,start_season,end_season,amount
            FROM sponsor_contracts WHERE career_id=? ORDER BY start_season DESC LIMIT 4""",(career,))]
    return dict(offers=offers,contracts=active,notice=DISCLAIMER)

def accept(db,career,offer_id):
    row=db.execute("""SELECT o.company,o.region,o.amount,o.season,c.name,p.league
       FROM sponsor_offers o JOIN careers c ON c.id=o.career_id
       JOIN club_profiles p ON p.career_id=c.id
       WHERE o.id=? AND o.career_id=? AND o.status='offered'""",
       (offer_id,career)).fetchone()
    if not row:raise ValueError('유효한 스폰서 제안이 아닙니다.')
    company,region,amount,season,team,league=row
    now=db.execute('SELECT season,week FROM careers WHERE id=?',(career,)).fetchone()
    if not now or now[0]!=season:raise ValueError('해당 제안의 시즌이 종료됐습니다.')
    db.execute("UPDATE sponsor_offers SET status='accepted' WHERE id=? AND career_id=?",(offer_id,career))
    db.execute("""UPDATE sponsor_offers SET status='expired'
        WHERE career_id=? AND season=? AND id!=? AND status='offered'""",
        (career,season,offer_id))
    db.execute("""INSERT OR REPLACE INTO sponsor_contracts
        (career_id,company,region,start_season,end_season,amount)
        VALUES(?,?,?,?,?,?)""",(career,company,region,season,season+1,amount))
    import management
    management.ensure(db,career)
    # ledger() is the authoritative cash mutation. Do not add the fee twice.
    management.ledger(db,career,'sponsor:'+str(offer_id),amount,'sponsorship',
                      '게임 내 가상 스폰서 계약: '+company,now[0],now[1])
    db.execute("""UPDATE club_finances
        SET transfer_budget=MIN(MAX(0,cash),transfer_budget+?)
        WHERE career_id=?""",(amount//2,career))
    club_history.record(db,league,team,now[0],now[1],'sponsor-change',
                        '새 스폰서 계약… '+company+' 합류',DISCLAIMER)
    return dict(company=company,amount=amount,source='fictional-game-contract',
                notice=DISCLAIMER)
