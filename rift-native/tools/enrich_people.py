from pathlib import Path
import json, urllib.request, urllib.parse, concurrent.futures
from bs4 import BeautifulSoup
root=Path('rift-native')
db=json.loads((root/'assets/people.json').read_text(encoding='utf-8'))
html=BeautifulSoup((root/'tools/t1-lol.html').read_bytes(),'html.parser')
urls={}
for image in html.find_all('img'):
    url=image.get('data-src') or image.get('src','')
    stem=Path(urllib.parse.unquote(urllib.parse.urlsplit(url).path)).stem.lower()
    if url.startswith('https://images.squarespace-cdn.com/'): urls[stem]=url
names={'faker':('이상혁',{'sanghyeoklee','leesanghyeok'}),
       'oner':('문현준',{'hyeonjunmoon','moonhyeonjun'}),
       'doran':('최현준',{'hyeonjoonchoi','choihyeonjoon','hyeonjunchoi','choihyeonjun'}),
       'peyz':('김수환',{'suhwankim','kimsuhwan','soohwankim','kimsoohwan'}),
       'keria':('류민석',{'minseokryu','ryuminseok'})}
def download(person):
    nick=person.get('nickname','').lower()
    if person['team']!='T1' or nick not in names or nick not in urls:return
    korean,variants=names[nick]
    normalized=''.join(c for c in person['real_name'].lower() if c.isalpha())
    if normalized not in variants:return
    target=root/'assets/portraits'/ (person['id']+Path(urllib.parse.urlsplit(urls[nick]).path).suffix)
    with urllib.request.urlopen(urls[nick]+'?format=500w',timeout=25) as response: target.write_bytes(response.read())
    person.update(display_name_ko=korean,nationality_code='KR',nationality_name_ko='대한민국',
                  photo='portraits/'+target.name,photo_source='https://www.t1.gg/teams/leagueoflegends',
                  identity_source='https://www.t1.gg/teams/leagueoflegends')
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(download,db['people']))
(root/'assets/people.json').write_text(json.dumps(db,ensure_ascii=False,indent=2),encoding='utf-8')
print('Matched portraits:',sum(bool(p.get('photo')) for p in db['people']))
