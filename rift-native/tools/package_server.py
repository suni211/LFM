from pathlib import Path
import tarfile

root=Path(__file__).resolve().parents[1]
target=root/'deployment-review'/'online-api-release.tar.gz'
with tarfile.open(target,'w:gz') as archive:
    for group in ('server','engine'):
        for path in (root/group).rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:continue
            if path.suffix=='.py' or group=='engine' and 'assets' in path.parts:
                archive.add(path,arcname=path.relative_to(root).as_posix())
    archive.add(root/'assets'/'people.json',arcname='assets/people.json')
    for name in ('club-assets.json','club-colors.json'):
        archive.add(root/'assets'/name,arcname='assets/'+name)
    for folder in ('clubs','portraits'):
        for path in (root/'assets'/folder).glob('*'):
            if path.is_file():archive.add(path,arcname=path.relative_to(root).as_posix())
    for path in (root/'web').glob('*'):
        if path.is_file():archive.add(path,arcname=path.relative_to(root).as_posix())
    archive.add(root/'deployment-review'/'deploy_online.py',arcname='deploy_online.py')
print(target)
