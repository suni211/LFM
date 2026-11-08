"""Source-verified nationality assignments indexed by stable person ID.

The Riot GCD includes contracts and teams but generally omits citizenship.
Never infer a player's nationality from team, league, spelling, or region.
"""
import json
from functools import lru_cache
from pathlib import Path

FILE=Path(__file__).resolve().parent.parent/'assets'/'nationality-overrides.json'
@lru_cache(maxsize=1)
def known():
    return json.loads(FILE.read_text(encoding='utf-8')).get('people',{}) if FILE.is_file() else {}

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
    row=known().get(p.get('id',''))
    if row:
        if not p.get('nationality_name_ko') and row.get('name'):
            p['nationality_name_ko']=row['name']
        if not p.get('nationality_code') and row.get('code'):
            p['nationality_code']=row['code']
        p['nationality_verified_source']=row.get('source')
        p['nationality_origin']='verified-source'
    elif p.get('real_person') is False and p.get('nationality_name_ko'):
        p['nationality_origin']='fictional-game-profile'
    elif p.get('real_person') and not p.get('nationality_code'):
        country=p.get('nationality_name_ko')
        if country not in COUNTRIES.values():
            p['nationality_pending']=True
    return p
