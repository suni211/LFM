from pathlib import Path
import json,unicodedata,collections
root=Path('rift-native');path=root/'assets/people.json';data=json.loads(path.read_text(encoding='utf-8'));people=data['people'];teams=json.loads((root/'tools/esports-source/official-rosters.json').read_text(encoding='utf-8'))['data']['teams']
def norm(v):return ''.join(c for c in unicodedata.normalize('NFKD',v or '').casefold() if c.isalnum())
alias={'geng':'gengesports','krx':'kiwoomdrx','nsredforce':'nongshimredforce','cloud9':'cloud9','teamliquid':'teamliquidhonda'}
roles={'top':'TOP','jungle':'JUNGLE','mid':'MID','bottom':'ADC','support':'SUPPORT'}
by=collections.defaultdict(list)
for t in teams:
 for p in t.get('players',[]):by[norm(p.get('handle'))].append((t,p))
updated=0
for p in people:
 if not p.get('real_person'):continue
 name=norm(p.get('team'));real=norm(p.get('real_name'));pairs=by[norm(p.get('nickname'))]
 same=[(t,q) for t,q in pairs if norm(t['name'])==alias.get(name,name)]
 exact=[(t,q) for t,q in pairs if real and real in {norm(q.get('firstName','')+q.get('lastName','')),norm(q.get('lastName','')+q.get('firstName',''))}]
 selected=same or exact
 found={roles[q['role']] for t,q in selected if q.get('role') in roles}
 if len(found)==1 and p.get('kind') not in ('coach','staff'):
  p['role']=found.pop();p['kind']='player';p['role_source']='https://lolesports.com/';updated+=1
# The Korean registration sheet lists the senior roster before developmental registrations.
for team in sorted({p['team'] for p in people if p.get('league')=='LCK'}):
 occupied=set()
 for p in people:
  if p.get('team')!=team or p.get('league')!='LCK' or p.get('kind')!='player':continue
  role=p.get('role')
  if role not in occupied and len(occupied)<5:p['squad']='first';occupied.add(role)
  else:p['squad']='academy';p['squad_source']='GCD registration order; senior positional slots filled'
ko='Faker:페이커,Oner:오너,Doran:도란,Peyz:페이즈,Keria:케리아,Kiin:기인,Canyon:캐니언,Chovy:쵸비,Ruler:룰러,Duro:듀로,Zeus:제우스,Kanavi:카나비,Zeka:제카,Gumayusi:구마유시,Delight:딜라이트,ShowMaker:쇼메이커,Lucid:루시드,Siwoo:시우,Smash:스매시,Career:커리어,PerfecT:퍼펙트,Cuzz:커즈,Bdd:비디디,Jiwoo:지우,Ghost:고스트,Pollu:폴루,DuDu:두두,Pyosik:표식,Clozer:클로저,deokdam:덕담,Peter:피터,Life:라이프,Kingen:킹겐,Sponge:스폰지,Scout:스카웃,Diable:디아블,Lehends:리헨즈,Rich:리치,Ucal:유칼,Aiming:에이밍,Andil:안딜,LazyFeel:레이지필,Clear:클리어,Raptor:랩터,Daystar:데이스타,Slayer:슬레이어,Luon:루온,VicLa:빅라,Kellin:켈린,Teddy:테디,GIDEON:기드온,Roamer:로머,DDahyuk:따혁,Hwichan:휘찬,Haetae:해태,Guardian:가디언,Painter:페인터,Carim:카림,Guti:구티,Cypher:사이퍼,Eclipse:이클립스,Cloud:클라우드,Jinbeom:진범,Ripple:리플,Courage:커리지,Kemish:케미시,MUDAI:무다이,Lumos:루모스,SIRIUSS:시리우스,kkOma:꼬마,Tom:톰,Mata:마타,Easyhoon:이지훈,DooTi:두티,Nagne:나그네,Ryu:류,Chaser:체이서,Thanatos:타나토스,Blaber:블래버,Loki:로키,Tactical:택티컬,Vulcan:벌컨,Impact:임팩트,CoreJJ:코어장전,UmTi:엄티,Yeon:연,Faker:페이커,JackeyLove:재키러브,Knight:나이트,Bin:빈,Elk:엘크,ON:온,Xun:쉰,Wei:웨이,Meiko:메이코,Tian:티안,369:369,Rookie:루키,TheShy:더샤이,Jackal:재칼,Panther:팬서,Cracker:크래커,Valiant:발리언트,Bluffing:블러핑,Wayne:웨인,Nevid:네비드,Loopy:루피,Solid:솔리드,Garden:가든,Jaehyuk:재혁,Taeyoon:태윤,Grizzly:그리즐리,Zephyr:제피르,Kangin:강인,Calix:칼릭스,MihawK:미호크,Lucy:루시,Pleata:플레타,SeTab:세탭,Janus:야누스,Winner:위너,Frog:프로그,Vincenzo:빈센조,Willer:윌러,Minous:미누스,Sylvie:실비,Effort:에포트,Sero:세로,FenRir:펜리르,Tempester:템페스터,OddEye:오드아이,Dinai:디나이,Casting:캐스팅,Namgung:남궁,PlanB:플랜비,Pungyeon:풍연,Sharvel:샤벨,Quantum:퀀텀,Lancer:랜서,Enosh:이노쉬,Flip:플립,Revenge:리벤지'
kn={norm(k):v for k,v in (a.split(':') for a in ko.split(','))}
real={'faker':'이상혁','oner':'문현준','doran':'최현준','peyz':'김수환','keria':'류민석','kiin':'김기인','canyon':'김건부','chovy':'정지훈','ruler':'박재혁','duro':'주민규','zeus':'최우제','kanavi':'서진혁','zeka':'김건우','gumayusi':'이민형','delight':'유환중','showmaker':'허수','lucid':'최용혁','bdd':'곽보성','cuzz':'문우찬','teddy':'박진성','pyosik':'홍창현','dudu':'이동주','aiming':'김하람'}
for p in people:
 n=norm(p.get('nickname'))
 if n in kn:p['nickname_ko']=kn[n]
 if n in real and p.get('region')=='KR':p['real_name_ko']=real[n];p['display_name_ko']=real[n]
 p['identity_type']='real' if p.get('real_person') else 'generated'
path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'official_roles_matched':updated,'korean_nicknames':sum(bool(p.get('nickname_ko')) for p in people),'academy':sum(p.get('squad')=='academy' for p in people)}))
