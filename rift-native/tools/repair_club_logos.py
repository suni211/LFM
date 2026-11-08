from pathlib import Path
import json,hashlib,io,requests
from PIL import Image
from concurrent.futures import ThreadPoolExecutor
root=Path(__file__).resolve().parents[1];a=root/'assets';manifest=json.loads((a/'club-assets.json').read_text(encoding='utf-8'));teams=json.loads((root/'tools/esports-source/official-rosters.json').read_text(encoding='utf-8'))['data']['teams'];by={t['slug']:t for t in teams}
alias={'MGN Vikings Esports':'saigon-buffalo-esports','VAREEL YOUTH':'varrel-youth','RED Canids Kalunga':'red-canids','KaBuM! Esports':'kabum-esports','RED Canids Kalunga Academy':'red-academy','Gen.G':'geng','KRX':'drx','NS REDFORCE':'nongshim-redforce','Deep Cross Gaming':'deep-cross-gaming','Cloud9':'cloud9','Team Liquid':'team-liquid','LUA':'lua-gaming','BKR':'bkrog-gamerorigin','ES':'e-shonen','IJC':'ici-japon-corp','JL':'joblife','KCB':'karmine-corp-blue','SC':'skillcamp','VITB':'vitalitybee','ZYB Esport':'zyb','Clocks':'clocks','DetonatioN FocusMe Academy':'detonation-focusme-academy','Ground Zero Academy':'gz-academy','SU Esports':'avella-su-esports','Saigon MVK Academy':'mvke-academy','Saigon Warriors':'saigon-warrior'}
people=json.loads((a/'people.json').read_text(encoding='utf-8'))['people']
jobs=[(league,name,by[alias[name]]) for league,name in sorted(set((p['league'],p['team']) for p in people)) if league+'\n'+name not in manifest and name in alias]
def fetch(job):
 league,name,t=job
 try:
  url=t['image'].replace('http://','https://');r=requests.get(url,timeout=25);r.raise_for_status();im=Image.open(io.BytesIO(r.content)).convert('RGBA');im.thumbnail((240,240));canvas=Image.new('RGBA',(256,256));canvas.alpha_composite(im,((256-im.width)//2,(256-im.height)//2));key=hashlib.sha256(json.dumps([league,name],ensure_ascii=False).encode()).hexdigest()[:24];target=a/'clubs'/(key+'.png');canvas.save(target)
  return league+'\n'+name,dict(league=league,team=name,logo='clubs/'+target.name,source='https://lolesports.com/',original_url=url,official_id=t['id'],official_name=t['name'])
 except Exception as e:return None,dict(team=name,error=str(e))
with ThreadPoolExecutor(max_workers=5) as pool:
 for key,value in pool.map(fetch,jobs):
  if key:manifest[key]=value
  else:print(json.dumps(value))
for item in manifest.values():
 im=Image.open(a/item['logo']).convert('RGBA');pixels=[p for p in im.getdata() if p[3]>128];lum=sum(.2126*p[0]+.7152*p[1]+.0722*p[2] for p in pixels)/max(1,len(pixels));item['background']='#253048' if lum>135 else '#dce3ed'
(a/'club-assets.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');print('logos',len(manifest))
