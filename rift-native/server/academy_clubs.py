"""Verified real-world tier-two organizations used by the LFM game.

LCK CL: 2026 official 10 organizations. LDL: a *historically confirmed* set
of 10 academy clubs from LDL 2025 Split 2, retained as a fictional 2026+
league for the simulation at the player's request. Never invent entrants.
The parent relationship does not imply automatic promotion of an affiliate.
"""
LCK_SOURCE='https://lolesports.com/en-US/tournament/116889604983108653/overview'
LDL_SOURCE='https://liquipedia.net/leagueoflegends/LDL/2025/Split_2/Stage_1'
PARENTS={
    'LCK CL':{
        'T1':'T1 Esports Academy',
        'Hanwha Life Esports':'Hanwha Life Esports Challengers',
        'Dplus Kia':'Dplus Kia Challengers',
        'kt Rolster':'KT Rolster Challengers',
        'HANJIN BRION':'HANJIN BRION Challengers',
        'Gen.G':'Gen.G Global Academy',
        'DN SOOPers':'DN SOOPers Challengers',
        'KRX':'Kiwoom DRX Challengers',
        'NS REDFORCE':'Nongshim Esports Academy',
        'BNK FEARX':'BNK FEARX Youth',
    },
    'LDL':{
        'TOP ESPORTS':'Top Esports Challenger',
        'BILIBILI GAMING':'Bilibili Gaming Junior',
        "Xi'an Team WE":'Team WE Academy',
        "Anyone's Legend": "Anyone's Legend Young",
        'Oh My God':'Oh My God Academy',
        'WeiboGaming':'Weibo Gaming Youth Team',
        'Suzhou LNG Esports':'LNG Esports Academy',
        'THUNDER TALK GAMING':'TT Gaming Young',
        'LGD GAMING':'LGD Gaming Youth Team',
        # Royal Club is a confirmed LDL team, but its present top-flight
        # parent was not in this catalog. No fabricated parent is assigned.
    }
}
INDEPENDENTS={'LDL':('Royal Club',)}
PARENT_LEAGUE={'LCK CL':'LCK','LDL':'LPL'}
SOURCES={'LCK CL':LCK_SOURCE,'LDL':LDL_SOURCE}

def teams(league):
    return tuple(PARENTS.get(league,{}).values())+INDEPENDENTS.get(league,())

def parent_of(league,academy):
    return next(((PARENT_LEAGUE[league],parent) for parent,team in PARENTS.get(league,{}).items()
                 if team==academy),None)

def academy_of(league,parent):
    return PARENTS.get(league,{}).get(parent)

def child_of(parent_league,parent_name):
    return next(((league,child) for league,names in PARENTS.items()
                 for child in [names.get(parent_name)]
                 if child and PARENT_LEAGUE[league]==parent_league),None)

def entries():
    return [dict(league=league,team=name,parent_team=parent[1] if parent else None,
                 parent_league=parent[0] if parent else None,
                 source=SOURCES[league],roster_status='real-organization')
            for league in PARENTS for name in teams(league)
            for parent in [parent_of(league,name)]]
