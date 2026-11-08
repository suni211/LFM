#!/usr/bin/env python3
"""Generate an ID-keyed, non-guessing nationality gap report from the live roster."""
import csv
import json
from collections import Counter
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import catalog

def audit(people):
    missing=[]
    for p in people:
        if p.get('nationality_code'):continue
        missing.append(dict(
            id=p.get('id',''),nickname=p.get('nickname',''),
            real_name=p.get('real_name',''),league=p.get('league',''),
            team=p.get('team',''),country_hint=p.get('country_name_ko',''),
            hint_source=p.get('country_source',''),
            hint_is_verified=False,
        ))
    total=len(people)
    with_code=total-len(missing)
    return dict(total=total,with_code=with_code,missing=len(missing),
                real_missing=sum(bool(p.get('real_person')) and not p.get('nationality_code') for p in people),
                hints_on_missing=sum(bool(row['country_hint']) for row in missing),
                missing_by_league=dict(sorted(Counter(r['league'] for r in missing).items()))),missing

def main():
    report,missing=audit(catalog.load()['people'])
    (ROOT/'nationality-gap-report.json').write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    path=ROOT/'nationality-gap.csv'
    with path.open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=(
            'id','nickname','real_name','league','team',
            'country_hint','hint_source','hint_is_verified'))
        writer.writeheader()
        writer.writerows(missing)
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    main()
