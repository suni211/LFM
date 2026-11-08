"""Import individually matched player nationalities from Leaguepedia Cargo.

Requires network access to lol.fandom.com and responds to source rate limiting.
DRY-RUN by default. Never infer nationality from region or club.
A nickname match ALONE is insufficient: normalized real names must match too.
"""
import argparse
import datetime
import json
import re
import shutil
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
PEOPLE=ROOT/'assets'/'people.json'
OVERRIDES=ROOT/'assets'/'nationality-overrides.json'
BASE='https://lol.fandom.com/api.php'
COUNTRY={
'KR':('KR','대한민국'),'Korea':('KR','대한민국'),'South Korea':('KR','대한민국'),
'JP':('JP','일본'),'Japan':('JP','일본'),
'CN':('CN','중국'),'China':('CN','중국'),
'TW':('TW','대만'),'Taiwan':('TW','대만'),
'US':('US','미국'),'United States':('US','미국'),
'CA':('CA','캐나다'),'Canada':('CA','캐나다'),
'BR':('BR','브라질'),'Brazil':('BR','브라질'),
'MX':('MX','멕시코'),'Mexico':('MX','멕시코'),
'VN':('VN','베트남'),'Vietnam':('VN','베트남'),
'TH':('TH','태국'),'Thailand':('TH','태국'),
'PH':('PH','필리핀'),'Philippines':('PH','필리핀'),
'ID':('ID','인도네시아'),'Indonesia':('ID','인도네시아'),
'MY':('MY','말레이시아'),'Malaysia':('MY','말레이시아'),
'SG':('SG','싱가포르'),'Singapore':('SG','싱가포르'),
'SE':('SE','스웨덴'),'Sweden':('SE','스웨덴'),
'NO':('NO','노르웨이'),'Norway':('NO','노르웨이'),
'FI':('FI','핀란드'),'Finland':('FI','핀란드'),
'DK':('DK','덴마크'),'Denmark':('DK','덴마크'),
'DE':('DE','독일'),'Germany':('DE','독일'),
'FR':('FR','프랑스'),'France':('FR','프랑스'),
'ES':('ES','스페인'),'Spain':('ES','스페인'),
'PT':('PT','포르투갈'),'Portugal':('PT','포르투갈'),
'GB':('GB','영국'),'United Kingdom':('GB','영국'),'England':('GB','영국'),
'IT':('IT','이탈리아'),'Italy':('IT','이탈리아'),
'PL':('PL','폴란드'),'Poland':('PL','폴란드'),
'CZ':('CZ','체코'),'Czechia':('CZ','체코'),
'TR':('TR','튀르키예'),'Turkey':('TR','튀르키예'),
'NL':('NL','네덜란드'),'Netherlands':('NL','네덜란드'),
'BE':('BE','벨기에'),'Belgium':('BE','벨기에'),
'RU':('RU','러시아'),'Russia':('RU','러시아'),
'UA':('UA','우크라이나'),'Ukraine':('UA','우크라이나'),
'AU':('AU','호주'),'Australia':('AU','호주'),
'NZ':('NZ','뉴질랜드'),'New Zealand':('NZ','뉴질랜드'),
'AR':('AR','아르헨티나'),'Argentina':('AR','아르헨티나'),
'CL':('CL','칠레'),'Chile':('CL','칠레'),
'HK':('HK','홍콩'),'Hong Kong':('HK','홍콩'),
}

def identity(name):
    value=unicodedata.normalize('NFKC',str(name or '')).casefold()
    value=re.sub(r'[^a-z0-9 ]',' ',value)
    return tuple(sorted(value.split()))

def records(page,timeout):
    params=urlencode(dict(action='cargoquery',tables='Players',
        fields='Player,Name,NationalityPrimary',limit=500,offset=page*500,format='json'))
    req=Request(BASE+'?'+params,headers={'User-Agent':'RiftManagerNationalityAudit/1.0 (data reconciliation; contact via project GitHub)'})
    with urlopen(req,timeout=timeout) as response:
        obj=json.load(response)
    if 'error' in obj:raise RuntimeError('Leaguepedia API error: '+str(obj['error']))
    if 'cargoquery' not in obj:raise RuntimeError('Cargo API returned no cargoquery entries')
    return [row['title'] for row in obj['cargoquery']]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--apply',action='store_true',help='write backup and confirmed ID mappings')
    parser.add_argument('--pages',type=int,default=40,help='maximum 500-row Cargo pages')
    parser.add_argument('--timeout',type=int,default=15)
    args=parser.parse_args()
    if not 1<=args.pages<=500:raise SystemExit('pages must be 1..500')
    people=json.loads(PEOPLE.read_text(encoding='utf-8'))['people']
    existing=json.loads(OVERRIDES.read_text(encoding='utf-8'))
    overrides=existing.setdefault('people',{})
    lookup=defaultdict(list)
    for player in people:
        if player.get('real_person') and not player.get('nationality_name_ko') and player['id'] not in overrides:
            lookup[str(player.get('nickname') or '').strip().casefold()].append(player)
    suggestions={}
    scanned=0
    for page in range(args.pages):
        try:batch=records(page,args.timeout)
        except Exception as e:
            print('Source unavailable; ending without guesses:',e)
            break
        if not batch:break
        scanned+=len(batch)
        for item in batch:
            nick=str(item.get('Player') or '').strip()
            real=str(item.get('Name') or '').strip()
            country=str(item.get('NationalityPrimary') or '').strip()
            result=COUNTRY.get(country)
            if not nick or not real or not result:continue
            possible=lookup.get(nick.casefold(),[])
            # Requires a real-name identity match in addition to matching handle.
            matched=[p for p in possible if identity(p.get('real_name')) and identity(p.get('real_name'))==identity(real)]
            if len(matched)!=1:continue
            p=matched[0]
            if p['id'] in suggestions:continue
            code,ko=result
            suggestions[p['id']]=dict(code=code,name=ko,
                source='https://lol.fandom.com/wiki/'+quote(nick.replace(' ','_')),
                verified_on=datetime.date.today().isoformat())
        if len(batch)<500:break
        time.sleep(.25)
    print('Leaguepedia players checked:',scanned)
    print('Identity-verified nationalities:',len(suggestions))
    for p in people:
        if p['id'] in suggestions:
            print(p.get('nickname'),p.get('real_name'),'->',suggestions[p['id']]['name'])
    if not args.apply:
        print('DRY RUN: no changes. Use --apply only after reviewing these matches.')
        return
    if not suggestions:
        print('No verified updates to save.')
        return
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    backup=OVERRIDES.with_name(OVERRIDES.name+'.backup-'+stamp)
    shutil.copy2(OVERRIDES,backup)
    overrides.update(suggestions)
    tmp=OVERRIDES.with_name(OVERRIDES.name+'.tmp')
    tmp.write_text(json.dumps(existing,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(OVERRIDES)
    print('Added',len(suggestions),'verified countries. Backup:',backup)

if __name__=='__main__':main()
