#!/usr/bin/env python3
"""Match official GCD identities to public Leaguepedia-derived country hints.

GPTilt public_figures.region = Leaguepedia NationalityPrimary OR Country.
The published snapshot does not distinguish those fields, so it is NOT safe
to treat the result as verified citizenship for import-limit rules. Exact IGN
and real-name matching supplies a country hint with an audit URL instead.
"""
import json
import pathlib
from collections import defaultdict
import pandas as pd
from import_leaguepedia_nationalities import (
    PEOPLE, ROOT, OVERRIDES, NAMES_KO, norm, same_real_name,
    country_code,
)

URL = ("https://huggingface.co/datasets/gptilt/lol-esports-entities/"
       "resolve/main/public_figures/public_figures.parquet")
OUTPUT = ROOT/"assets"/"country-hints.json"
REPORT = ROOT/"country-hints-report.json"
SNAPSHOT = "2026-06 / GPTilt public figures snapshot"


def reconcile(people, source, official):
    by_ign=defaultdict(list)
    for p in people:
        if p.get('real_person'):
            by_ign[norm(p.get('nickname'))].append(p)
    candidates=defaultdict(list)
    unmatched=defaultdict(int)
    for row in source:
        ign=row.get('display_name')
        fullname=row.get('canonical_name')
        page=row.get('source_url')
        region=row.get('region')
        if not ign or not fullname or not region or not page:
            unmatched['source-incomplete']+=1
            continue
        code=country_code(region)
        if not code:
            unmatched['country-unknown']+=1
            continue
        for p in by_ign.get(norm(ign),()):
            if not same_real_name(fullname,p.get('real_name')):
                unmatched['name-mismatch']+=1
                continue
            candidates[p['id']].append(dict(
                code=code,
                name=NAMES_KO.get(code,str(region)),
                source=str(page),
                country_data_source="gptilt/Leaguepedia",
                source_field="NationalityPrimary or Country (indistinguishable in published snapshot)",
                citizenship_verified=False,
                identity_match="exact competitive nickname + equivalent real-world name",
                dataset_snapshot=SNAPSHOT
            ))
    chosen={}
    conflicts=[]
    for p in people:
        pid=p['id']
        records=candidates.get(pid,())
        codes={x['code'] for x in records}
        if len(codes)>1:
            conflicts.append(dict(id=pid,nickname=p.get('nickname'),codes=sorted(codes)))
            continue
        if not records:continue
        record=records[0]
        official_code=p.get('nationality_code') or (official.get(pid) or {}).get('code')
        if official_code and official_code!=record['code']:
            conflicts.append(dict(id=pid,nickname=p.get('nickname'),
                verified_nationality=official_code,public_country=record['code']))
            continue
        # Keep a distinct citizenship-candidate namespace, never overwrite
        # nationality_code or an existing verified manual override.
        chosen[pid]=record
    return chosen,conflicts,dict(unmatched)


def main():
    data=pd.read_parquet(URL)
    required={'display_name','canonical_name','region','source_url'}
    if not required.issubset(data.columns):
        raise ValueError("published schema changed: "+repr(data.columns.tolist()))
    people=json.loads(PEOPLE.read_text(encoding='utf-8'))['people']
    official=json.loads(OVERRIDES.read_text(encoding='utf-8')).get('people',{})
    rows=data.to_dict('records')
    values,conflicts,skipped=reconcile(people,rows,official)
    report=dict(total=len(people),source_rows=len(rows),matched_hints=len(values),
        citizenship_explicit=sum(bool(p.get('nationality_code') or (official.get(p['id']) or {}).get('code'))
                           for p in people),
        missing_country_hints=len(people)-len(values),
        conflicts=conflicts,unmatched_source_breakdown=skipped,
        warning="GPTilt region is NationalityPrimary OR Country; DO NOT treat as verified citizenship.")
    OUTPUT.write_text(json.dumps(dict(
        description="Country hints from Leaguepedia; citizenship NOT independently confirmed",
        source=URL,
        people=values),ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in
                      ('conflicts','unmatched_source_breakdown')},ensure_ascii=False,indent=2))

if __name__=='__main__':
    main()
