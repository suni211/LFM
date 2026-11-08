"""Aggregate recorded game results, never substitute invented player statistics."""
import json

def hub(db,career,season):
    if type(season) is not int or not 1<=season<=10000: raise ValueError('invalid season')
    champions={};players={};matches=[]
    sets_played=0
    for fixture,week,opponent,raw in db.execute("SELECT id,week,opponent,result FROM fixtures WHERE career_id=? AND season=? AND state='finished' ORDER BY week,id",(career,season)):
        result=json.loads(raw)
        matches.append(dict(fixture=fixture,week=week,opponent=opponent,winner=result['winner'],score=result.get('score',[])))
        for game in result.get('sets',[result]):
            sets_played+=1
            for index,p in enumerate(game.get('players',[])):
                team=p.get('team',index//5);won=team==game['winner']
                champion=champions.setdefault(p['name'],dict(champion=p['name'],games=0,wins=0,bans=0))
                champion['games']+=1;champion['wins']+=int(won)
                if not p.get('player_id'): continue
                stats=players.setdefault(p['player_id'],dict(id=p['player_id'],name=p.get('player_name') or p['player_id'],role=p['role'],games=0,wins=0,kills=0,deaths=0,assists=0,cs=0,gold=0,damage=0,rating_sum=0))
                stats['games']+=1;stats['wins']+=int(won)
                for key,value in zip(('kills','deaths','assists'),p.get('kda',[0,0,0])):stats[key]+=value
                for key in ('cs','gold','damage'): stats[key]+=p.get(key,0)
                k,d,a=p.get('kda',[0,0,0])
                team_damage=sum(v.get('damage',0) for j,v in enumerate(game.get('players',[])) if v.get('team',j//5)==team)
                share=p.get('damage',0)/max(1,team_damage)
                expected={'TOP':.2,'JUNGLE':.18,'MID':.25,'ADC':.25,'SUPPORT':.12}.get(p['role'],.2)
                rating=6+min(1.4,k*.18+a*.08)-min(3.5,d*.38)+(.5 if won else -.3)+(share-expected)*2
                stats['rating_sum']+=max(1,min(9.9,rating))
            for action in game.get('draft',[]):
                if action['action']=='ban': champions.setdefault(action['champion'],dict(champion=action['champion'],games=0,wins=0,bans=0))['bans']+=1
    for stats in players.values():
        stats['win_rate']=round(100*stats['wins']/stats['games'],1)
        stats['kda']=round((stats['kills']+stats['assists'])/max(1,stats['deaths']),2)
        stats['rating']=round(stats.pop('rating_sum')/stats['games'],1)
    for c in champions.values():
        games,bans=c['games'],c['bans']
        c['win_rate']=round(100*c['wins']/games,1) if games else None
        c['pick_rate']=round(100*games/max(1,sets_played),1)
        c['ban_rate']=round(100*bans/max(1,sets_played),1)
        c['presence']=round(100*(games+bans)/max(1,sets_played),1)
        # Small samples should never be presented as authoritative global tiers.
        if games>=4 and sets_played>=8:
            impact=c['presence']*.65+c['win_rate']*.35
            c['tier']='S' if impact>=65 else 'A' if impact>=48 else 'B' if impact>=30 else 'C'
            c['tier_source']='자체 경기 표본'
        else:
            c['tier']='표본 부족'
            c['tier_source']='내 구단 기록 부족'
    return dict(patch='16.22.1',patch_source='Riot Data Dragon',
                sample_notice='내 구단의 게임 내 경기 기록 기준. 실제 전 세계 승률이나 공식 메타 통계가 아닙니다.',
                season=season,series=len(matches),sets=sets_played,matches=matches,
                players=sorted(players.values(),key=lambda p:(-p['wins'],-p['kda'],p['id'])),
                champions=sorted(champions.values(),key=lambda c:(-c['games'],-c['bans'],c['champion'])),source='simulation-results')
