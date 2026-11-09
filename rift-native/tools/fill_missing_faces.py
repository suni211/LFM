"""Fill only missing real-player faces after official ID/name/club verification."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,as_completed
import json,unicodedata,collections,io,threading,shutil,tempfile
import requests,numpy as np,cv2
from PIL import Image,ImageOps
ROOT=Path(__file__).resolve().parents[1];ASSETS=ROOT/'assets'
def norm(s):return ''.join(c for c in unicodedata.normalize('NFKD',s or '').casefold() if c.isalnum())
def main():
    cv2.setNumThreads(1)
    data=json.loads((ASSETS/'people.json').read_text(encoding='utf-8'));teams=json.loads((ROOT/'tools/esports-source/official-rosters.json').read_text(encoding='utf-8'))['data']['teams']
    by=collections.defaultdict(list)
    for team in teams:
        for p in team.get('players',[]):by[norm(p.get('handle'))].append((team,p))
    cache=ROOT/'tools'/'face-cache';cache.mkdir(parents=True,exist_ok=True)
    model=cache/'yunet.onnx'
    existing=ROOT.parent.parent/'rift-native/tools/media-cache/face_detection_yunet_2023mar.onnx'
    if existing.exists() and not model.exists():shutil.copyfile(existing,model)
    if not model.exists():
        r=requests.get('https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx',timeout=35);r.raise_for_status();model.write_bytes(r.content)
    readable=Path(tempfile.gettempdir())/'lfm-yunet.onnx';shutil.copyfile(model,readable)
    local=threading.local();jobs=[];pending=[]
    for p in data['people']:
        if not p.get('real_person') or p.get('kind')!='player':continue
        if p.get('photo') and (ASSETS/p['photo']).is_file():continue
        real=norm(p.get('real_name'));rows=by[norm(p.get('nickname'))]
        exact=[(t,q) for t,q in rows if real and real in (norm(q.get('firstName','')+q.get('lastName','')),norm(q.get('lastName','')+q.get('firstName','')))]
        same=[(t,q) for t,q in rows if norm(t['name'])==norm(p.get('team'))]
        matches=exact or same
        identities={q['id'] for t,q in matches}
        if len(identities)!=1:pending.append(dict(id=p['id'],nickname=p.get('nickname'),reason='official identity not confirmed'));continue
        t,q=matches[0];url=q.get('image') or ''
        if not url or any(s in url.lower() for s in ('placeholder','default-player','player_default')):pending.append(dict(id=p['id'],reason='official photo unavailable'));continue
        jobs.append((p,q,url.replace('http://','https://')))
    def run(job):
        p,q,url=job
        try:
            source_file=cache/(p['id']+'.source')
            old=ROOT.parent.parent/'rift-native/tools/media-cache/people'/(p['id']+'.source')
            if not source_file.exists() and old.exists():shutil.copyfile(old,source_file)
            if not source_file.exists():
                r=requests.get(url,timeout=20);r.raise_for_status()
                if len(r.content)>12000000:raise ValueError('oversized image')
                source_file.write_bytes(r.content)
            image=ImageOps.exif_transpose(Image.open(source_file)).convert('RGB');image.thumbnail((1800,1800))
            detector=getattr(local,'detector',None)
            if detector is None:detector=cv2.FaceDetectorYN.create(str(readable),'',(320,320),.80,.3,1000);local.detector=detector
            scale=min(1,800/max(image.size));small=image.resize((round(image.width*scale),round(image.height*scale)));array=np.ascontiguousarray(cv2.cvtColor(np.asarray(small),cv2.COLOR_RGB2BGR));detector.setInputSize(small.size);faces=detector.detect(array)[1]
            if faces is None or not len(faces):raise ValueError('face not detected')
            faces=sorted(faces,key=lambda f:f[2]*f[3],reverse=True)
            if len(faces)>1 and faces[1][2]*faces[1][3]>.45*faces[0][2]*faces[0][3]:raise ValueError('ambiguous multiple faces')
            x,y,w,h=faces[0][:4]/scale;edge=min(round(max(w,h)*1.28),image.width,image.height);left=max(0,min(image.width-edge,round(x+w/2-edge/2)));top=max(0,min(image.height-edge,round(y+h*.43-edge/2)))
            face=image.crop((left,top,left+edge,top+edge)).resize((256,256),Image.Resampling.LANCZOS);target=ASSETS/'portraits'/(p['id']+'.png');face.save(target,optimize=True)
            return p['id'],dict(photo='portraits/'+target.name,photo_source='https://lolesports.com/',photo_original_url=url,photo_player_id=q['id'],photo_crop='verified_face_only',photo_retrieved='2026-11-09')
        except Exception as e:return None,dict(id=p['id'],nickname=p.get('nickname'),reason=str(e))
    index={};print(json.dumps(dict(candidates=len(jobs),unconfirmed=len(pending))),flush=True)
    with ThreadPoolExecutor(max_workers=6) as pool:
        for future in as_completed([pool.submit(run,j) for j in jobs]):
            pid,item=future.result()
            if pid:index[pid]=item
            else:pending.append(item)
    target=ASSETS/'portrait-index.json';previous=json.loads(target.read_text(encoding='utf-8')) if target.exists() else {};previous.update(index);target.write_text(json.dumps(previous,ensure_ascii=False,indent=2),encoding='utf-8')
    report=dict(added=len(index),pending=pending,total_real_players=sum(p.get('real_person') and p.get('kind')=='player' for p in data['people']));(ROOT/'tools'/'face-coverage.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(dict(added=len(index),pending=len(pending))),flush=True)
if __name__=='__main__':main()
