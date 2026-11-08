"""Bundle assets, deterministic demo and native app without global package edits."""
import enum,typing,pathlib,importlib.metadata as metadata,shutil,sys
from pathlib import Path
from replay import signature,load
def main():
    root=Path(__file__).parent
    assert all('site-packages' not in m.__file__ for m in (enum,typing,pathlib))
    original=metadata.distribution
    def distribution(name):
        if name in ('enum34','typing','pathlib'):raise metadata.PackageNotFoundError(name)
        return original(name)
    metadata.distribution=distribution
    (root/'version.py').write_text(f'SIGNATURE={signature()!r}\n',encoding='utf-8')
    try:
        load(root/'runs/match-1.json.gz');shutil.copy2(root/'runs/match-1.json.gz',root/'assets/demo.json.gz')
    except (OSError,ValueError):
        pass
    import PyInstaller.__main__
    name=sys.argv[1] if len(sys.argv)>1 else 'RiftManager'
    script=sys.argv[2] if len(sys.argv)>2 else 'app.py'
    PyInstaller.__main__.run(['--noconfirm','--onefile','--windowed','--name',name,'--icon',str(root/'assets/rm-logo.ico'),'--distpath','dist','--workpath','build',
                             '--add-data',f'{root/"assets"};assets','--hidden-import','version',script])
if __name__=='__main__':main()
