"""Archive versioned official champion and spell metadata for offline simulation."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import json,time,requests

ROOT=Path(__file__).resolve().parents[1]/'engine'/'assets'
def main():
    index=json.loads((ROOT/'champions.json').read_text(encoding='utf-8'))
    version=index['version']
    target=ROOT/'champion-details';target.mkdir(exist_ok=True)
    def fetch(name):
        output=target/(name+'.json')
        if output.exists():return
        for attempt in range(3):
            try:
                url=f'https://ddragon.leagueoflegends.com/cdn/{version}/data/en_US/champion/{name}.json'
                response=requests.get(url,timeout=35);response.raise_for_status()
                data=response.json();data['source']=url
                output.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8');return
            except requests.RequestException:
                if attempt==2:raise
                time.sleep(attempt+1)
    with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,index['data']))
    print(json.dumps({'version':version,'champions':len(index['data']),'details':len(list(target.glob('*.json')))}))
if __name__=='__main__':main()
