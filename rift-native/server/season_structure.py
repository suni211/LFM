"""150-week career season structure. Scheduling windows are in-game rules,
not claims about real-world 2026 tournament dates."""
WEEKS=150
REGIONAL_START=11
REGIONAL_END=125
WORLD_REST=(126,130)
WORLD_SWISS=(131,136)
WORLD_PLAYOFFS=(137,144)

# League-specific playable weeks, leaving room for international breaks.
# A real calendar import or administrator-created fixture overrides these slots.
WINDOWS={
    'LCK': ((11,27,'LCK CUP'),(36,55,'LCK Circuit 1'),(65,88,'LCK Circuit 2'),(97,125,'LCK Finals')),
    'LCK CL': ((11,27,'LCK CL'),(36,55,'LCK CL'),(65,88,'LCK CL'),(97,125,'LCK CL')),
    'LPL': ((11,27,'LPL Split 1'),(36,55,'LPL Split 2'),(65,88,'LPL Split 3'),(97,125,'LPL Playoffs')),
    'LDL': ((11,27,'LDL'),(36,55,'LDL'),(65,88,'LDL'),(97,125,'LDL')),
}
DEFAULT_WINDOWS=((11,27,'regional'),(36,55,'regional'),(65,88,'regional'),(97,125,'regional'))
INTERNATIONAL=((28,35,'international'),(56,64,'international'),(89,96,'international'))

def absolute_turn(season,week):
    if type(season) is not int or type(week) is not int or season<1 or not 1<=week<=WEEKS:
        raise ValueError('invalid season/week')
    return (season-1)*WEEKS+week

def decode_turn(turn):
    if type(turn) is not int or turn<1:raise ValueError('invalid turn')
    return (turn-1)//WEEKS+1,(turn-1)%WEEKS+1

def following(season,week):
    absolute_turn(season,week)
    return (season+1,1) if week==WEEKS else (season,week+1)

def phase(week):
    if not 1<=week<=WEEKS: raise ValueError('invalid week')
    if week<=10:return 'preseason-transfer'
    if week<=125:
        if any(start<=week<=end for start,end,_ in INTERNATIONAL):return 'international'
        return 'regional'
    if week<=130:return 'worlds-break'
    if week<=136:return 'worlds-swiss'
    if week<=144:return 'worlds-playoffs'
    return 'postseason-transfer'

def league_windows(league):
    return WINDOWS.get(league,DEFAULT_WINDOWS)

def round_slots(league):
    """Distinct regional weeks; never schedule weekly fixtures in all 115 weeks."""
    return [(week,label) for start,end,label in league_windows(league)
            for week in range(start,end+1)]
