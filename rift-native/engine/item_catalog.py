"""Six-slot purchase plans using the same patch's official item prices/stats."""
import json
from champion_catalog import ROOT

ITEM_DETAILS={int(key):value for key,value in json.loads((ROOT/'items.json').read_text(encoding='utf-8'))['data'].items()}
PLANS={
    'ad':(3006,6672,3031,3085,3033,3072),
    'ap':(3020,6655,3089,3135,3157,4645),
    'fighter':(3047,3078,3053,6333,3065,3153),
    'tank':(3047,3068,3075,3083,6665,2502),
    'support':(3009,4005,6617,3504,3107,6620),
    'support_tank':(3009,3190,3107,3075,3065,3083),
}
def register(kits,items):
    from dataclasses import replace
    for key,kit in list(kits.items()):kits[key]=replace(kit,build=PLANS.get(kit.style,PLANS['fighter']))
    for plan in PLANS.values():
        for item in plan:
            entry=ITEM_DETAILS[item]
            if not entry.get('maps',{}).get('11') or not entry['gold']['purchasable']:
                raise ValueError(f'purchase plan contains unavailable item {item}')
            items[item]=(entry['name'],entry['gold']['total'],'official',0)

def build_for(kit,role):
    if role=='SUPPORT':return PLANS['support_tank' if kit.style in ('tank','fighter') else 'support']
    return kit.build
