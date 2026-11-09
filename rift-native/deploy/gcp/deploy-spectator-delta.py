"""Apply a reviewed delta to LOL26's existing LFM; preserve users and other services."""
from pathlib import Path
import datetime,hashlib,json,os,shutil,sqlite3,subprocess,sys,time,urllib.request
APP=Path('/opt/lfm');DB=Path('/var/lib/lfm/server.db');STAGE=Path(__file__).resolve().parent
SERVICES=('lfm-api.service','lfm-match-worker.service')
def service(action):subprocess.run(['systemctl',action,*SERVICES],check=True)
def main():
    manifest=json.loads((STAGE/'delta.json').read_text())
    for rel,info in manifest['files'].items():
        target=APP/rel
        if '..' in Path(rel).parts or not target.resolve().is_relative_to(APP):raise RuntimeError('unsafe deploy target')
        if info.get('base') and target.exists() and hashlib.sha256(target.read_bytes()).hexdigest()!=info['base']:
            raise RuntimeError('Production file differs from reviewed GitHub base: '+rel)
        if hashlib.sha256((STAGE/rel).read_bytes()).hexdigest()!=info['sha256']:raise RuntimeError('upload digest mismatch: '+rel)
        if rel.endswith('.py'):compile((STAGE/rel).read_text(encoding='utf-8-sig'),rel,'exec')
    stamp=datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ');backup=Path('/var/lib/lfm/backups')/('engine-stove-'+stamp);backup.mkdir(mode=0o700)
    service('stop')
    dbstat=DB.stat()
    try:
        with sqlite3.connect(DB) as source,sqlite3.connect(backup/'server.db') as target:source.backup(target)
        for rel in manifest['files']:
            target=APP/rel
            if target.exists():
                saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(STAGE/rel,target);os.chmod(target,0o644)
        os.environ['RIFT_DB']=str(DB);os.environ['RIFT_PEOPLE']=str(APP/'assets/people.json');sys.path.insert(0,str(APP/'server'));sys.dont_write_bytecode=True
        import server
        server.init()
        service('start')
        for _ in range(30):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8871/health',timeout=3) as r:health=json.load(r)
                if health['revision']!=manifest['revision']:raise RuntimeError('unexpected deployed revision')
                break
            except OSError:time.sleep(.5)
        else:raise RuntimeError('LFM health unavailable after restart')
        print(json.dumps(dict(deployed=True,backup=str(backup),health=health)))
    except BaseException:
        service('stop')
        for rel in manifest['files']:
            saved=backup/rel;target=APP/rel
            if saved.exists():shutil.copy2(saved,target)
            elif target.exists():target.unlink()
        restore=DB.with_name('spectator-restore.db')
        with sqlite3.connect(backup/'server.db') as source,sqlite3.connect(restore) as target:source.backup(target)
        os.chown(restore,dbstat.st_uid,dbstat.st_gid);os.chmod(restore,dbstat.st_mode&0o777)
        for suffix in ('-wal','-shm'):
            p=Path(str(DB)+suffix)
            if p.exists():p.unlink()
        os.replace(restore,DB);service('start');raise
if __name__=='__main__':main()
