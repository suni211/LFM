"""Source-verified nationality assignments indexed by stable person ID.

The Riot GCD includes contracts and teams but generally omits citizenship.
Never infer a player's nationality from team, league, spelling, or region.
"""
import json
from functools import lru_cache
from pathlib import Path

FILE=Path(__file__).resolve().parent.parent/'assets'/'nationality-overrides.json'
COUNTRY_HINTS=Path(__file__).resolve().parent.parent/'assets'/'country-hints.json'
@lru_cache(maxsize=1)
def known():
    return json.loads(FILE.read_text(encoding='utf-8')).get('people',{}) if FILE.is_file() else {}

@lru_cache(maxsize=1)
def country_hints():
    """Unverified country profiles, not suitable for import-quota citizenship."""
    if not COUNTRY_HINTS.is_file():return {}
    return json.loads(COUNTRY_HINTS.read_text(encoding='utf-8')).get('people',{})

# ISO country-code choices for game managers; user-selected nationality is
# self-reported, never inferred from location, employer or league.
COUNTRIES={
    'KR':'대한민국','CN':'중국','JP':'일본','TW':'대만','HK':'홍콩','MO':'마카오',
    'VN':'베트남','TH':'태국','PH':'필리핀','ID':'인도네시아','MY':'말레이시아',
    'SG':'싱가포르','IN':'인도','US':'미국','CA':'캐나다','BR':'브라질',
    'AR':'아르헨티나','MX':'멕시코','CL':'칠레','GB':'영국','FR':'프랑스',
    'DE':'독일','ES':'스페인','PT':'포르투갈','IT':'이탈리아',
    'NL':'네덜란드','BE':'벨기에','DK':'덴마크','SE':'스웨덴','NO':'노르웨이',
    'FI':'핀란드','PL':'폴란드','CZ':'체코','TR':'튀르키예','UA':'우크라이나',
    'RU':'러시아','AU':'호주','NZ':'뉴질랜드','ZA':'남아프리카공화국'
}

def enrich(person):
    """Country is sourced by person ID, not guessed from a team or region."""
    p=dict(person)
    hint=country_hints().get(p.get('id',''))
    if hint and not p.get('nationality_code'):
        p['country_code']=hint['code']
        p['country_name_ko']=hint['name']
        p['country_source']=hint['source']
        p['country_hint']=True
        p['nationality_pending']=True
    row=known().get(p.get('id',''))
    if row:
        if not p.get('nationality_name_ko') and row.get('name'):
            p['nationality_name_ko']=row['name']
        if not p.get('nationality_code') and row.get('code'):
            p['nationality_code']=row['code']
        p['nationality_source']=row.get('source')
        if row.get('citizenship_verified') is False:
            # User explicitly accepts documented country of birth / origin as
            # the in-game nationality. Keep the evidence type transparent.
            p['nationality_origin']='leaguepedia-country-or-birthplace'
            p['nationality_evidence_type']='country-or-birthplace'
            p['nationality_citizenship_verified']=False
        else:
            p['nationality_verified_source']=row.get('source')
            p['nationality_origin']='verified-source'
            p['nationality_evidence_type']='citizenship-or-reported-nationality'
            p['nationality_citizenship_verified']=True
        p.pop('country_hint',None)
        p.pop('nationality_pending',None)
    elif p.get('real_person') is False and p.get('nationality_name_ko'):
        # Fictional source records already specify a game-country label.
        # Turning that existing label into its ISO code is not a claim about
        # a real person's citizenship.
        p['nationality_code']=next((code for code,label in COUNTRIES.items()
            if label==p['nationality_name_ko']),p.get('nationality_code'))
        p['nationality_origin']='fictional-game-profile'
    elif p.get('real_person') and not p.get('nationality_code'):
        country=p.get('nationality_name_ko')
        if country not in COUNTRIES.values():
            p['nationality_pending']=True
    return p
