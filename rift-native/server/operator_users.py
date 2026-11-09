"""Operator-only user directory: public manager identity and managed club, no credentials."""
import online_world

def directory(db):
    users=[]
    for uid,account,nick in db.execute('SELECT u.id,u.name,a.nickname FROM users u LEFT JOIN account_managers a ON a.user_id=u.id ORDER BY u.id'):
        operator=online_world.operator(db,uid)
        teams=[] if operator else [dict(id=cid,team=team,league=league) for cid,team,league in db.execute("SELECT c.id,c.name,p.league FROM members m JOIN careers c ON c.id=m.career_id LEFT JOIN club_profiles p ON p.career_id=c.id WHERE m.user_id=? AND m.role='admin' ORDER BY c.id",(uid,))]
        users.append(dict(id=uid,account=account,nickname=nick or '',operator=operator,clubs=teams,status='운영자' if operator else '감독' if teams else '미소속'))
    return users
