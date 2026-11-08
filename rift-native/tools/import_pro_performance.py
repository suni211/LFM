#!/usr/bin/env python3
"""Aggregate observed 2026 professional LoL game results for game rating.

Open statistical dataset: ChainCC (CC BY 4.0) https://chaincc.lol/free/data
All saved figures are retrospective pro-match results (not salary disclosures).
Join only when a competitive nickname is unique in the local roster AND role
is consistent. Otherwise leave it unmatched; never create fictional matches.
"""
import json
import math
import pathlib
import re
import unicodedata
from collections import Counter, defaultdict

import pandas as pd

ROOT=pathlib.Path(__file__).resolve().parents[1]
INPUT=ROOT/'assets'/'people.json'
OUTPUT=ROOT/'assets'/'pro-performance-2026.json'
REPORT=ROOT/'pro-performance-2026-report.json'
DATA_URL='https://chaincc.lol/data/chaincc-players-2026.csv.gz'

ROLES={'top':'TOP','jng':'JUNGLE','jungle':'JUNGLE',
       'mid':'MID','middle':'MID','bot':'ADC','bottom':'ADC','adc':'ADC',
       'sup':'SUPPORT','support':'SUPPORT','utility':'SUPPORT'}

def norm(value):
    text=unicodedata.normalize('NFKD',str(value or ''))
    return ''.join(c.casefold() for c in text
                   if c.isalnum() and not unicodedata.combining(c))

def resolve(columns,options,required=True):
    keys={norm(x):x for x in columns}
    for candidate in options:
        if norm(candidate) in keys:return keys[norm(candidate)]
    if required:raise ValueError('Column missing ('+', '.join(options)+'); actual='+', '.join(columns))
    return None

def numeric(row,key,default=0):
    if not key:return default
    v=row.get(key)
    try:
        x=float(v)
        return x if math.isfinite(x) else default
    except (ValueError,TypeError):return default

def parse_win(value):
    if value is None:return None
    value=str(value).strip().lower()
    if value in ('1','1.0','true','win','w','yes'):return 1
    if value in ('0','0.0','false','loss','l','no'):return 0
    return None

def generate(people,df):
    column=df.columns.tolist()
    alias={
        'nick':resolve(column,['playername','player_name','player','summonername','ign','player_name_original']),
        'role':resolve(column,['position','role','pos']),
        'win':resolve(column,['result','win','won','victory']),
        'kills':resolve(column,['kills','kill']),
        'deaths':resolve(column,['deaths','death']),
        'assists':resolve(column,['assists','assist']),
        'dpm':resolve(column,['dpm','damage_per_minute','damageperminute','damagetochampionsperminute'],False),
        'team':resolve(column,['teamname','team_name','team'],False),
        'league':resolve(column,['league','league_name','competition'],False),
    }
    names=defaultdict(list)
    for p in people:
        if p.get('kind')=='player' and p.get('real_person') and p.get('nickname'):
            names[norm(p['nickname'])].append(p)
    aggregates=defaultdict(lambda:dict(games=0,wins=0,kills=0,deaths=0,assists=0,dpm=0,dpm_games=0,teams=Counter()))
    role_dpm=defaultdict(list)
    excluded=Counter()
    for row in df.to_dict('records'):
        key=norm(row.get(alias['nick']))
        role=ROLES.get(norm(row.get(alias['role'])))
        if not role:
            excluded['invalid-role']+=1;continue
        candidates=[p for p in names.get(key,[]) if p.get('role')==role]
        if len(candidates)!=1:
            excluded['nickname-ambiguous-or-missing']+=1;continue
        player=candidates[0]
        win=parse_win(row.get(alias['win']))
        if win is None:
            excluded['no-result']+=1;continue
        k,d,a=[numeric(row,alias[t]) for t in ('kills','deaths','assists')]
        if min(k,d,a)<0:
            excluded['invalid-kda']+=1;continue
        result=aggregates[player['id']]
        result['games']+=1
        result['wins']+=win
        result['kills']+=k;result['deaths']+=d;result['assists']+=a
        damage=numeric(row,alias['dpm'],-1)
        if damage>=0:
            result['dpm']+=damage;result['dpm_games']+=1
            role_dpm[role].append(damage)
        if alias['team'] and row.get(alias['team']):
            result['teams'][str(row[alias['team']])]+=1
    means={}
    for role,values in role_dpm.items():
        means[role]=sum(values)/len(values) if values else 0
    by_id={p['id']:p for p in people}
    out={}
    for pid,item in aggregates.items():
        played=item['games']
        if played<4:continue
        wr=item['wins']/played
        kda=(item['kills']+item['assists'])/max(1,item['deaths'])
        role=by_id[pid].get('role')
        avg_dpm=item['dpm']/item['dpm_games'] if item['dpm_games'] else None
        benchmark=means.get(role,0)
        damage_adjustment=0 if avg_dpm is None or benchmark<=0 else (
            max(-1.5,min(1.5,(avg_dpm/benchmark-1)*2.2)))
        # Actual result sample, role-normalized damage; no claim of
        # predictive validity or independent player "skill" measurement.
        raw=50+26*(wr-.5)+8*math.tanh((kda-3)/3)+7*damage_adjustment
        normalized=max(25,min(90,round(50+(raw-50)*played/(played+12),1)))
        out[pid]=dict(games=played,wins=item['wins'],win_rate=round(wr,3),
            kills=round(item['kills']/played,2),
            deaths=round(item['deaths']/played,2),
            assists=round(item['assists']/played,2),
            kda=round(kda,2),dpm=round(avg_dpm,1) if avg_dpm is not None else None,
            performance=normalized,
            sample='2026 professional match results',
            matched_team=item['teams'].most_common(1)[0][0] if item['teams'] else None,
            identity_check='unique competitive nickname and exact role')
    report=dict(roster_count=len(people),matched_players=len(out),
                observed_games=sum(x['games'] for x in out.values()),
                excluded=dict(excluded),source_columns=alias,
                note='Performance and game salaries are fictional evaluation, based on observed results. No actual salaries are disclosed.')
    return out,report

def main():
    df=pd.read_csv(DATA_URL,compression='gzip',low_memory=False)
    people=json.loads(INPUT.read_text(encoding='utf8'))['people']
    out,report=generate(people,df)
    if not out:
        raise RuntimeError('No attributable pro match data; refusing empty import')
    OUTPUT.write_text(json.dumps(dict(
        description='CC BY 4.0 ChainCC 2026 pro match dataset; aggregate game evidence only',
        attribution='ChainCC. League of Legends esports match dataset. https://chaincc.lol/free/data',
        people=out),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True)

if __name__=='__main__':
    main()
