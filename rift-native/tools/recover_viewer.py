"""Recover this project's deleted renderer from recorded source-edit patches."""
from pathlib import Path
import json,re,sys

root=Path(__file__).resolve().parents[1]
kind=sys.argv[1] if len(sys.argv)>1 else 'app'
events=json.loads((root/('deployment-review/recovered-replay-events.json' if kind=='replay' else 'deployment-review/recovered-source-events.json')).read_text(encoding='utf-8'))
source=None;applied=0
for event in events:
    raw=event['raw']
    for match in re.finditer(r'tools\.apply_patch\(',raw):
        try:patch,_=json.JSONDecoder().raw_decode(raw[match.end():])
        except ValueError:continue
        lines=patch.splitlines();i=0
        while i<len(lines):
            line=lines[i]
            if not (line.startswith('*** Add File:') or line.startswith('*** Update File:')) or not line.endswith('/rift-rebuild/'+kind+'.py'):
                i+=1;continue
            add=line.startswith('*** Add File:');i+=1;block=[]
            while i<len(lines) and not lines[i].startswith('*** '):block.append(lines[i]);i+=1
            if add:
                source='\n'.join(s[1:] for s in block if s.startswith('+'))+'\n';applied+=1;continue
            if source is None:raise RuntimeError('missing initial source')
            hunks=[];hunk=[]
            for line in block+['@@']:
                if line.startswith('@@'):
                    if hunk:hunks.append(hunk)
                    hunk=[]
                else:hunk.append(line)
            for hunk in hunks:
                old='\n'.join(s[1:] for s in hunk if s.startswith((' ','-')))
                new='\n'.join(s[1:] for s in hunk if s.startswith((' ','+')))
                if source.count(old)!=1:
                    (root/'deployment-review/recovery-unapplied.patch').write_text(patch,encoding='utf-8')
                    print(f'Skipped nonmatching historical edit at line {event["line"]}; preserved for inspection')
                    continue
                source=source.replace(old,new,1);applied+=1
if source is None:raise RuntimeError('renderer source not found')
target=root/'engine'/('legacy_replay.py' if kind=='replay' else 'legacy_viewer.py');target.write_text(source,encoding='utf-8')
print(f'Recovered {len(source)} characters, {applied} source edits into {target.name}')
