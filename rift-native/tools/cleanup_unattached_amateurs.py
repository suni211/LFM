"""Preview/delete only unused legacy 'amateur-*' artificial free-agent records.

Run with --apply after backing up the isolated SQLite database.
Never deletes genuine FA players, imported roster members, signed amateurs,
or anyone attached to a career or another persisted object.
"""
import argparse
import os
import sqlite3
from pathlib import Path

DB = Path(os.environ.get("RIFT_DB", Path(__file__).resolve().parents[1] / "server" / "server.db"))

def table(db, name):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())

def candidates(db):
    if not table(db, "solo_people") or not table(db, "solo_ranks"):
        return []
    sql = """SELECT p.person_id, r.nickname FROM solo_people p
        JOIN solo_ranks r ON r.person_id=p.person_id
        WHERE p.person_id LIKE 'amateur-%'
        AND (r.club_name='' OR r.club_name IS NULL)
        AND r.career_id IS NULL
        AND r.path='amateur'"""
    rows = db.execute(sql).fetchall()
    keep=[]
    for pid,nick in rows:
        if table(db,"generated_people") and db.execute(
            "SELECT 1 FROM generated_people WHERE id=?",(pid,)).fetchone(): continue
        if table(db,"club_roster") and db.execute(
            "SELECT 1 FROM club_roster WHERE person_id=?",(pid,)).fetchone(): continue
        if table(db,"person_ownership") and db.execute(
            "SELECT 1 FROM person_ownership WHERE person_id=?",(pid,)).fetchone(): continue
        if table(db,"club_contracts") and db.execute(
            "SELECT 1 FROM club_contracts WHERE person_id=?",(pid,)).fetchone(): continue
        if table(db,"transfer_offers") and db.execute(
            "SELECT 1 FROM transfer_offers WHERE person_id=?",(pid,)).fetchone(): continue
        if table(db,"transfer_events") and db.execute(
            "SELECT 1 FROM transfer_events WHERE person_id=?",(pid,)).fetchone(): continue
        if table(db,"player_departure_requests") and db.execute(
            "SELECT 1 FROM player_departure_requests WHERE person_id=?",(pid,)).fetchone(): continue
        if table(db,"agent_relations") and db.execute(
            "SELECT 1 FROM agent_relations WHERE person_id=?",(pid,)).fetchone(): continue
        if table(db,"club_health") and db.execute(
            "SELECT 1 FROM club_health WHERE person_id=?",(pid,)).fetchone(): continue
        if table(db,"person_overrides") and db.execute(
            "SELECT 1 FROM person_overrides WHERE person_id=?",(pid,)).fetchone(): continue
        keep.append((pid,nick))
    return keep

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--db",type=Path,default=DB)
    parser.add_argument("--apply",action="store_true")
    args=parser.parse_args()
    if not args.db.is_file():
        raise SystemExit("Database not found: "+str(args.db))
    with sqlite3.connect(args.db) as db:
        rows=candidates(db)
        print("Unused auto-generated unattached amateur records:",len(rows))
        for pid,nick in rows[:120]:
            print(pid,nick)
        if not args.apply:
            print("DRY RUN: no records deleted. Back up DB and rerun with --apply.")
            return
        db.execute("BEGIN IMMEDIATE")
        try:
            for pid,_ in rows:
                db.execute("DELETE FROM solo_ranks WHERE person_id=?",(pid,))
                db.execute("DELETE FROM solo_people WHERE person_id=?",(pid,))
            db.commit()
        except BaseException:
            db.rollback()
            raise
    print("Deleted unused artificial amateurs:",len(rows))

if __name__=="__main__":
    main()
