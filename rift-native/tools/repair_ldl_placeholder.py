"""One-time repair for the eight fictional LDL bucket players.

Assignments are GAME SIMULATION placements at historically documented LDL
organizations, not claims about their real-world contracts in 2026.
Dry-run by default. Run with --apply only on a backed-up test database.
"""
import argparse
import json
import os
import shutil
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "assets" / "people.json"
BAD = "LDL 2군"
# Historical LDL participant names (2025); 2026 game assignments are fictional.
ASSIGNMENTS = {
    "2246b9279d05bc478958": "Top Esports Challenger",
    "fc55cb581ae744ae9d91": "Bilibili Gaming Junior",
    "2bf5d5a5ce06789a9bca": "Top Esports Challenger",
    "a9a2146013b938c963b8": "Bilibili Gaming Junior",
    "baca779894caca007c72": "EDG Youth Team",
    "5969315173ce4a16f7ad": "EDG Youth Team",
    "2763f580151bee68f1b5": "Team WE Academy",
    "08166da21242984af349": "Team WE Academy",
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--db", type=Path, default=Path(os.environ.get("RIFT_DB", ROOT / "server" / "server.db")))
    args = parser.parse_args()
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    current = {p["id"]: p for p in data["people"] if p.get("league") == "LDL" and p.get("team") == BAD}
    unexpected = set(current) - set(ASSIGNMENTS)
    if unexpected:
        raise SystemExit(f"Unmapped LDL placeholder IDs: {sorted(unexpected)}. No changes made.")
    if not current:
        print("No LDL 2군 placeholder players remain; nothing to do.")
        return
    print("Proposed in-game assignments (not verified real-world affiliations):")
    for pid, player in current.items():
        print(f"  {player.get('nickname')} ({player.get('role')}) -> {ASSIGNMENTS[pid]}")
    if not args.apply:
        print("DRY RUN only. Add --apply to save.")
        return
    if args.db.exists():
        with sqlite3.connect(args.db) as db:
            exists = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='club_profiles'").fetchone()
            if exists:
                affected = db.execute("""SELECT c.id,c.name FROM careers c
                    JOIN club_profiles p ON p.career_id=c.id
                    WHERE p.league='LDL' AND c.name=?""", (BAD,)).fetchall()
                if affected:
                    raise SystemExit(f"Existing careers use placeholder club: {affected}. Manual migration needed; no changes made.")
                rosters = db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='club_roster'").fetchone()
                if rosters:
                    ids = tuple(current)
                    q = "SELECT count(*) FROM club_roster WHERE person_id IN (" + ",".join("?" for _ in ids) + ")"
                    if db.execute(q, ids).fetchone()[0]:
                        raise SystemExit("Existing club_roster owns an affected player; no changes made.")
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = CATALOG.with_name("people.json.backup-" + suffix)
    shutil.copy2(CATALOG, backup)
    for pid, player in current.items():
        player.setdefault("original_team_bucket", BAD)
        player["team"] = ASSIGNMENTS[pid]
        player["assignment_origin"] = "fictional-game-ldl-placement"
    tmp = CATALOG.with_suffix(".json.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        tmp.replace(CATALOG)
    finally:
        if tmp.exists():
            tmp.unlink()
    print(f"Updated {len(current)} players. Backup: {backup}")
    print("Restart the isolated LFM test API after checking the assignment list.")

if __name__ == "__main__":
    main()
