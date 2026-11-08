#!/usr/bin/env python3
"""Idempotently apply individually identified country/birthplace evidence in-game.

User policy: a sourced country of birth/origin is acceptable in nationality_code.
This is a GAME DISPLAY value; verified citizenship remains distinguished in
evidence_type/citizenship_verified. Never infer origin from league/team/names.
"""
import json
import pathlib

ROOT=pathlib.Path(__file__).resolve().parents[1]
PEOPLE=ROOT/'assets'/'people.json'
HINTS=ROOT/'assets'/'country-hints.json'
OVERRIDES=ROOT/'assets'/'nationality-overrides.json'
REPORT=ROOT/'nationality-merged-report.json'

def combine(people,hints,original):
    by_id={p['id']:p for p in people}
    if len(by_id)!=len(people):raise ValueError('Duplicate person IDs in roster')
    output=dict(original)
    merged=dict(original.get('people',{}))
    created=0
    contradictions=[]
    skipped=0
    for ident,record in hints.items():
        person=by_id.get(ident)
        if not person or not person.get('real_person'):
            skipped+=1;continue
        code=record.get('code')
        source=record.get('source')
        matching=record.get('identity_match')
        if not (isinstance(code,str) and len(code)==2 and code.isalpha()
                and isinstance(source,str) and source.startswith('https://')
                and isinstance(matching,str) and matching.startswith(('exact ','matching '))):
            skipped+=1;continue
        code=code.upper()
        previous=person.get('nationality_code') or merged.get(ident,{}).get('code')
        if previous:
            if previous!=code:
                contradictions.append(dict(id=ident,stored=previous,source_code=code))
            continue
        merged[ident]=dict(code=code,name=record.get('name') or code,
                          source=source,verified_on='2026-11-08',
                          evidence_type='leaguepedia-country-or-birthplace',
                          citizenship_verified=False,identity_match=matching,
                          source_field=record.get('source_field'),
                          dataset_snapshot=record.get('dataset_snapshot'))
        created+=1
    output['people']=merged
    output['country_or_birthplace_accepted']=True
    output['description']=(
      "In-game nationality accepts Leaguepedia country or birthplace when exact"
      " individual identity is established; citizenship_verified:false is"
      " preserved. No nationalities inferred from team, region or name alone."
    )
    covered=sum(bool(p.get('nationality_code') or merged.get(p['id'],{}).get('code'))
                for p in people)
    report=dict(total=len(people),added=created,country_source_hints=len(hints),
                with_country=covered,missing=len(people)-covered,
                original_verified_entries=sum(bool(p.get('nationality_code')) for p in people)
                +sum(bool(x.get('code')) and x.get('citizenship_verified') is not False
                      for x in original.get('people',{}).values()),
                contradictions=contradictions,skipped=skipped)
    if contradictions:
        raise ValueError('Disagreement with an existing documented country: '+
                         json.dumps(contradictions,ensure_ascii=False))
    return output,report

def main():
    people=json.loads(PEOPLE.read_text(encoding='utf-8'))['people']
    hint_data=json.loads(HINTS.read_text(encoding='utf-8'))
    current=json.loads(OVERRIDES.read_text(encoding='utf-8'))
    merged,report=combine(people,hint_data['people'],current)
    OVERRIDES.write_text(json.dumps(merged,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    main()
