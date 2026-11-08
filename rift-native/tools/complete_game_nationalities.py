#!/usr/bin/env python3
"""Fill LFM game-country roster gaps, without requiring citizenship paperwork.

Public nationality roster matches should be imported first. Unresolved players
receive explicit GAME ESTIMATES only; those are not asserted to be real-world
nationality or citizenship, and can be replaced by better person-ID evidence.
Never change an existing country code or overwrite a signed game contract.
"""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
PEOPLE=ROOT/'assets'/'people.json'
OVERRIDES=ROOT/'assets'/'nationality-overrides.json'
REPORT=ROOT/'game-nationality-fill-report.json'

DEFAULT={
    'CBLOL':'BR','Circuito Desafiante':'BR','FLS':'US',
    'LCK':'KR','LCK CL':'KR','LPL':'CN','LDL':'CN',
    'LCP':'TW','LCS':'US','LEC':'ES','LES':'ES',
    'LFL':'FR','LJL':'JP','NACL':'US','PCS':'TW',
    'PRM':'DE','TCL':'TR','VCS':'VN','WildCard':'TH',
}
NAME={
    'KR':'대한민국','BR':'브라질','US':'미국','CN':'중국',
    'TW':'대만','JP':'일본','AR':'아르헨티나','CL':'칠레',
    'PE':'페루','CO':'콜롬비아','VE':'베네수엘라','SE':'스웨덴',
    'AU':'호주','TR':'튀르키예','VN':'베트남','HK':'홍콩',
    'PH':'필리핀','ES':'스페인','PT':'포르투갈','GB':'영국',
    'NO':'노르웨이','DK':'덴마크','GR':'그리스','PL':'폴란드',
    'UA':'우크라이나','RO':'루마니아','BG':'불가리아',
    'FR':'프랑스','FI':'핀란드','EG':'이집트','AM':'아르메니아',
    'DE':'독일','CA':'캐나다','MX':'멕시코','IL':'이스라엘',
}
# Esports-nationality corrections for imports and cross-border competitors.
# Key is (competitive league, nickname). Each existing person ID remains
# independently addressable; duplicate nicknames in different leagues do not mix.
EXCEPTIONS={
 'CBLOL':{
   'CL':'Zothve cody Strensh',
   'KR':'BAO Mireu Keine Trigger Kuri',
   'AR':'Guchi LautaLoval Ackerman Kaze ceo',
   'PE':'Booki Shiku Kouke',
   'CO':'Devost',
   'VE':'STEPZ',
   'SE':'Smiley',
 },
 'Circuito Desafiante':{
   'PE':'Oddie',
   'AU':'Kisee',
 },
 'LCP':{
   'CN':'Shad0w',
   'JP':'Keisuke Ando',
   'KR':'Van1',
   'HK':'Skywalk',
   'AU':'Sheep',
   'VN':'BigKoro LilyMeow',
 },
 'LCS':{
   'PE':'Lyonz',
   'TR':'Gakgos',
   'KR':'Quad Hambak Rahel Zinie Bvoy',
   'PH':'Dayos',
   'AR':'Josedeodo',
 },
 'LEC':{
   'ES':'Gaax Sr_Antonio',
   'BR':'Rodrigo',
   'TR':'Lot',
   'PT':'Rhuckz',
   'GB':'Maxlore',
   'NO':'Lider Hansen',
   'KR':'Hype Way FIESTA',
   'DK':'Hidon',
 },
 'LES':{
   'GR':'Mentos',
   'PT':'Attila Papiteero Gaio',
   'GB':'Dan',
   'UA':'Slayer',
   'PL':'Fresskowy Kozi Escik',
   'TR':'ANDARIEL',
   'FR':'13',
 },
 'LFL':{
   'SE':'Unforg1ven',
   'DK':'Doss Carlsen',
   'BG':'Archfiend Exofeng',
   'TR':'xKenzuke Aetinoth',
   'PT':'Lulas',
   'VN':'Yukino',
   'RO':'Hazel Yakkey',
   'KR':'Piero',
 },
 'LJL':{
   'KR':'DICE Imagine Jubssal Amel Cryo EL PAKA',
   'CN':'ice wanan',
   'TW':'Sai',
   'US':'ReaperBabe JucDuc',
   'DE':'Dopaminw',
 },
 'PCS':{
   'HK':'lazyleung 131 Emoking K_B Micinb RedamnTion ForeverLim ner4 Mogu Tobi BuLuKaKa XDDCC 曾小姐',
   'AU':'jar',
 },
 'PRM':{
   'FI':'Unforgiven Whiteknight',
   'DK':'DenVoksne',
   'NO':'GreenThor',
   'EG':'Boda',
   'AM':'Edward',
   'TR':'White',
 },
}
# User-facing roster names can contain spaces; exact exceptions below supersede
# the whitespace-separated shorthand above.
FULL_NICK_EXCEPTIONS={('LEC','Sr Antonio'):'ES',('PCS','K B'):'HK'}
CODE_BY_NICK={}
for lg, groups in EXCEPTIONS.items():
    for code, nicks in groups.items():
        for nick in nicks.split():
            key=(lg,nick.casefold())
            if key in CODE_BY_NICK and CODE_BY_NICK[key]!=code:
                raise ValueError('Contradictory game override: '+str(key))
            CODE_BY_NICK[key]=code
for (lg,nick),code in FULL_NICK_EXCEPTIONS.items():
    CODE_BY_NICK[(lg,nick.casefold())]=code

def fill(people, existing):
    if len({p['id'] for p in people})!=len(people):
        raise ValueError('duplicate stable person IDs')
    result=dict(existing)
    identities=dict(result.get('people',{}))
    changes=[]
    missing=[]
    counts=Counter()
    for p in people:
        pid=p['id']
        if p.get('nationality_code') or (identities.get(pid) or {}).get('code'):
            continue
        league=p.get('league') or ''
        nick=(p.get('nickname') or '').casefold()
        code=CODE_BY_NICK.get((league,nick)) or DEFAULT.get(league)
        if code not in NAME:
            missing.append({'id':pid,'nickname':nick,'league':league})
            continue
        method='player-specific-game-mapping' if (league,nick) in CODE_BY_NICK else 'league-based-game-default'
        identities[pid]=dict(
            code=code,name=NAME[code],source='LFM game nationality assignment',
            evidence_type='game-estimate',citizenship_verified=False,
            game_estimate=True,identity_match='exact stable person ID',
            origin=method,assigned_on='2026-11-08',
        )
        counts[method]+=1
        changes.append({'id':pid,'league':league,'nickname':nick,'code':code,'origin':method})
    result['people']=identities
    result['game_estimates_separate_from_public_nationality']=True
    report={'total':len(people),
            'with_country':sum(bool(p.get('nationality_code') or identities.get(p['id'],{}).get('code')) for p in people),
            'game_estimate_added':len(changes),
            'specific_mapping_added':counts['player-specific-game-mapping'],
            'regional_game_default_added':counts['league-based-game-default'],
            'missing_after':missing,
            'reassigned_existing':0,
            'note':'Fallbacks are game-only nationality assignments, not assertions about real-world passports or citizenship.'}
    return result,report

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args()
    people=json.loads(PEOPLE.read_text(encoding='utf8'))['people']
    existing=json.loads(OVERRIDES.read_text(encoding='utf8'))
    output,report=fill(people,existing)
    if args.apply:
        OVERRIDES.write_text(json.dumps(output,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if report['missing_after']:
        raise SystemExit('Unmapped game league; examine exact player IDs before release.')
if __name__=='__main__':
    main()
