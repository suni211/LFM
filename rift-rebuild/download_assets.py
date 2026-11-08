"""Pinned public art; the game never downloads assets at runtime."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.request import Request,urlopen
ROOT=Path(__file__).parent/'assets'
NAMES='Alistar Annie Ashe Fiddlesticks Jax Kayle MasterYi Morgana Nunu Ryze Sion Sivir Soraka Teemo Tristana TwistedFate Warwick'.split()
def get(job):
    name,url=job;p=ROOT/name;p.parent.mkdir(parents=True,exist_ok=True)
    if not p.exists():p.write_bytes(urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=40).read())
    return name
def main():
    dd='https://ddragon.leagueoflegends.com/cdn/16.21.1/'
    cd='https://raw.communitydragon.org/16.21/game/'
    jobs=[('map.png',cd+'assets/maps/info/map11/2dlevelminimap_base_baron1.png')]
    jobs += [(f'champions/{n}.png',dd+f'img/champion/{n}.png') for n in NAMES]
    jobs += [(f'items/{i}.png',dd+f'img/item/{i}.png') for i in (1001,1053,3031,3033,3035,3089,3152,3153,3157,3190,3504,4005,3118,3075,3083,6655,3116,3047,3111,3006,3020,3117,3107,3053,3078,3115)]
    jobs += [(f'icons/{n}.png',cd+f'assets/ux/minimap/icons/{n}.png') for n in ('dragon_infernal','dragon_ocean','dragon_mountain','dragon_cloud','dragon_hextech','dragon_chemtech','dragon_elder','baron','grub','camp','blue','icon_ui_tower_minimap','inhibitor','icon_ui_nexus_minimap_v2')]
    jobs += [(f'fonts/{n}',f'https://cdn.jsdelivr.net/npm/galmuri@2.40.3/dist/{n}') for n in ('Galmuri11.ttf','Galmuri11-Bold.ttf','LICENSE.txt')]
    with ThreadPoolExecutor(max_workers=5) as pool:
        for n in pool.map(get,jobs):print(n,flush=True)
if __name__=='__main__':main()
