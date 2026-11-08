"""Repair fictional catch-all second-team bucket affiliations in the test catalog.

Game simulation placements only: does NOT assert real-world player contracts.
Uses actual individually named team identities already present in the catalog.
No guessing if fewer than two valid destinations exist. Dry-run by default.
"""
import argparse
import json
import os
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/'assets'/'people.json'
BUCKETS={'LCK 2군':'LCK CL','LCK CL 2군':'LCK CL','LDL 2군':'LDL'}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    parser.add_argument('--db',type=Path,default=Path(os.environ.get('RIFT_DB',ROOT/'server'/'server.db')))
    args=parser.parse_args()
    data=json.loads(PATH.read_text(encoding='utf-8'))
    people=data['people']
    bucket=[p for p in people if p.get('team') in BUCKETS and p.get('kind')=='player']
    if not bucket:
        print('No generic second-team bucket players found')
        return
    # Never invent target club names; select from named 2nd-tier clubs already in the roster.
    available={}
    for target in set(BUCKETS.values()):
        names=sorted({p.get('team') for p in people if p.get('league')==target and p.get('team') and p.get('team') not in BUCKETS and p.get('real_person')})
        available[target]=names
    for p in bucket:
        target=BUCKETS[p['team']]
        if len(available[target])<2:
            print(f'ERROR: {target} has only {len(available[target])} named clubs. Refusing arbitrary assignments.')
            print('Available:',available[target])
            raise SystemExit('Populate validated team list before reassigning this bucket')
    taken=defaultdict(set)
    allocations=[]
    for p in sorted(bucket,key=lambda p:(p.get('role') or '',p['id'])):
        target=BUCKETS[p['team']]
        role=p.get('role')
        teams=available[target]
        # Distribute by position without forcing multiple same-role starters together.
        chosen=min(teams,key=lambda team:(role in taken[(target,team)],len(taken[(target,team)]),team))
        taken[(target,chosen)].add(role)
        allocations.append((p,target,chosen))
    print('Fictional in-game placement preview:')
    for p,league,team in allocations:
        print(f"{p.get('nickname')} [{p.get('role')}] {p.get('team')} -> {league} / {team}")
    if not args.apply:
        print('DRY RUN. No files modified.')
        return
    if args.db.exists():
        with sqlite3.connect(args.db) as db:
            ids=[p['id'] for p,_,_ in allocations]
            for table in ('club_roster','generated_people','person_ownership','club_contracts','transfer_offers'):
                exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone()
                if not exists:continue
                key='id' if table=='generated_people' else 'person_id'
                for pid in ids:
                    if db.execute(f"SELECT 1 FROM {table} WHERE {key}=? LIMIT 1",(pid,)).fetchone():
                        raise SystemExit(f'{pid} has live {table} references; requires coordinated migration, no changes made.')
            if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='careers'").fetchone():
                if any(db.execute("SELECT 1 FROM careers WHERE name=?",(name,)).fetchone() for name in BUCKETS):
                    raise SystemExit('A career uses a placeholder club; migrate career first.')
    dest=PATH.with_name('people.json.second-team-backup-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    shutil.copy2(PATH,dest)
    for person,league,team in allocations:
        person['previous_placeholder_team']=person['team']
        person['team']=team
        person['league']=league
        person['club_assignment_origin']='fictional-game-placement'
    tmp=PATH.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(PATH)
    print('Updated',len(allocations),'generated bucket player records; catalog backup:',dest)

if __name__=='__main__':
    main()
