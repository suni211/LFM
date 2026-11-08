"""Versioned spell descriptions and explicit simulation coverage.

Data Dragon describes abilities but does not supply executable game mechanics.
Imported descriptions must never be advertised as fully implemented abilities.
"""
from pathlib import Path
import json,re,html,sys

ROOT=Path(__file__).parent/'assets'
if getattr(sys,'frozen',False):ROOT=Path(sys._MEIPASS)/'engine'/'assets'
def plain(value):return html.unescape(re.sub('<[^>]+>',' ',value or ''))
def load():
    result={}
    for path in sorted((ROOT/'champion-details').glob('*.json')):
        document=json.loads(path.read_text(encoding='utf-8'))
        for key,value in document['data'].items():
            result[key]=dict(value,source=document.get('source'),version=document['version'])
    return result

CATALOG=load()
KO_NAMES={key:entry['name'] for key,entry in json.loads((ROOT/'champions-ko.json').read_text(encoding='utf-8'))['data'].items()}
def display_name(key):return KO_NAMES.get(key,key)
# Role eligibility in this simulator, not claims about current professional meta.
ADC=set('Aphelios Ashe Caitlyn Corki Draven Ezreal Jhin Jinx KaiSa Kalista KogMaw Lucian MissFortune Nilah Samira Senna Sivir Smolder Tristana Twitch Varus Vayne Xayah Zeri'.split())
SUPPORT=set('Alistar Bard Blitzcrank Braum Janna Karma Leona Lulu Milio Morgana Nami Nautilus Neeko Pantheon Pyke Rakan Rell Renata Seraphine Senna Sett Shaco Shen Sona Soraka TahmKench Taric Thresh Velkoz Xerath Yuumi Zilean Zyra'.split())
JUNGLE=set('Amumu Belveth Brand Briar Diana DrMundo Ekko Elise Evelynn Fiddlesticks Graves Gragas Gwen Hecarim Ivern JarvanIV Jax Karthus Kayn Khazix Kindred LeeSin Lillia MasterYi Maokai Morgana Naafiri Nidalee Nocturne Nunu Olaf Pantheon Poppy Qiyana Rammus RekSai Rengar Rumble Sejuani Shaco Shyvana Skarner Sylas Taliyah Talon Trundle Udyr Vi Viego Volibear Warwick Wukong XinZhao Zac Zed Zyra'.split())
TOP=set('Aatrox Akali Akshan Ambessa Aurora Camille Chogath Darius DrMundo Fiora Gangplank Garen Gnar Gragas Gwen Heimerdinger Illaoi Irelia Jax Jayce KSante Kayle Kennen Kled Malphite Maokai Mordekaiser Nasus Olaf Ornn Pantheon Poppy Quinn Renekton Rengar Riven Rumble Ryze Sett Shen Shyvana Singed Sion Swain TahmKench Teemo Trundle Tryndamere Urgot Vayne Vladimir Volibear Warwick Wukong Yasuo Yone Yorick Zac'.split())

def roles_for(key,entry):
    roles=[]
    if key in TOP:roles.append('TOP')
    if key in JUNGLE:roles.append('JUNGLE')
    if ('Mage' in entry['tags'] or 'Assassin' in entry['tags'] or key in {'Lucian','Tristana','Corki','Jayce','Irelia','Yasuo','Yone','Smolder'}):roles.append('MID')
    if key in ADC:roles.append('ADC')
    if key in SUPPORT:roles.append('SUPPORT')
    return tuple(roles or ('TOP',))

def classify(spell):
    text=plain(spell.get('description','')).lower()
    cc=1.2 if any(s in text for s in ('stun','knock up','knocks up','root','charms','fear','suppres')) else .6 if 'slow' in text else 0
    if any(s in text for s in ('invulnerab','cannot die')):family='immune'
    elif 'shield' in text and 'damage' not in text:family='shield'
    elif any(s in text for s in ('heals an','heal an','heals allied','heal all')):family='heal'
    elif 'blink' in text or 'teleports to' in text:family='blink'
    elif any(s in text for s in ('dashes','leaps','lunges')):family='dash'
    elif any(s in text for s in ('fires','shoots','missile','projectile','throws')):family='line'
    elif any(s in text for s in ('surrounding','nearby enemies','area','erupts')):family='aoe'
    elif 'attack speed' in text:family='haste'
    elif 'shield' in text:family='shield'
    elif 'heal' in text:family='drain'
    else:family='target'
    return family,cc

def extend(kits,Kit,keystones):
    for key,entry in CATALOG.items():
        if key in kits:continue
        tags=entry['tags'];stats=entry['stats'];roles=roles_for(key,entry)
        style='ad' if key in ADC else 'tank' if 'Tank' in tags else 'ap' if 'Mage' in tags or 'Support' in tags else 'fighter'
        spells=[]
        for slot,spell in enumerate(entry['spells']):
            family,cc=classify(spell)
            ranges=[r for r in spell.get('range',[]) if isinstance(r,(int,float)) and 0<r<25000]
            reach=(max(ranges) if ranges else 600)*512/14850
            effects=spell.get('effect',[])
            candidates=[row[1] for row in effects if isinstance(row,list) and len(row)>1 and isinstance(row[1],(int,float)) and 30<=row[1]<=600]
            power=(candidates[0] if candidates else (180 if slot==3 else 80))
            if family=='haste':power=.5
            if family=='immune':power=2
            cool=spell.get('cooldown',[90 if slot==3 else 10])[0]
            spells.append((spell['name'],family,power,max(reach,8),max(1,cool),cc))
        build=(3006,3031,3033,3035) if style=='ad' else (3047,3118,3083,3075) if style=='tank' else (3020,6655,3089,3157) if style=='ap' else (3047,3078,3153,3053)
        kits[key]=Kit(entry['name'],roles,style,round(stats['hp']),round(stats['attackdamage']),stats['attackrange'],tuple(spells),build)
        keystones[key]='tempo' if style=='ad' else 'grasp' if style=='tank' else 'electrocute'
    from dataclasses import replace
    for key,kit in list(kits.items()):kits[key]=replace(kit,ko=display_name(key))

def coverage(key):
    entry=CATALOG[key]
    return dict(champion=key,source=entry['source'],version=entry['version'],
                complete=False,passive={'name':entry['passive']['name'],'description':plain(entry['passive']['description']),'status':'not_fully_implemented'},
                spells=[{'slot':'QWER'[i],'name':s['name'],'description':plain(s['description']),'status':'simplified'} for i,s in enumerate(entry['spells'])])
