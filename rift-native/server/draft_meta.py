"""Recent in-game league draft statistics; never claim global live LoL win rates."""
import json

def report(db,league,season):
    if not isinstance(league,str) or len(league)>120 or type(season) is not int or not 1<=season<=10000:raise ValueError('invalid draft statistics')
    stats={};seen=set();sets=0;series=0
    rows=db.execute("""SELECT f.id,c.name,f.opponent,f.week,f.result FROM fixtures f JOIN careers c ON c.id=f.career_id
        JOIN club_profiles p ON p.career_id=f.career_id WHERE f.state='finished' AND f.season=? AND p.league=?
        ORDER BY f.week DESC,f.id DESC LIMIT 200""",(season,league))
    for fid,home,away,week,raw in rows:
        identity=(week,*sorted((home,away)))
        if identity in seen:continue
        seen.add(identity);series+=1
        result=json.loads(raw)
        for game in result.get('sets',[result]):
            if game.get('winner') not in (0,1):continue
            sets+=1
            for p in game.get('players',[]):
                name=p.get('name')
                if not name:continue
                row=stats.setdefault(name,dict(champion=name,games=0,wins=0,bans=0))
                row['games']+=1;row['wins']+=int(p.get('team')==game['winner'])
            banned={a['champion'] for a in game.get('draft',[]) if a.get('action')=='ban'}
            for name in banned:stats.setdefault(name,dict(champion=name,games=0,wins=0,bans=0))['bans']+=1
        if series>=100:break
    for row in stats.values():
        n=row['games'];row['win_rate']=round(row['wins']*100/n,1) if n else None
        row['pick_rate']=round(row['games']*100/max(1,sets),1);row['ban_rate']=round(row['bans']*100/max(1,sets),1)
        row['recommendation']='최근 승률 양호' if n>=5 and row['win_rate']>=55 else '최근 자주 선택됨' if n>=5 and row['pick_rate']>=20 else '최근 승률 낮음' if n>=5 and row['win_rate']<45 else '표본 부족' if n<5 else '기록상 무난'
        row['sample_sufficient']=n>=5
    return dict(league=league,season=season,series=series,sets=sets,champions=stats,source='recorded-league-matches',notice='이번 게임 리그의 최근 최대 100시리즈 기록입니다. 실제 전 세계 랭크 승률이 아닙니다.')
