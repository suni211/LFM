"""Fictional career progression with region-specific promotion gates.

LCS NACL promotion echoes the real guest-team qualifying route.
LCK/LPL/LEC use clearly labeled *game-only* expansion licensing, NOT claims
that real franchised leagues promote an academy club automatically.
Applied at the next season boundary after a completed season, never mid-season.
"""
import academy_clubs
import catalog
import clubs

ROUTES={
    'LCK CL':dict(target='LCK',type='expansion_license',name='LCK 신규 참가 라이선스 (게임 규칙)',
                  min_games=8,min_win_rate=.60,rank_limit=2,min_cash=40000000,min_board=65),
    'LDL':dict(target='LPL',type='expansion_license',name='LPL 신규 참가 라이선스 (게임 규칙)',
               min_games=8,min_win_rate=.60,rank_limit=2,min_cash=40000000,min_board=65),
    'NACL':dict(target='LCS',type='guest_tournament',name='LCS 승격 토너먼트 게스트 시드 (게임)',
                min_games=8,min_win_rate=.55,rank_limit=2,min_cash=25000000,min_board=55),
    'LFL':dict(target='LEC',type='erl_invitation',name='EMEA Masters 성과 기반 LEC 특별 초청 (게임)',
               min_games=8,min_win_rate=.65,rank_limit=1,min_cash=35000000,min_board=60),
    'LES':dict(target='LEC',type='erl_invitation',name='EMEA Masters 성과 기반 LEC 특별 초청 (게임)',
               min_games=8,min_win_rate=.65,rank_limit=1,min_cash=35000000,min_board=60),
    'PRM':dict(target='LEC',type='erl_invitation',name='EMEA Masters 성과 기반 LEC 특별 초청 (게임)',
               min_games=8,min_win_rate=.65,rank_limit=1,min_cash=35000000,min_board=60),
    'TCL':dict(target='LEC',type='erl_invitation',name='EMEA Masters 성과 기반 LEC 특별 초청 (게임)',
               min_games=8,min_win_rate=.65,rank_limit=1,min_cash=35000000,min_board=60),
}
SOURCES={
    'LCS':'https://lolesports.com/en-US/lolesports/news/lcs-promotion-tournament-wsci',
    'LEC':'https://lolesports.com/en-GB/news/lec-2026-format-update',
}
def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS club_promotions(
        career_id INTEGER NOT NULL REFERENCES careers(id),
        season INTEGER NOT NULL,target_league TEXT NOT NULL,
        route TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'approved',
        PRIMARY KEY(career_id,season))""")

def check(db,career):
    import dashboard
    row=db.execute('SELECT c.name,c.season,c.week,p.league FROM careers c JOIN club_profiles p ON p.career_id=c.id WHERE c.id=?',(career,)).fetchone()
    if not row:raise ValueError('career not found')
    name,season,week,league_name=row
    rule=ROUTES.get(league_name)
    if not rule:return dict(available=False,league=league_name,reason='해당 리그에는 LFM 승격 경로가 없습니다.')
    # Approval possible at the final week of the season; one per season.
    previous=db.execute('SELECT target_league,status FROM club_promotions WHERE career_id=? AND season=?',(career,season)).fetchone()
    ranked=dashboard.league_table(db,league_name,season)
    mine=next((r for r in ranked if r['team']==name),None)
    games=mine['played'] if mine else 0
    wins=mine['wins'] if mine else 0
    rank=mine['rank'] if mine else None
    finance=db.execute('SELECT cash,board FROM club_finances WHERE career_id=?',(career,)).fetchone()
    cash,board=finance if finance else (0,0)
    contract_count=db.execute('SELECT COUNT(*) FROM club_contracts WHERE career_id=? AND active=1',(career,)).fetchone()[0]
    conditions=[
        dict(label='시즌 종료 주차',current=week,need=104,met=week==104),
        dict(label='공식 경기 수',current=games,need=rule['min_games'],met=games>=rule['min_games']),
        dict(label='승률',current=round(100*wins/max(1,games),1),need=round(rule['min_win_rate']*100,1),
             met=games>0 and wins/games>=rule['min_win_rate']),
        dict(label='리그 순위',current=rank,need=rule['rank_limit'],met=rank is not None and rank<=rule['rank_limit']),
        dict(label='구단 보유 현금',current=cash,need=rule['min_cash'],met=cash>=rule['min_cash']),
        dict(label='구단주 신임',current=board,need=rule['min_board'],met=board>=rule['min_board']),
        dict(label='프로 계약 인원',current=contract_count,need=5,met=contract_count>=5),
    ]
    return dict(available=True,can_apply=all(item['met'] for item in conditions) and not previous,
                applied=bool(previous),target=rule['target'],type=rule['type'],
                route=rule['name'],source=SOURCES.get(rule['target']),
                game_rule=True,season=season,conditions=conditions,league=league_name)

def request(db,career):
    state=check(db,career)
    if not state.get('can_apply'):raise ValueError('승격 라이선스 조건을 충족하지 못했거나 이미 신청했습니다.')
    db.execute('INSERT INTO club_promotions(career_id,season,target_league,route) VALUES(?,?,?,?)',
               (career,state['season'],state['target'],state['type']))
    return dict(approved=True,effective_season=state['season']+1,
                target=state['target'],type=state['type'],game_rule=True)

def apply_new_season(db,new_season):
    """Called inside the authoritative shared-week advancement transaction."""
    from career_rules import seed_league
    rows=db.execute("""SELECT career_id,target_league FROM club_promotions
        WHERE season=? AND status='approved'""",(new_season-1,)).fetchall()
    for career,target in rows:
        db.execute('UPDATE club_profiles SET league=? WHERE career_id=?',(target,career))
        db.execute("UPDATE club_promotions SET status='applied' WHERE career_id=? AND season=?",
                   (career,new_season-1))
        # Schedule only actual catalog clubs in the new division.
        try:seed_league(db,career,target,new_season,1)
        except ValueError:pass
    return len(rows)
