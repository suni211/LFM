"""Read-only active match lineups used by the web draft swap screen."""
import catalog
import recruitment

ROLES=('TOP','JUNGLE','MID','ADC','SUPPORT')

def lineup(db, fixture, user):
    match=db.execute("""
        SELECT f.career_id,f.opponent,p.league
        FROM fixtures f
        JOIN club_profiles p ON p.career_id=f.career_id
        JOIN members m ON m.career_id=f.career_id
        WHERE f.id=? AND m.user_id=?
    """,(fixture,user)).fetchone()
    if not match:
        return None
    own,opponent,league=match
    other=db.execute("""
        SELECT c.id FROM careers c JOIN club_profiles p ON p.career_id=c.id
        WHERE c.name=? AND p.league=? AND c.id!=? ORDER BY c.id LIMIT 1
    """,(opponent,league,own)).fetchone()
    def starters(career):
        if career is None:
            return {role:None for role in ROLES}
        view=recruitment.view(db,career)
        squad={p['role']:p for p in view['roster']
               if p.get('kind')=='player' and p.get('assignment')=='first'}
        return {role:catalog.display(squad[role]) if role in squad else None
                for role in ROLES}
    return {'roles':list(ROLES),
            'teams':[{'name':db.execute('SELECT name FROM careers WHERE id=?',(own,)).fetchone()[0],
                      'players':starters(own)},
                     {'name':opponent,'players':starters(other[0] if other else None)}]}
