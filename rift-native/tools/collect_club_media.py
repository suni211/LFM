"""Identity-matched official photos, face-only crops and verified team logos."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import collections,hashlib,json,shutil,tempfile,unicodedata,requests,io,threading
import cv2,numpy as np
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'assets';CACHE=ROOT/'tools'/'media-cache'
CATALOG=ASSETS/'people.json';SOURCE='https://lolesports.com/'
def norm(value):return ''.join(c for c in unicodedata.normalize('NFKD',value or '').casefold() if c.isalnum())
def secure(url):return url.replace('http://','https://',1)
def download(url,path):
    if path.exists():return path.read_bytes()
    response=requests.get(secure(url),timeout=30);response.raise_for_status()
    if len(response.content)>12_000_000:raise ValueError('oversized image')
    path.parent.mkdir(exist_ok=True,parents=True);path.write_bytes(response.content);return response.content

def main():
    CACHE.mkdir(exist_ok=True,parents=True);cv2.setNumThreads(1)
    model=CACHE/'face_detection_yunet_2023mar.onnx'
    download('https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx',model)
    # OpenCV's ONNX reader cannot open a non-ASCII path on Windows.
    readable=Path(tempfile.gettempdir())/'rift-face-yunet-2023mar.onnx'
    if not readable.exists() or readable.stat().st_size!=model.stat().st_size:shutil.copyfile(model,readable)
    probe=cv2.FaceDetectorYN.create(str(readable),'',(320,320),.86,.3,1000)
    if probe is None:raise RuntimeError('face detector model did not load')
    del probe
    people=json.loads(CATALOG.read_text(encoding='utf-8'))['people']
    teams=json.loads((ROOT/'tools/esports-source/official-rosters.json').read_text(encoding='utf-8'))['data']['teams']
    by_nick=collections.defaultdict(list);by_team=collections.defaultdict(list)
    for team in teams:
        if team.get('image'):by_team[norm(team['name'])].append(team)
        for player in team.get('players',[]):
            if player.get('image') and not any(s in player['image'].lower() for s in ('placeholder','default-player','player_default')):
                by_nick[norm(player.get('handle'))].append((team,player))
    candidates=[];unmatched=[]
    for person in people:
        rows=by_nick[norm(person.get('nickname',person.get('name','')))];real=norm(person.get('real_name',''))
        exact=[(t,p) for t,p in rows if real and real in (norm((p.get('firstName') or '')+(p.get('lastName') or '')),norm((p.get('lastName') or '')+(p.get('firstName') or '')))]
        same_team=[(t,p) for t,p in rows if norm(t['name'])==norm(person['team'])]
        matches=exact or same_team
        if not matches:unmatched.append({'id':person['id'],'nickname':person['nickname'],'reason':'no_confirmed_official_identity'});continue
        # Prefer the matching club photo when the official source also confirms the name.
        matches.sort(key=lambda pair:norm(pair[0]['name'])!=norm(person['team']))
        t,p=matches[0]
        if not exact and len({p['id'] for _,p in matches})>1:
            unmatched.append({'id':person['id'],'nickname':person['nickname'],'reason':'ambiguous_official_identity'});continue
        candidates.append((person,t,p,'nickname_and_real_name' if exact else 'nickname_and_club'))
    (ASSETS/'portraits').mkdir(exist_ok=True)
    local=threading.local()
    def portrait(job):
        person,team,player,identity=job
        try:
            raw=download(player['image'],CACHE/'people'/(person['id']+'.source'))
            source=Image.open(io.BytesIO(raw));source=ImageOps.exif_transpose(source).convert('RGB')
            if max(source.size)>2000:source.thumbnail((2000,2000),Image.Resampling.LANCZOS)
            detector=getattr(local,'detector',None)
            if detector is None:
                detector=cv2.FaceDetectorYN.create(str(readable),'',(320,320),.86,.3,1000)
                if detector is None:raise RuntimeError('face detector model did not load')
                local.detector=detector
            scale=min(1,800/max(source.size));analysis=source.resize((max(1,round(source.width*scale)),max(1,round(source.height*scale))))
            array=np.ascontiguousarray(cv2.cvtColor(np.asarray(analysis),cv2.COLOR_RGB2BGR))
            detector.setInputSize((analysis.width,analysis.height))
            found=detector.detect(array)
            faces=found[1] if isinstance(found,tuple) else found
            if faces is None or len(faces)==0:raise ValueError('no verified face detected')
            faces=sorted(faces,key=lambda f:f[2]*f[3],reverse=True)
            if len(faces)>1 and faces[1][2]*faces[1][3]>.45*faces[0][2]*faces[0][3]:raise ValueError('multiple comparable faces')
            x,y,w,h=faces[0][:4]/scale;side=max(w,h)*1.35;cx=x+w/2;cy=y+h*.43
            box=(round(cx-side/2),round(cy-side/2),round(cx+side/2),round(cy+side/2))
            # Shift within the original photograph instead of padding or inventing face pixels.
            left=max(0,min(source.width-round(side),box[0]));top=max(0,min(source.height-round(side),box[1]));edge=min(round(side),source.width,source.height)
            image=source.crop((left,top,left+edge,top+edge)).resize((256,256),Image.Resampling.LANCZOS)
            target=ASSETS/'portraits'/(person['id']+'.png');image.save(target,optimize=True)
            return dict(id=person['id'],photo='portraits/'+target.name,photo_source=SOURCE,photo_original_url=secure(player['image']),
                        photo_identity=identity,photo_player_id=player['id'],photo_crop='verified_face_only',photo_retrieved='2026-11-05')
        except Exception as error:
            return dict(id=person['id'],nickname=person['nickname'],reason=type(error).__name__+': '+str(error))
    confirmed=[];failed=[];reported=False
    print(json.dumps({'official_candidates':len(candidates),'unmatched':len(unmatched)}),flush=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        futures=[pool.submit(portrait,job) for job in candidates]
        for n,future in enumerate(as_completed(futures),1):
            result=future.result();(confirmed if 'photo' in result else failed).append(result)
            if 'photo' not in result and not reported:
                reported=True;print(json.dumps({'first_failure':result},ensure_ascii=False),flush=True)
            if n%25==0:print(json.dumps({'processed':n,'faces':len(confirmed),'pending':len(failed)}),flush=True)
    # Re-read before merging to preserve unrelated changes made while fetching photos.
    data=json.loads(CATALOG.read_text(encoding='utf-8'));changes={p['id']:p for p in confirmed}
    for person in data['people']:
        if person['id'] in changes:person.update({k:v for k,v in changes[person['id']].items() if k!='id'})
    temporary=CATALOG.with_suffix('.media.tmp');temporary.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temporary.replace(CATALOG)
    club_assets={};logos_pending=[]
    for league,name in sorted({(p['league'],p['team']) for p in people}):
        matches=by_team[norm(name)]
        if not matches:logos_pending.append({'league':league,'team':name});continue
        matches.sort(key=lambda t:norm((t.get('homeLeague') or {}).get('name',''))!=norm(league));team=matches[0]
        key=hashlib.sha256(json.dumps([league,name],ensure_ascii=False).encode()).hexdigest()[:24]
        try:
            raw=download(team['image'],CACHE/'clubs'/(key+'.source'));image=Image.open(io.BytesIO(raw)).convert('RGBA');image.thumbnail((240,240),Image.Resampling.LANCZOS)
            canvas=Image.new('RGBA',(256,256));canvas.alpha_composite(image,((256-image.width)//2,(256-image.height)//2))
            target=ASSETS/'clubs'/(key+'.png');target.parent.mkdir(exist_ok=True);canvas.save(target,optimize=True)
            club_assets[league+'\n'+name]=dict(league=league,team=name,logo='clubs/'+target.name,source=SOURCE,original_url=secure(team['image']),official_id=team['id'])
        except Exception as error:logos_pending.append(dict(league=league,team=name,reason=str(error)))
    (ASSETS/'club-assets.json').write_text(json.dumps(club_assets,ensure_ascii=False,indent=2),encoding='utf-8')
    report=dict(catalog=len(people),faces=len(confirmed),unmatched=unmatched,photo_pending=failed,logos=len(club_assets),logos_pending=logos_pending)
    (ROOT/'deployment-review/media-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if isinstance(v,int)}),flush=True)

if __name__=='__main__':main()
