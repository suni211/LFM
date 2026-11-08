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

def enrich(person):
    """Non-mutating ID-based country annotation; preserves original source values."""
    p=dict(person)
    row=known().get(p.get('id',''))
    if not row:return p
    if not p.get('nationality_name_ko') and row.get('name'):
        p['nationality_name_ko']=row['name']
    if not p.get('nationality_code') and row.get('code'):
        p['nationality_code']=row['code']
    p['nationality_verified_source']=row.get('source')
    return p
