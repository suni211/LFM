"""Explicit tier-two competition identities; club != reserve-squad assignment.

The LCK CL clubs are listed by Riot's 2026 event page. The LDL entries are
playable GAME clubs derived from development organisations, not a claim that
an official full 2026 LDL season ran or that their rosters are verified.
"""
LCK_CL=(
    "HLE Challengers",
    "T1 Esports Academy",
    "BNK FEARX Youth",
    "DNS Challengers",
    "BRO Challengers",
    "Gen.G Global Academy",
    "DK Challengers",
    "kt Challengers",
    "NS Challengers",
    "KRX Challengers",
)
LDL=(
    "BLG Junior",
    "TES Challenger",
    "EDG YOUTH TEAM",
    "LGD Young Team",
    "WE Academy",
    "WBG Youth Team",
    "AL.Young",
    "OMG Academy",
    "LNG Academy",
    "TT Young",
)
LCK_PARENT={
    "HLE Challengers":"Hanwha Life Esports",
    "T1 Esports Academy":"T1",
    "BNK FEARX Youth":"BNK FEARX",
    "DNS Challengers":"DN SOOPers",
    "BRO Challengers":"HANJIN BRION",
    "Gen.G Global Academy":"Gen.G",
    "DK Challengers":"Dplus Kia",
    "kt Challengers":"kt Rolster",
    "NS Challengers":"NS REDFORCE",
    "KRX Challengers":"KRX",
}
CLUBS={"LCK CL":LCK_CL,"LDL":LDL}
SOURCES={
    "LCK CL":"https://lolesports.com/en-US/tournament/116889604983108653/overview",
    "LDL":"https://liquipedia.net/leagueoflegends/LoL_Development_League",
}
LEGACY_PLACEHOLDERS={"LCK 2군","LDL 2군"}
LEAGUES=("LCK","LCK CL","LPL","LDL","LEC","LCS","LCP","CBLOL")
def additional():
    return [dict(league=league,team=name,players=0,staff=0,unclassified=0,
                 roster_status="verification_required",competition_level=2,
                 schedule_type="game-simulation") for league,names in CLUBS.items() for name in names]
def resolve(league):
    aliases={"LCK 2군":"LCK CL","LDL 2군":"LDL","LCKCL":"LCK CL",
             "LCK Challengers":"LCK CL"}
    return aliases.get(league,league)


def academy_people(catalog_people, league, team):
    """Read-only 2026 LCK academy source mapping; do not duplicate player IDs
    into another club's transfer ownership or assert unverified nationalities.
    """
    if league!='LCK CL' or team not in LCK_PARENT:
        return []
    parent=LCK_PARENT[team]
    return [dict(p,league=league,team=team,registered_team=parent,
                 registered_league='LCK',assignment='first',
                 source_team_relation='parent-academy') for p in catalog_people
            if p.get('league')=='LCK' and p.get('team')==parent
            and p.get('squad')=='academy' and p.get('kind')=='player']
