"""Restore the original viewer's pinned public assets; include all draft images."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,requests,time,shutil
root=Path(__file__).resolve().parents[1];assets=root/'engine'/'assets'
index=json.loads((assets/'champions.json').read_text(encoding='utf-8'));version=index['version']
dd=f'https://ddragon.leagueoflegends.com/cdn/{version}/';cd='https://raw.communitydragon.org/16.21/game/'
jobs=[]
for name in index['data']:
    jobs.extend([(f'champions/{name}.png',dd+f'img/champion/{name}.png'),(f'loading/{name}.jpg',f'https://ddragon.leagueoflegends.com/cdn/img/champion/loading/{name}_0.jpg')])
for item in (1001,3031,3033,3035,3089,3152,3153,3157,3190,3504,4005,3118,3075,3083,6655,3116,3047,3111,3006,3020,3117,3107,3053,3078,3115):jobs.append((f'items/{item}.png',dd+f'img/item/{item}.png'))
for name in ('dragon_infernal','dragon_ocean','dragon_mountain','dragon_cloud','dragon_hextech','dragon_chemtech','dragon_elder','baron','grub','camp','blue','icon_ui_tower_minimap','inhibitor','icon_ui_nexus_minimap_v2'):jobs.append((f'icons/{name}.png',cd+f'assets/ux/minimap/icons/{name}.png'))
for name in ('Flash','Teleport','Dot','Exhaust','Heal','Haste','Barrier','Boost','Smite'):jobs.append((f'summoners/{name}.png',dd+f'img/spell/Summoner{name}.png'))
(assets/'fonts').mkdir(exist_ok=True)
for name in ('Galmuri11.ttf','Galmuri11-Bold.ttf'):shutil.copy2(root/'assets'/name,assets/'fonts'/name)
def fetch(job):
    name,url=job;target=assets/name
    if target.exists() and target.stat().st_size>100:return
    target.parent.mkdir(exist_ok=True,parents=True)
    for attempt in range(3):
        try:
            r=requests.get(url,timeout=30);r.raise_for_status();target.write_bytes(r.content);return
        except requests.RequestException:
            if attempt==2:return name
            time.sleep(attempt+1)
with ThreadPoolExecutor(max_workers=8) as pool:failed=[name for name in pool.map(fetch,jobs) if name]
(assets/'asset-sources.json').write_text(json.dumps(dict(version=version,sources=dict(jobs),failed=failed),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(dict(assets=len(jobs),failed=failed)))
