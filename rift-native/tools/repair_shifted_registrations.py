from pathlib import Path
import csv,json,datetime,re
p=Path('rift-native/assets/people.json');data=json.loads(p.read_text(encoding='utf-8'));lookup={(v['league'],v['team'],v.get('nickname')):v for v in data['people']}
positions={'top':'TOP','jungle':'JUNGLE','jungler':'JUNGLE','mid':'MID','middle':'MID','bot':'ADC','bottom':'ADC','adc':'ADC','support':'SUPPORT','sup':'SUPPORT'}
def parse(v):
 raw=v.strip().casefold();parts=re.split(r'[/ -]+',raw)
 for part in parts:
  if part in positions:return 'player',positions[part]
 if any(term in raw for term in ('coach','analyst','manager','director','physio')):return 'staff' if 'coach' not in raw else 'coach','COACH'
 return None,None
count=0
for row in csv.reader(open('rift-rebuild/runs/gcd-LCP.csv',encoding='utf-8-sig')):
 if len(row)<8:continue
 person=lookup.get((row[0],row[1],row[2]))
 if not person:continue
 kind,role=parse(row[3]);first,last=row[4:6];raw=row[3]
 if not kind:
  kind,role=parse(row[5]);first,last=row[3:5];raw=row[5]
 if kind:
  person.update(kind=kind,role=role,raw_role=raw,real_name=(first+' '+last).strip(),role_source=person['source'],identity_import_revision='lcp-shifted-columns-20261105');count+=1
  if kind in ('coach','staff'):
   person.pop('squad',None)
   person['staff_role']='ANALYST' if 'analyst' in raw.casefold() else 'GM' if 'manager' in raw.casefold() else 'HEAD_COACH' if 'head coach' in raw.casefold() else 'COACH'
 rawdate=row[7].strip()
 try:date=datetime.datetime.strptime(rawdate,'%B %d, %Y').date().isoformat()
 except ValueError:date=None
 person.update(contract_end=date,contract_raw=rawdate,contract_estimated=False)
for person in data['people']:
 raw=(person.get('raw_role') or '').casefold()
 if person.get('kind')=='unclassified' and any(v in raw for v in ('manager','analyst')):
  person.update(kind='staff',role='COACH',staff_role='ANALYST' if 'analyst' in raw else 'GM')
p.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');print('corrected shifted LCP registrations',count)
