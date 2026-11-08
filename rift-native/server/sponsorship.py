"""Fictional esports sponsorship with one title partner and several supporters.

All brands are existing real-world companies, but EVERY proposed contract,
amount and affiliation is fictional. No real business is contacted.
"""
import hashlib
import random
import club_history

DISCLAIMER='실존 기업 이름을 활용한 게임 내 가상 계약입니다. 실제 후원 관계가 아닙니다. 제휴·연락·계약은 전혀 이루어지지 않았습니다.'
REGIONS={
  'LCK':'KR','LCK CL':'KR','LPL':'CN','LDL':'CN','LCS':'NA','NACL':'NA',
  'LEC':'EU','LFL':'EU','LES':'EU','PRM':'EU','TCL':'EU',
  'CBLOL':'BR','Circuito Desafiante':'BR','LCP':'APAC','PCS':'APAC',
  'LJL':'JP','VCS':'VN','FLS':'EU','WildCard':'APAC'
}
MAJOR={'LCK','LPL','LCS','LEC','LCP','CBLOL'}
GLOBAL_TITLE=('Red Bull','Razer','Logitech G','HyperX','ASUS ROG','Intel',
              'Alienware','Acer Predator','Samsung Odyssey','LG UltraGear','SteelSeries',
              'Corsair','Secretlab','MSI Gaming','AMD','NVIDIA')
LOCAL_TITLE={
 'KR':('삼성전자','SK텔레콤','현대자동차','네이버','카카오','넥슨','LG전자','농심'),
 'CN':('Tencent','JD.com','Lenovo Legion','Xiaomi','BYD','Bilibili','Meituan','OPPO'),
 'NA':('Microsoft','Google','Dell','HP OMEN','Best Buy','T-Mobile','Verizon'),
 'EU':('BMW','SAP','adidas','Orange','Deutsche Telekom','Vodafone','Kia','Puma'),
 'BR':('Nubank','Itaú','Mercado Livre','KaBuM!','Banco do Brasil'),
 'APAC':('Sony','ASUS','Acer','AirAsia','Grab','Singtel'),
 'JP':('Sony','Toyota','Nintendo','Panasonic','GALLERIA','G-Tune'),
 'VN':('Viettel','FPT','VNG','Vingroup','MoMo')
}
LOCAL_SUPPORT={
 'KR':('컴포즈커피','메가MGC커피','빽다방','맘스터치','노브랜드버거','이디야커피',
       '교촌치킨','BBQ치킨','롯데리아','GS25','CU','오뚜기','풀무원','무신사','올리브영'),
 'CN':('Heytea','CHAGEE','Luckin Coffee','Mixue','Haier','Anta','Li-Ning',
       'Uniqlo','Kuaishou','Douyin','TCL','Didi'),
 'NA':('Chipotle','Taco Bell',"Jersey Mike's",'Subway','Popeyes','Walmart',
       'GameStop','DoorDash','Uber Eats','Domino’s','Dunkin’'),
 'EU':('ALDI','Lidl','REWE','Carrefour','Auchan','Decathlon','Fnac','MediaMarkt',
       'Just Eat','Deliveroo','NIVEA','Tesco','Zalando'),
 'BR':('iFood','Casas Bahia','Magazine Luiza','O Boticário','Havaianas',
       'Cacau Show','Localiza','Renner','Sadia'),
 'APAC':('Shopee','Lazada','Foodpanda','GrabFood','Jollibee','Uniqlo','7-Eleven',
         'Acer','OPPO','Xiaomi','Secretlab'),
 'JP':('FamilyMart','Lawson','7-Eleven','Bic Camera','Yodobashi Camera',
       'Don Quijote','KFC Japan','ZOZOTOWN','G-Tune'),
 'VN':('Highlands Coffee','The Coffee House','WinMart','Shopee','Lazada',
       'Vinamilk','Biti’s','Tiki')
}
# Small sponsors are intentionally possible at any club strength and division.
SUPPORT_GLOBAL=('Razer','Logitech G','HyperX','SteelSeries','Corsair',
                'ASUS ROG','MSI Gaming','Turtle Beach','NZXT','Elgato','Secretlab')
COMPANIES={region:list(dict.fromkeys(LOCAL_TITLE[region]+GLOBAL_TITLE+LOCAL_SUPPORT[region]+SUPPORT_GLOBAL))
           for region in LOCAL_TITLE}
TIERS=('main','support')
MAX_SUPPORT=4

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
        PRIMARY KEY(career_id,start_season));
    CREATE TABLE IF NOT EXISTS sponsor_contract_tiers(
        career_id INTEGER NOT NULL REFERENCES careers(id),company TEXT NOT NULL,
        tier TEXT NOT NULL CHECK(tier IN ('main','support')),
        region TEXT NOT NULL,start_season INTEGER NOT NULL,
        end_season INTEGER NOT NULL,amount INTEGER NOT NULL,
        PRIMARY KEY(career_id,company,start_season));
    CREATE INDEX IF NOT EXISTS sponsor_contract_tiers_current
        ON sponsor_contract_tiers(career_id,tier,end_season);""")
    columns={row[1] for row in db.execute('PRAGMA table_info(sponsor_offers)')}
    if 'tier' not in columns:
        db.execute("ALTER TABLE sponsor_offers ADD COLUMN tier TEXT NOT NULL DEFAULT 'main'")
    # Migrate old main sponsorship without losing historic deals.
    db.execute("""INSERT OR IGNORE INTO sponsor_contract_tiers
        (career_id,company,tier,region,start_season,end_season,amount)
        SELECT career_id,company,'main',region,start_season,end_season,amount
        FROM sponsor_contracts""")

def _rng(*parts):
    h=hashlib.sha256('|'.join(map(str,parts)).encode()).digest()
    return random.Random(int.from_bytes(h[:8],'big'))

def _team(db,career):
    return db.execute("""SELECT c.name,p.league,c.season
        FROM careers c JOIN club_profiles p ON p.career_id=c.id
        WHERE c.id=?""",(career,)).fetchone()

def offer(db,career,season,why='team-performance',tier='main',slot=0):
    if tier not in TIERS:raise ValueError('invalid sponsor tier')
    row=_team(db,career)
    if not row:return None
    team,league,_=row;region=REGIONS.get(league,'APAC')
    choices=list(dict.fromkeys((LOCAL_TITLE[region]+GLOBAL_TITLE)
              if tier=='main' else (LOCAL_SUPPORT[region]+SUPPORT_GLOBAL)))
    rng=_rng('sponsor',career,season,region,tier,slot)
    existing={name for name, in db.execute(
        'SELECT company FROM sponsor_offers WHERE career_id=? AND season=?',(career,season))}
    existing.update(name for name, in db.execute(
        'SELECT company FROM sponsor_contract_tiers WHERE career_id=? AND end_season>=?',
        (career,season)))
    rng.shuffle(choices)
    company=next((name for name in choices if name not in existing),None)
    if not company:return None
    amount=rng.randrange(7,22)*10000000 if tier=='main' else rng.randrange(2,16)*1000000
    if tier=='main' and league not in MAJOR:amount=amount*3//5
    db.execute("""INSERT OR IGNORE INTO sponsor_offers
        (career_id,season,company,region,amount,tier) VALUES(?,?,?,?,?,?)""",
        (career,season,company,region,amount,tier))
    return dict(company=company,amount=amount,tier=tier,
                source='fictional-game-contract',notice=DISCLAIMER)

def generate_available(db,career):
    row=_team(db,career)
    if not row:return
    _,league,season=row
    # Always keep grassroots supporting offers accessible, independent of win rate.
    pending=db.execute("""SELECT COUNT(*) FROM sponsor_offers
        WHERE career_id=? AND season=? AND tier='support' AND status='offered'""",
        (career,season)).fetchone()[0]
    for slot in range(max(0,3-pending)):
        offer(db,career,season,tier='support',slot=pending+slot)
    # All top division clubs may seek a principal corporate sponsor.
    if league in MAJOR:
        has=db.execute("""SELECT 1 FROM sponsor_offers
            WHERE career_id=? AND season=? AND tier='main'""",(career,season)).fetchone()
        if not has:offer(db,career,season,tier='main')

def year_end(db,season):
    import dashboard
    for cid,name,league in db.execute("""SELECT c.id,c.name,p.league
        FROM careers c JOIN club_profiles p ON p.career_id=c.id""").fetchall():
        table=dashboard.league_table(db,league,season)
        row=next((x for x in table if x['team']==name),None)
        if row and row['played']>=6 and row['wins']/max(1,row['played'])>=.60:
            offer(db,cid,season+1,tier='main')
        # Minor sponsorship opportunities are generated on demand each year.

def proposals(db,career):
    generate_available(db,career)
    rows=db.execute("""SELECT id,season,company,region,amount,status,source,tier
        FROM sponsor_offers WHERE career_id=?
        ORDER BY season DESC,tier,id DESC LIMIT 100""",(career,)).fetchall()
    offers=[dict(zip(('id','season','company','region','amount','status','source','tier'),row))
           for row in rows]
    active=[dict(zip(('company','region','start_season','end_season','amount','tier'),row))
        for row in db.execute("""SELECT company,region,start_season,end_season,amount,tier
            FROM sponsor_contract_tiers WHERE career_id=? ORDER BY start_season DESC LIMIT 30""",(career,))]
    return dict(offers=offers,contracts=active,notice=DISCLAIMER,
                max_support=MAX_SUPPORT,companies_by_region=REGIONS)

def accept(db,career,offer_id):
    row=db.execute("""SELECT o.company,o.region,o.amount,o.season,c.name,p.league,o.tier
       FROM sponsor_offers o JOIN careers c ON c.id=o.career_id
       JOIN club_profiles p ON p.career_id=c.id
       WHERE o.id=? AND o.career_id=? AND o.status='offered'""",
       (offer_id,career)).fetchone()
    if not row:raise ValueError('유효한 스폰서 제안이 아닙니다.')
    company,region,amount,season,team,league,tier=row
    now=db.execute('SELECT season,week FROM careers WHERE id=?',(career,)).fetchone()
    if not now or now[0]!=season:raise ValueError('해당 시즌의 계약 제안만 수락할 수 있습니다.')
    active=db.execute("""SELECT COUNT(*) FROM sponsor_contract_tiers
       WHERE career_id=? AND tier=? AND end_season>=?""",
       (career,tier,season)).fetchone()[0]
    if (tier=='main' and active>=1) or (tier=='support' and active>=MAX_SUPPORT):
        raise ValueError('해당 스폰서 등급의 계약 정원이 가득 찼습니다.')
    db.execute("UPDATE sponsor_offers SET status='accepted' WHERE id=? AND career_id=?",(offer_id,career))
    if tier=='main':
        db.execute("""UPDATE sponsor_offers SET status='expired'
            WHERE career_id=? AND season=? AND tier='main' AND id!=? AND status='offered'""",
            (career,season,offer_id))
        db.execute("""INSERT OR REPLACE INTO sponsor_contracts
            (career_id,company,region,start_season,end_season,amount)
            VALUES(?,?,?,?,?,?)""",(career,company,region,season,season+1,amount))
    db.execute("""INSERT INTO sponsor_contract_tiers
        (career_id,company,tier,region,start_season,end_season,amount)
        VALUES(?,?,?,?,?,?,?)""",(career,company,tier,region,season,season+1,amount))
    import management
    management.ensure(db,career)
    management.ledger(db,career,'sponsor:'+str(offer_id),amount,'sponsorship',
                      '가상 '+('메인' if tier=='main' else '파트너')+' 스폰서: '+company,
                      now[0],now[1])
    db.execute("""UPDATE club_finances SET transfer_budget=MIN(MAX(0,cash),transfer_budget+?)
                  WHERE career_id=?""",(amount//2,career))
    club_history.record(db,league,team,now[0],now[1],
        'sponsor-change','게임 내 '+('메인' if tier=='main' else '보조')+' 스폰서 합류… '+company,
        DISCLAIMER)
    return dict(company=company,amount=amount,tier=tier,
                source='fictional-game-contract',notice=DISCLAIMER)
