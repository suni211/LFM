"""Fictional club merchandise sales and weekly player profit.

Weekly sales are derived from signed player fame, team fan affinity and
simulated demand. Real-world shirt sales are never asserted.
"""
import math
import player_economy


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS club_merchandise(
        career_id INTEGER NOT NULL,season INTEGER NOT NULL,
        week INTEGER NOT NULL,person_id TEXT NOT NULL,
        units INTEGER NOT NULL,gross_sales INTEGER NOT NULL,
        production_cost INTEGER NOT NULL,club_profit INTEGER NOT NULL,
        PRIMARY KEY(career_id,season,week,person_id))""")


def estimate(person,fan_support=50):
    econ=person.get('economics') or player_economy.estimate(person)
    if not econ or person.get('kind')!='player':
        return dict(units=0,gross_sales=0,cost=0,profit=0)
    factor=max(.20,min(1.9,float(fan_support)/65))
    # One simulated item per 35,000 KRW of fictional gross demand.
    gross=int(econ['merch_annual_sales']/150*factor)
    units=max(0,gross//35000)
    gross=units*35000
    cost=units*19250
    return dict(units=units,gross_sales=gross,cost=cost,profit=gross-cost)


def weekly(db,career,season,week,contracts,fan_support):
    import management
    for contract in contracts:
        if not contract['active'] or contract['end_turn']<(season-1)*150+week:
            continue
        person=contract['person']
        if person.get('kind')!='player':continue
        outcome=estimate(person,fan_support)
        if not outcome['units']:continue
        changed=db.execute("""INSERT OR IGNORE INTO club_merchandise(
            career_id,season,week,person_id,units,gross_sales,production_cost,club_profit)
            VALUES(?,?,?,?,?,?,?,?)""",
            (career,season,week,person['id'],
             outcome['units'],outcome['gross_sales'],outcome['cost'],outcome['profit']))
        if changed.rowcount:
            management.ledger(db,career,
                f'merchandise:{season}:{week}:{person["id"]}',
                outcome['profit'],'merchandise',
                (person.get('nickname') or person.get('real_name') or '선수')+
                ' 굿즈 판매 순이익',season,week)


def snapshot(db,career,season=None):
    if season is None:
        season=db.execute('SELECT season FROM careers WHERE id=?',(career,)).fetchone()[0]
    rows=db.execute("""SELECT person_id,SUM(units),SUM(gross_sales),
        SUM(production_cost),SUM(club_profit) FROM club_merchandise
        WHERE career_id=? AND season=? GROUP BY person_id
        ORDER BY SUM(club_profit) DESC""",(career,season)).fetchall()
    return dict(season=season,units=sum(r[1] for r in rows),
        sales=sum(r[2] for r in rows),costs=sum(r[3] for r in rows),
        profit=sum(r[4] for r in rows),
        players=[dict(id=pid,units=u,sales=gross,cost=cost,profit=profit)
                 for pid,u,gross,cost,profit in rows])
