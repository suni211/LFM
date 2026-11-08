"""FM game contract values and scouting rating.

In-game model only. None of the computed salary/fee figures disclose an
actual professional contract. Based on 30 game attributes, recorded real
2026 pro-game outcomes when identity-matched, completed LFM fixtures, and
observable fame/participation. Existing signed contracts are not overwritten.
"""
import json
import math
from functools import lru_cache
from pathlib import Path

import player_attributes

MATCH_FILE=Path(__file__).resolve().parents[1]/'assets'/'pro-performance-2026.json'

# Competitive exposure is a reputation input, NOT a claim of player quality.
VISIBILITY={
    'LCK':22,'LPL':22,'LEC':19,'LCS':18,'LCP':15,'CBLOL':14,
    'LCK CL':9,'LDL':9,'NACL':9,'LFL':11,'PRM':10,'LES':9,'TCL':10,
    'PCS':9,'LJL':9,'VCS':9,'Circuito Desafiante':7,
}
CRITERIA={
    'rating':'30개 게임 능력치 55% + 실제 프로 경기 성적 최대 30% + 게임 경기 성적 최대 15%',
    'fame':'경기 출전 수 + 리그 인지도 + 게임 수상 이력',
    'salary':'경기 레이팅·인지도·실전 경험을 반영한 게임 연봉 추정',
    'market_value':'게임 연봉·레이팅·인지도·굿즈 판매 기대수익에 따른 이적 가치',
    'note':'실제 선수의 공개 연봉이나 공식 능력치가 아닌 FM 게임 산정값',
}
@lru_cache(maxsize=1)
def performance_index():
    if not MATCH_FILE.is_file():return {}
    try:
        data=json.loads(MATCH_FILE.read_text(encoding='utf8'))
        return data.get('people',{}) if isinstance(data,dict) else {}
    except (ValueError,OSError):
        return {}

def clamp(v,lo,hi):
    return max(lo,min(hi,v))

def _round100k(v):
    return max(1000000,int(round(v/100000))*100000)

def estimate(person,ratings=None,played=None,awards=0):
    if person.get('kind') not in ('player','coach','staff'):
        return None
    is_player=person.get('kind')=='player'
    ratings=ratings or (player_attributes.estimated(person) if is_player else {})
    base=5*sum(ratings.values())/len(ratings) if ratings else 54
    source=performance_index().get(person.get('id')) or {}
    pro_games=int(clamp(source.get('games',0),0,300))
    pro_score=source.get('performance')
    if not isinstance(pro_score,(int,float)) or not math.isfinite(pro_score):
        pro_score=None
    # Missing pro match data must not be counted as a bad performance.
    # More matches increase evidence weight, but ability remains anchored.
    real_weight=min(.30,.30*pro_games/20) if is_player and pro_score is not None else 0
    live_games=int(clamp((played or {}).get('games',0),0,500))
    live_score=(played or {}).get('performance')
    live_weight=min(.15,.15*live_games/12) if is_player and isinstance(live_score,(int,float)) else 0
    rating=clamp(round(base*(1-real_weight-live_weight)
        + (pro_score or 0)*real_weight+(live_score or 0)*live_weight),1,99)
    visibility=VISIBILITY.get(person.get('league',''),7)
    reputation=clamp(round((11 if is_player else 7)+visibility
        + min(30,math.log1p(pro_games)*5.7)
        + min(18,math.log1p(live_games)*5)
        + min(15,awards*7)),1,100)
    # Transparent, reproducible in-game KRW model. Distinct star salaries;
    # no player gets a factual "reported salary" label.
    annual=_round100k(clamp(
        9000000 + (max(0,rating-32)**2)*36000 + reputation*310000
        + math.sqrt(pro_games)*130000,
        12000000,900000000
    ))
    if not is_player:
        annual=_round100k(annual*.66)
    valuation=_round100k(clamp(annual*(2.3+rating/130+reputation/250),
                                15000000,2500000000))
    # Merchandise sales use a fictional games-only demand curve. The expected
    # gross is not the same as club profit: manufacturing and logistics cost 55%.
    merch_gross=_round100k(max(1000000,(reputation**2)*28000+(rating**2)*3000))
    merch_profit=_round100k(merch_gross*.45)
    # Year-one player valuation can be profitable through fan engagement even
    # when immediate performance improvement is small.
    marketing=round(reputation*.5+min(20,pro_games/5),1)
    return dict(rating=rating,ovr=rating,ability=round(base,1),
                fame=reputation,annual_salary=annual,market_value=valuation,
                merch_annual_sales=merch_gross,merch_annual_profit=merch_profit,
                marketing_impact=marketing,
                pro_games=pro_games,pro_performance=pro_score,
                in_game_games=live_games,in_game_performance=live_score,
                basis='game-estimate',criteria=CRITERIA)


def completed_games(db,person_id,limit=120):
    games=0
    score=0
    # Only game data involving the exact person id. Every completed fixture
    # counts once; a mirrored team entry may repeat and is deduplicated.
    games_seen=set()
    for fixture,raw in db.execute(
        "SELECT id,result FROM fixtures WHERE state='finished' AND result IS NOT NULL ORDER BY id DESC LIMIT ?",
        (limit,)):
        try:
            payload=json.loads(raw)
        except (TypeError,ValueError):continue
        if not isinstance(payload,dict):continue
        for set_no,game in enumerate(payload.get('sets',[payload])):
            if not isinstance(game,dict):continue
            participants=game.get('players',[])
            if not isinstance(participants,list):continue
            for i,p in enumerate(participants):
                if p.get('player_id')!=person_id:continue
                ident=(fixture,set_no)
                if ident in games_seen:continue
                games_seen.add(ident)
                kda=p.get('kda',[0,0,0])
                if not isinstance(kda,list) or len(kda)!=3:continue
                k,d,a=(max(0,float(x)) if isinstance(x,(int,float)) else 0 for x in kda)
                team=p.get('team',i//5)
                won=int(team==game.get('winner'))
                # Rating uses recorded kills, deaths, assists, and game wins.
                per=clamp(47+8*won+clamp((k+.55*a-d*1.7)*1.7,-20,25),15,95)
                score+=per
                games+=1
    return dict(games=games,performance=round(score/games,1) if games else None)

def awarded(db,person_id):
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='season_honors'").fetchone()
    if not exists:return 0
    return db.execute("SELECT COUNT(*) FROM season_honors WHERE person_id=?",(person_id,)).fetchone()[0]

def profile(db,person):
    if person.get('kind') not in ('player','coach','staff'):return None
    detailed=player_attributes.read(db,person)
    ratings=detailed['ratings'] if detailed else None
    return estimate(person,ratings=ratings,
                    played=completed_games(db,person['id']),
                    awards=awarded(db,person['id']))
