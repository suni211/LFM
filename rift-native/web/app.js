const BASE = location.pathname.startsWith('/rift') ? '/rift' : ''
const NAV = [
  ['홈', '/app/home', '경기'],
  ['운영 대시보드', '/app/operator', '운영'],
  ['우편', '/app/inbox', '경기'],
  ['뉴스', '/app/news', '경기'],
  ['1군', '/app/squad', '선수단'],
  ['2군', '/app/academy', '선수단'],
  ['전술', '/app/tactics', '선수단'],
  ['훈련', '/app/training', '선수단'],
  ['프런트', '/app/staff', '구단'],
  ['프런트 DB', '/app/front-database', '구단'],
  ['의료', '/app/medical', '선수단'],
  ['관계', '/app/relations', '선수단'],
  ['일정', '/app/schedule', '대회'],
  ['역사관', '/app/history', '대회'],
  ['리그', '/app/leagues', '대회'],
  ['선수 DB', '/app/players', '대회'],
  ['솔로랭크', '/app/solo', '대회'],
  ['이적', '/app/transfers', '영입'],
  ['영입 명단', '/app/shortlist', '영입'],
  ['재정', '/app/finance', '구단'],
  ['데이터', '/app/data', '구단'],
  ['스폰서', '/app/sponsors', '구단'],
  ['비전', '/app/vision', '구단'],
  ['커뮤니티', '/app/community', '구단']
]
const WIDGETS = {cash:'현금 흐름',
  news: '뉴스', inbox: '우편', standings: '리그 순위', next: '다음 경기', squad: '선수단',
  budget: '이적 예산', wages: '급여', schedule: '일정', staff: '스태프', medical: '의료',
  board: '구단주·팬', form: '최근 경기'
}
const ROLE = {TOP:'탑', JUNGLE:'정글', MID:'미드', ADC:'원딜', SUPPORT:'서포터'}
let media = {colors:{}, logos:{}, brandings:null,academyParents:{},leagueLogos:{}}
let careerCache = null
let managerProfile = null
let isOperator = false
let worldState = null

const CHAMP_PATCH='16.22.1'
let championMeta={}
let championFetch=null
async function loadChampionMeta(){
 if(championFetch)return championFetch
 championFetch=fetch('https://ddragon.leagueoflegends.com/cdn/'+CHAMP_PATCH+'/data/ko_KR/champion.json')
  .then(r=>{if(!r.ok)throw Error('Riot champion list unavailable');return r.json()})
  .then(d=>{championMeta=d.data||{};return championMeta})
  .catch(()=>{championMeta={};return championMeta})
 return championFetch
}
function championKo(id){return championMeta[id]?.name||id}
function championIcon(id){
 const name=String(id||'')
 if(!/^[A-Za-z0-9]{2,30}$/.test(name))return ''
 const filename=championMeta[name]?.image?.full||name+'.png'
 return '<img class="champion-icon" alt="'+esc(championKo(name))+'" loading="lazy" src="https://ddragon.leagueoflegends.com/cdn/'+CHAMP_PATCH+'/img/champion/'+encodeURIComponent(filename)+'" onerror="this.hidden=true"/>'
}


function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))
}

const FLAG_COUNTRIES={
  '대한민국':['kr','대한민국'],'한국':['kr','대한민국'],'KR':['kr','대한민국'],'KOR':['kr','대한민국'],'Korea':['kr','대한민국'],'South Korea':['kr','대한민국'],
  '중국':['cn','중국'],'CN':['cn','중국'],'CHN':['cn','중국'],'China':['cn','중국'],
  '일본':['jp','일본'],'JP':['jp','일본'],'JPN':['jp','일본'],'Japan':['jp','일본'],
  '대만':['tw','대만'],'TW':['tw','대만'],'Taiwan':['tw','대만'],
  '베트남':['vn','베트남'],'VN':['vn','베트남'],'Vietnam':['vn','베트남'],
  '홍콩':['hk','홍콩'],'HK':['hk','홍콩'],'Hong Kong':['hk','홍콩'],
  '필리핀':['ph','필리핀'],'PH':['ph','필리핀'],'Philippines':['ph','필리핀'],
  '태국':['th','태국'],'TH':['th','태국'],'Thailand':['th','태국'],
  '인도네시아':['id','인도네시아'],'ID':['id','인도네시아'],'Indonesia':['id','인도네시아'],
  '말레이시아':['my','말레이시아'],'MY':['my','말레이시아'],'Malaysia':['my','말레이시아'],
  '싱가포르':['sg','싱가포르'],'SG':['sg','싱가포르'],'Singapore':['sg','싱가포르'],
  '미국':['us','미국'],'US':['us','미국'],'USA':['us','미국'],'United States':['us','미국'],
  '캐나다':['ca','캐나다'],'CA':['ca','캐나다'],'Canada':['ca','캐나다'],
  '브라질':['br','브라질'],'BR':['br','브라질'],'Brazil':['br','브라질'],
  '아르헨티나':['ar','아르헨티나'],'AR':['ar','아르헨티나'],'Argentina':['ar','아르헨티나'],
  '멕시코':['mx','멕시코'],'MX':['mx','멕시코'],'Mexico':['mx','멕시코'],
  '영국':['gb','영국'],'GB':['gb','영국'],'UK':['gb','영국'],'United Kingdom':['gb','영국'],
  '프랑스':['fr','프랑스'],'FR':['fr','프랑스'],'France':['fr','프랑스'],
  '독일':['de','독일'],'DE':['de','독일'],'Germany':['de','독일'],
  '스페인':['es','스페인'],'ES':['es','스페인'],'Spain':['es','스페인'],
  '이탈리아':['it','이탈리아'],'IT':['it','이탈리아'],'Italy':['it','이탈리아'],
  '포르투갈':['pt','포르투갈'],'PT':['pt','포르투갈'],'Portugal':['pt','포르투갈'],
  '덴마크':['dk','덴마크'],'DK':['dk','덴마크'],'Denmark':['dk','덴마크'],
  '스웨덴':['se','스웨덴'],'SE':['se','스웨덴'],'Sweden':['se','스웨덴'],
  '폴란드':['pl','폴란드'],'PL':['pl','폴란드'],'Poland':['pl','폴란드'],
  '체코':['cz','체코'],'CZ':['cz','체코'],'Czechia':['cz','체코'],
  '튀르키예':['tr','튀르키예'],'터키':['tr','튀르키예'],'TR':['tr','튀르키예'],'Turkey':['tr','튀르키예'],
  '러시아':['ru','러시아'],'RU':['ru','러시아'],'Russia':['ru','러시아'],
  '우크라이나':['ua','우크라이나'],'UA':['ua','우크라이나'],'Ukraine':['ua','우크라이나'],
  '호주':['au','호주'],'AU':['au','호주'],'Australia':['au','호주'],
  '뉴질랜드':['nz','뉴질랜드'],'NZ':['nz','뉴질랜드'],'New Zealand':['nz','뉴질랜드']
}
function flagAndCountry(person) {
  const p=person||{}
  const raw=String(p.nationality_name_ko||p.nationality_name||p.country_name_ko||p.country_name||(typeof p.nationality==='string'?p.nationality:'')||'').trim()
  const rawCode=String(p.nationality_code||p.country_code||p.iso2||'').trim()
  const entry=FLAG_COUNTRIES[raw]||FLAG_COUNTRIES[rawCode]
  const code=entry?.[0]||(/^[A-Za-z]{2}$/.test(rawCode)?rawCode.toLowerCase():null)
  const name=(raw||entry?.[1]||'국적 미등록')+(p.country_hint&&!p.nationality_code?' · 국적 확인 필요':'')
  const image=code?'<img class="country-flag" loading="lazy" width="24" height="16" src="https://flagcdn.com/w40/'+code+'.png" alt="'+esc(name)+' 국기" onerror="this.hidden=true"/>':''
  return '<span class="country-badge">'+image+'<span>'+esc(name)+'</span></span>'
}

function money(value) { return value == null ? '기록 없음' : Number(value).toLocaleString('ko-KR') + '원' }
function token() { return localStorage.getItem('rift-token') || '' }
function careerId() { return Number(localStorage.getItem('rift-career') || 0) }
async function api(path, body) {
  const headers = {Accept:'application/json'}
  if (token()) headers.Authorization = 'Bearer ' + token()
  const response = await fetch(BASE + (BASE ? '/api' : '') + path, body == null ? {headers} : {method:'POST', headers:{...headers, 'Content-Type':'application/json'}, body:JSON.stringify(body)})
  const data = await response.json().catch(() => ({error:'응답을 읽지 못했습니다'}))
  if (response.status === 401 && path !== '/login' && path !== '/register') { localStorage.removeItem('rift-token'); location.href = BASE + '/' }
  if (!response.ok) { const errors={'invalid credentials':'계정 이름 또는 비밀번호를 확인하세요.','account name already exists':'이미 사용 중인 계정 이름입니다.','password must be 10 to 128 characters':'비밀번호는 10~128자로 입력하세요.','account name must be 1 to 30 characters':'계정 이름은 1~30자로 입력하세요.','endpoint not found':'해당 기능의 연결 주소를 찾을 수 없습니다.'};throw new Error(errors[data.error] || data.error || '요청을 처리하지 못했습니다.') }
  return data
}
function face(id, available=true) {
  const silhouette='<svg class="portrait-person-svg" viewBox="0 0 64 64" aria-hidden="true" fill="none"><circle cx="32" cy="23" r="13" fill="currentColor" opacity=".78"/><path d="M8 59c0-13 10-22 24-22s24 9 24 22" fill="currentColor" opacity=".58"/></svg>'
  const fallback='<span class="face-placeholder" aria-label="등록된 얼굴 사진 없음">'+silhouette+'</span>'
  if (!available) return '<span class="face-frame">'+fallback+'</span>'
  return '<span class="face-frame"><img class="face" alt="선수 얼굴" src="'+BASE+'/media/portraits/'+esc(id)+'.png" onerror="this.hidden=true;this.nextElementSibling.hidden=false"/><span class="face-placeholder" hidden aria-label="등록된 얼굴 사진 없음">'+silhouette+'</span></span>'
}
function logoImg(league, team, overrideBrand=null) {
  const original=league+'\n'+team
  const key=media.academyParents?.[original]||original
  const brand=overrideBrand||media.brandings?.[key]
  const alt=esc(team||'구단')
  // Uploaded or official club image is the representative identity.
  // A selected shield/star/other emblem is strictly a last fallback.
  const uploaded=brand?.logo_data
  if(typeof uploaded==='string'&&uploaded.length<=110000&&/^data:image\/(png|jpeg|webp);base64,[a-zA-Z0-9+/=]+$/.test(uploaded))
    return `<img class="logo club-primary-image" alt="${alt} 구단 로고" src="${esc(uploaded)}"/>`
  const item=media.logos?.[key]
  if(item?.logo)
    return `<img class="logo club-primary-image" alt="${alt} 구단 로고" style="background:${esc(item.background||'#dce3ed')}" src="${BASE}/media/${esc(item.logo)}"/>`
  const symbol={shield:'⬡',star:'★',crown:'♛',bolt:'ϟ',diamond:'◆'}[brand?.emblem]
  const abbreviation=brand?.short||(team||'RM').slice(0,2)
  const color=typeof brand?.color==='string'&&/^#[0-9a-fA-F]{6}$/.test(brand.color)?brand.color:'#17324d'
  return `<span class="club-monogram club-emblem-fallback" style="background:${esc(color)};color:#fff" aria-label="${alt} 구단 로고 대체"><span class="club-emblem-symbol" aria-hidden="true">${symbol||''}</span><span>${esc(abbreviation)}</span></span>`
}
function careerLogo(careerItem) {
  return logoImg(careerItem?.club_profile?.league||'',careerItem?.name||'',careerItem?.branding||null)
}
const LEAGUE_INFO={
 'LCK':['🇰🇷','대한민국','1부','kr'],'LCK CL':['🇰🇷','대한민국','2부','kr'],
 'LPL':['🇨🇳','중국','1부','cn'],'LDL':['🇨🇳','중국','2부','cn'],
 'LCS':['🇺🇸','북미','1부','na'],'NACL':['🇺🇸','북미','2부','na'],
 'LEC':['🇪🇺','유럽','1부','eu'],'LFL':['🇫🇷','프랑스','2부','eu'],
 'LES':['🇪🇸','스페인','2부','eu'],'PRM':['🇩🇪','독일','2부','eu'],
 'TCL':['🇹🇷','튀르키예','2부','eu'],'CBLOL':['🇧🇷','브라질','1부','br'],
 'Circuito Desafiante':['🇧🇷','브라질','2부','br'],
 'LCP':['🌏','아시아 태평양','1부','apac'],
 'PCS':['🌏','아시아 태평양','2부','apac'],
 'LJL':['🇯🇵','일본','2부','jp'],'VCS':['🇻🇳','베트남','2부','vn']
}
function leagueInfo(league){return LEAGUE_INFO[league]||['🏆','지역 리그','리그','general']}
function leagueIcon(league){
 const [flag,region,level,tone]=leagueInfo(league)
 const item=media.leagueLogos?.[league]
 const known=item&&/^https:\/\/commons\.wikimedia\.org\/wiki\/Special:FilePath\//.test(item.url)
 const logo=known?'<img class="league-official-mark" loading="lazy" src="'+esc(item.url)+'" alt="'+esc(league)+' 대회 로고" onerror="this.hidden=true;this.nextElementSibling.hidden=false"/><span class="league-emblem-fallback" hidden>'+esc(league)+'</span>':
  '<span class="league-emblem-flag">'+flag+'</span><strong>'+esc(league.length>8?league.slice(0,3).toUpperCase():league)+'</strong>'
 return '<span class="league-emblem league-emblem-'+tone+'" title="'+esc(region+' '+level)+'">'+logo+'</span>'
}
function displayTeam(league,team){return media.brandings?.[league+'\n'+team]?.display_name||team}
function teamColor(league, team) { return media.colors[league + '\n' + team] || '#17324d' }
function go(href) { history.pushState({}, '', BASE && !href.startsWith(BASE + '/') ? BASE + href : href); draw() }
async function career() {
  if (!careerCache || careerCache.id !== careerId()) {
    const data = await api('/careers')
    careerCache = data.careers.find(item => item.id === careerId()) || data.careers[0] || null
    if (careerCache) localStorage.setItem('rift-career', careerCache.id)
  }
  return careerCache
}
function shell(body,path) {
  const categories=[['구단',['home','inbox','news','finance','vision','community','staff','front-database','sponsors']],['선수단',['squad','academy','medical','relations','players','solo']],['전술·훈련',['tactics','training']],['영입',['transfers','shortlist']],['리그·경기',['schedule','leagues','history','data']],...(isOperator?[['운영',['operator','clubs']]]:[])]
  const selected=NAV.find(n=>n[1]===path)?.[0]||'구단 관리'
  const menu=categories.map(([label,keys])=>`<details class="nav-category"><summary>${label}<span>⌄</span></summary><div class="dropdown">${keys.map(key=>{const item=NAV.find(n=>n[1]==='/app/'+key)||[key==='clubs'?(isOperator?'구단 조회':'구단 선택'):key,'/app/'+key];return `<a href="${item[1]}" class="${path===item[1]?'on':''}">${item[0]}</a>`}).join('')}</div></details>`).join('')
  document.getElementById('app').innerHTML=`<div id="shell"><header id="masthead"><div id="top"></div><nav id="navigation"><a class="brand" href="/app/home">R/M<span>RIFT MANAGER</span></a>${menu}${isOperator?'<span class="account-link">운영자 · 관전 모드</span>':'<a class="account-link" href="/app/manager">감독 프로필</a>'}<button id="logout" aria-label="로그아웃">로그아웃</button></nav></header><main id="view" aria-label="${esc(selected)}">${body}</main></div>`
  document.getElementById('logout').onclick=()=>{localStorage.removeItem('rift-token');localStorage.removeItem('rift-career');careerCache=null;location.href=BASE+'/'}
}
async function topbar() {
  const current=await career();const world=await api('/world');const bar=document.getElementById('top');if(!bar)return
  const league=current?.club_profile?.league||'',name=current?displayTeam(league,current.name):(isOperator?'리그 운영':'구단 선택')
  document.documentElement.style.setProperty('--team',teamColor(league,name))
  const fixtures=current?(await api('/fixtures?id='+current.id)).fixtures:[]
  const due=(fixtures||[]).find(g=>g.state==='queued')
  bar.innerHTML=`<div class="club-identity">${current?careerLogo(current):logoImg(league,name)}<div><b>${esc(name)}</b><small>${esc(league)} · 온라인 리그</small></div></div><div class="search-wrap"><label class="sr-only" for="global-search">통합 검색</label><input id="global-search" placeholder="선수, 스태프, 구단 검색" autocomplete="off"/><div id="search-results" hidden></div></div><div class="week"><small>현재 시즌</small><b>${world.season}시즌 ${world.week}주차</b></div>${isOperator?'<button class="continue" id="operator-advance">다음 주 진행 <span>❯❯</span></button>':due?'<button class="continue" id="play-match">경기 진행 <span>❯❯</span></button>':'<button class="continue" disabled title="다음 주차와 시즌 변경은 운영자만 가능합니다.">운영자 턴 진행 대기</button>'}`
  if(isOperator)document.getElementById('operator-advance').onclick=async()=>{
    if(!confirm(world.season+'시즌 '+world.week+'주차를 완료하고 모든 구단을 다음 주로 진행할까요?'))return
    const b=document.getElementById('operator-advance');if(b)b.disabled=true
    try{await api('/operator/advance',{version:world.version});careerCache=null;worldState=null;await draw()}
    catch(e){alert(e.message);if(b)b.disabled=false}
  }
  if(!isOperator&&due)document.getElementById('play-match').onclick=()=>go('/app/match/'+due.id)
  const input=document.getElementById('global-search'),results=document.getElementById('search-results');let generation=0,timer
  input.oninput=()=>{const g=++generation;clearTimeout(timer);results.hidden=true;const q=input.value.trim();if(!q)return;timer=setTimeout(async()=>{try{const data=await api('/search?query='+encodeURIComponent(q));if(g!==generation||!results.isConnected)return;results.innerHTML=(data.results||[]).map(item=>{const href=item.kind==='team'?'/app/team/'+encodeURIComponent(item.league)+'/'+encodeURIComponent(item.team):item.kind==='manager'||item.kind==='owner'?'/app/entity/'+item.kind+'/'+encodeURIComponent(item.id):'/app/player/'+encodeURIComponent(item.id);return `<a href="${href}"><b>${esc(item.label)}</b><small>${esc(item.subtitle)}</small></a>`}).join('')||'<p>검색 결과가 없습니다.</p>';results.hidden=false}catch(e){if(g===generation){results.innerHTML='<p>검색을 다시 시도해 주세요.</p>';results.hidden=false}}},180)}
  input.onkeydown=e=>{if(e.key==='Escape')results.hidden=true};input.onblur=()=>setTimeout(()=>{results.hidden=true},160)
}
function login() {
  document.getElementById('app').innerHTML = `<div class="entry"><section class="entry-story"><span class="entry-mark">R/M · CAREER MODE</span><h1>당신의 팀.<br><em>당신의 역사.</em></h1><p>하부 리그의 작은 구단에서 출발해 국제 무대까지 올라가세요.</p><div class="entry-facts"><span>150 WEEKS / SEASON</span><span>CLUB MANAGEMENT</span><span>ONLINE CAREER</span></div></section><form class="login" id="gate"><small>MANAGER ACCESS</small><h1>RIFT MANAGER</h1><p>감독 계정을 만들고 커리어를 시작하세요.</p><p class="err" id="err" role="alert"></p><label for="name">계정 이름</label><input id="name" autocomplete="username" maxlength="30" required placeholder="계정 ID"/><label for="password">비밀번호 · 10~128자</label><input id="password" type="password" autocomplete="current-password" minlength="10" maxlength="128" required placeholder="비밀번호"/><div class="entry-actions"><button class="act" type="button" id="in">로그인</button><button class="act" type="button" id="up">새 감독 계정 만들기</button></div><small>감독 닉네임은 가입 후 영문 2~20자로 설정합니다.</small></form></div>`
  let submitting=false
  const send = async (path) => {
    if(submitting || !document.getElementById('gate').reportValidity())return
    submitting=true;document.querySelectorAll('#gate button').forEach(b=>b.disabled=true)
    try {
      const result = await api(path, {name:document.getElementById('name').value.trim(), password:document.getElementById('password').value})
      localStorage.setItem('rift-token', result.token)
      localStorage.setItem('rift-name', document.getElementById('name').value.trim())
      careerCache=null;managerProfile=null;localStorage.removeItem('rift-career');go('/app')
    } catch (error) { const el=document.getElementById('err');if(el)el.textContent=error.message } finally {submitting=false;document.querySelectorAll('#gate button').forEach(b=>b.disabled=false)}
  }
  document.getElementById('gate').onsubmit=event=>{event.preventDefault();send('/login')}
  document.getElementById('in').onclick = event => { event.preventDefault(); send('/login') }
  document.getElementById('up').onclick = event => { event.preventDefault(); send('/register') }
}
async function continueCareer() {
  const mine=await api('/careers')
  if(!mine.careers.length) return go('/app/clubs')
  const selected=mine.careers.find(c=>c.id===careerId())||mine.careers[0]
  localStorage.setItem('rift-career',selected.id)
  const league=selected.club_profile?.league||''
  let position='순위 집계 전'
  try {
    const result=await api('/dashboard?id='+selected.id)
    const mineRow=(result.standings||[]).find(row=>row.team===selected.name)
    if(mineRow)position=mineRow.rank+'위'
  } catch(e) { /* Continue works even without completed standings. */ }
  shell(`<div class="continue-landing"><p class="eyebrow">CONTINUE CAREER</p><div class="continue-club">${careerLogo(selected)}<div><h1>${esc(selected.name)}</h1><p>${esc(league)} · ${selected.season}시즌 ${selected.week}주차</p><strong>리그 순위 · ${esc(position)}</strong></div></div><div class="continue-actions"><button class="act" id="resume">이어하기</button><a class="act" href="/app/manager">감독 프로필</a></div></div>`, '/app/home')
  document.getElementById('resume').onclick=()=>go('/app/home')
  await topbar()
}
async function operatorDesk() {
  const [data,calendar,audit]=await Promise.all([
    api('/operator/world'),api('/season-calendar?league=LCK'),api('/operator/nationality-audit')
  ])
  const upcoming=(calendar.fixtures||[]).filter(g=>g.week>=data.world.week).slice(0,15)
  const matches=upcoming.map(g=>'<div class="row"><b>'+g.season+'시즌 '+g.week+'주</b><span>'+esc(g.home)+' vs '+esc(g.away)+'</span><small>BO'+g.best_of+'</small></div>').join('')||'<p>진행될 대진이 없습니다.</p>'
  const summary='<div class="page-heading"><div><p class="eyebrow">FM · LEAGUE OPERATIONS</p><h1>리그 운영 대시보드</h1><p>최신 FM UI · 구단 관전 · 30개 선수 능력치 · 주차 진행</p></div><a class="act" href="/app/clubs">구단 관전</a></div>'
  const stats='<div class="grid3"><section class="panel"><h2>현재 주차</h2><strong>'+data.world.season+'시즌 '+data.world.week+'주차</strong></section><section class="panel"><h2>온라인 구단</h2><strong>'+data.clubs.length+'개</strong></section><section class="panel"><h2>국적 대조 현황</h2><strong>'+audit.with_code+' / '+audit.total+'</strong><p>국적 미확인 '+audit.missing_code+'명 · 국가 정보 후보 '+audit.source_backed_country_hints+'명 (별도 검증 필요)</p></section></div>'
  const seasons='<section class="panel"><h2>예정 경기 일정</h2>'+matches+'<a class="text-link" href="/app/schedule">전체 리그 캘린더</a></section>'
  const links='<section class="panel"><h2>운영 도구</h2><div class="row"><a class="act" href="/app/history">시즌 역사관 · 리그별 수상</a><a class="act" href="/app/players">선수 30개 능력치</a><a class="act" href="/app/leagues">LCK CL · LDL 리그</a></div></section>'
  shell(summary+stats+seasons+links,'/app/operator')
  await topbar()
}
async function worldSchedule(selected='LCK') {
  const world=worldState||await api('/world')
  const data=await api('/season-calendar?season='+world.season+'&league='+encodeURIComponent(selected))
  const items=(data.fixtures||[]).map(g=>'<tr><td>'+g.season+'시즌 '+g.week+'주</td><td>'+esc(g.league)+'</td><td>'+esc(g.home)+' vs '+esc(g.away)+'</td><td>BO'+g.best_of+'</td></tr>').join('')
  const picker='<label for="calendar-league">리그 선택</label><select id="calendar-league">'+data.leagues.map(league=>'<option value="'+esc(league)+'" '+(league===selected?'selected':'')+'>'+esc(league)+'</option>').join('')+'</select>'
  shell('<div class="page-heading"><div><p class="eyebrow">SEASON CALENDAR</p><h1>리그 전체 일정</h1><p>게임 내 생성 대진 · 실제 경기 날짜와 다를 수 있습니다</p></div></div><section class="panel">'+picker+'</section><section class="panel"><h2>대진 · '+data.fixtures.length+'경기</h2><div class="table-scroll"><table><thead><tr><th>시즌·주차</th><th>리그</th><th>경기</th><th>방식</th></tr></thead><tbody>'+items+'</tbody></table></div></section>','/app/schedule')
  document.getElementById('calendar-league').onchange=e=>worldSchedule(e.target.value)
  await topbar()
}
async function managerSetup() {
  const profile=managerProfile||await api('/manager-profile');const owned=await career()
  shell(`<div class="page-heading"><div><p class="eyebrow">MANAGER PROFILE</p><h1>${profile.complete?'감독 프로필':'감독 만들기'}</h1><p>닉네임과 이름을 정하고 능력치 60점을 배분하세요.</p></div></div><form id="manager-setup" class="panel manager-setup"><label>닉네임<input name="nickname" autocomplete="nickname" maxlength="30" required value="${esc(profile.nickname)}" placeholder="English nickname (e.g. Raven)" pattern="[A-Za-z]{2,20}" title="영문 2~20자"/></label><label>감독 이름<input name="managerName" autocomplete="name" maxlength="30" required value="${esc(profile.name)}" placeholder="감독 이름"/></label><label>감독 국적<input name="nationality" list="manager-nationalities" required placeholder="국가 이름을 입력하거나 선택" value="${esc(profile.nationality_name_ko||'')}"/><datalist id="manager-nationalities">${[...new Set(Object.values(FLAG_COUNTRIES).map(x=>x[1]))].map(name=>`<option value="${esc(name)}"></option>`).join('')}</datalist></label><h2>감독 능력치 <span id="stat-total"></span></h2><p>각 능력치 1~20 · 합계 60</p>${profile.attributes.map(key=>`<label class="stat-allocation"><span>${esc(key)}</span><input type="range" min="1" max="20" step="1" data-stat="${esc(key)}" value="${profile.stats[key]}"/><output>${profile.stats[key]}</output></label>`).join('')}<p class="err" id="manager-error" role="alert"></p><button class="act" id="save-manager">${owned?'프로필 저장':'저장하고 구단 선택'}</button></form>`,'/app/manager')
  const form=document.getElementById('manager-setup'),inputs=[...form.querySelectorAll('[data-stat]')],button=document.getElementById('save-manager')
  const update=()=>{const total=inputs.reduce((sum,i)=>sum+Number(i.value),0);inputs.forEach(i=>i.nextElementSibling.value=i.value);document.getElementById('stat-total').textContent=`${total} / 60 · ${total===60?'배분 완료':total<60?(60-total)+'점 남음':(total-60)+'점 초과'}`;button.disabled=total!==60}
  inputs.forEach(i=>i.oninput=update);update()
  form.onsubmit=async event=>{event.preventDefault();if(!form.reportValidity()||button.disabled)return;button.disabled=true;try{const name=form.elements.nationality.value.trim();const country=FLAG_COUNTRIES[name];if(!country)throw Error('국적을 국가 목록에서 선택하세요.');managerProfile=await api('/manager-profile',{nickname:form.elements.nickname.value.trim(),name:form.elements.managerName.value.trim(),nationality_code:country[0].toUpperCase(),stats:Object.fromEntries(inputs.map(i=>[i.dataset.stat,Number(i.value)]))});careerCache=null;go(owned?'/app/home':'/app/clubs')}catch(e){document.getElementById('manager-error').textContent=e.message;update()}}
  await topbar()
}
async function clubs() {
  const [mine,board,jobOffers]=await Promise.all([api('/careers'),api('/clubs'),isOperator?Promise.resolve({offers:[]}):api('/rookie-offers')])
  if(mine.careers.length&&!isOperator)return go('/app')
  const proposals=isOperator?board.clubs.map(c=>({team_key:c.team_key,team:c.team,league:c.league,power:c.power,available:true,description:'운영자 관전 · 읽기 전용'})):(jobOffers.offers||[])
  const open=mine.careers.map(c=>`<div class="row">${careerLogo(c)}<b>${esc(c.name)}</b><span>${esc(c.club_profile?.league||'')} · ${c.season}시즌 ${c.week}주</span><button class="act" data-open="${c.id}">이어하기</button></div>`).join('')
  const available=proposals.map(c=>`<div class="club-choice ${c.available?'':'club-locked'}">${logoImg(c.league,c.team)}<div><b>${esc(displayTeam(c.league,c.team))}</b><small>${esc(c.league)} · 파워 ${c.power??'미집계'} · ${isOperator?'운영자 조회':'부임 제안 '+c.ordinal+'/5'}</small><p>${esc(c.description||'')}</p></div><button class="act" data-team="${esc(c.team_key)}" ${c.available?'':'disabled'}>${isOperator?'구단 관전':c.available?'제안 수락':'부임 마감'}</button></div>`).join('')
  const leagues=board.leagues||[]
  shell(`<div class="page-heading"><div><p class="eyebrow">START YOUR CAREER</p><h1>${isOperator?'구단 관전 · 리그 관리':'감독 커리어 시작'}</h1><p>${isOperator?'선택한 구단을 최신 FM 화면으로 읽기 전용 조회합니다.':'하위 리그 또는 파워랭킹이 낮은 구단에서 시작하세요. 최상위 강팀은 경력이 필요합니다.'}</p></div></div>${open?`<section class="panel"><h2>내 커리어</h2>${open}</section>`:''}<div class="career-choice-grid">${isOperator?'':`<section class="panel club-creation"><h2>2부 리그 신생 구단 창단</h2><p>구단 이름, 3자 영문 약자, 전용 로고와 홈 컬러를 설정하세요.</p><form id="new-club"><label>구단 이름<input name="clubName" required minlength="2" maxlength="40" placeholder="예: Rising Phoenix"/></label><label>약자 (영문 대문자 3자)<input name="short" required maxlength="3" minlength="3" pattern="[A-Z]{3}" placeholder="RPH" style="text-transform:uppercase"/></label><label>참가할 2부 리그<select name="league">${leagues.map(l=>`<option value="${esc(l)}" ${l==='LCK CL'?'selected':''}>${esc(l)}</option>`).join('')}</select></label><label>홈 컬러<input name="color" type="color" value="#254a7a"/></label><label>엠블럼 모양<select name="emblem"><option value="shield">방패</option><option value="star">별</option><option value="crown">왕관</option><option value="bolt">번개</option><option value="diamond">다이아몬드</option></select></label><label>구단 로고 이미지 (선택, PNG/JPEG/WebP · 최대 80KB)<input name="logo" type="file" accept="image/png,image/jpeg,image/webp"/></label><p class="muted-note">로고 파일이 없으면 선택한 색상과 약자로 기본 엠블럼을 만듭니다.</p><button class="act" type="submit">신생 구단 창단 및 코치 영입</button><p class="err" id="club-err" role="alert"></p></form></section>`}<section class="panel"><h2>신인 감독에게 도착한 제안 · ${proposals.length}개 구단</h2><p>각 구단이 신인 감독에게 부임을 제안했습니다. 하나를 수락하거나 2부 구단을 직접 창단할 수 있습니다.</p><div class="club-choice-list">${available}</div></section></div>`,'/app/clubs')
  document.querySelectorAll('[data-open]').forEach(b=>b.onclick=()=>{localStorage.setItem('rift-career',b.dataset.open);careerCache=null;go('/app')})
  document.querySelectorAll('[data-team]').forEach(b=>b.onclick=async()=>{b.disabled=true;try{const result=await api('/careers',{mode:isOperator?'enter':'takeover',team_key:b.dataset.team});localStorage.setItem('rift-career',result.id);careerCache=null;go('/app')}catch(e){alert(e.message);b.disabled=false}})
  const form=document.getElementById('new-club')
  if(form) form.onsubmit=async e=>{e.preventDefault();const button=form.querySelector('button[type=submit]');button.disabled=true;const err=document.getElementById('club-err');try{
    const file=form.elements.logo.files[0]
    let logo_data=''
    if(file){if(file.size>80000||!['image/png','image/jpeg','image/webp'].includes(file.type))throw Error('80KB 이하 PNG/JPEG/WebP 이미지만 사용할 수 있습니다.');logo_data=await new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result);reader.onerror=()=>reject(Error('로고 파일을 읽을 수 없습니다.'));reader.readAsDataURL(file)})}
    const result=await api('/careers',{mode:'create',name:form.elements.clubName.value.trim(),short:form.elements.short.value.trim().toUpperCase(),league:form.elements.league.value,color:form.elements.color.value,emblem:form.elements.emblem.value,logo_data})
    localStorage.setItem('rift-career',result.id);careerCache=null;media.brandings=null;go('/app/onboarding')
  }catch(error){err.textContent=error.message;button.disabled=false}}
  await topbar()
}
async function onboarding() {
  const current=await requireCareer();if(!current)return
  const state=await api('/recruitment?id='+current.id)
  if(state.complete)return go('/app/home')
  const coaches=(state.people||[]).filter(p=>p.kind==='coach'&&p.assignment==='candidate')
  const chosen=(state.staff||[]).filter(p=>p.kind==='coach')
  shell(`<div class="onboarding-wizard"><p class="eyebrow">CLUB FOUNDATION · STEP 1 / 2</p><h1>코치진부터 구성하세요</h1><p>감독으로서 먼저 코치 후보를 선임하세요. 이후 선수 영입과 주전 5인 구성을 진행합니다.</p><section class="panel"><h2>선임한 코치 · ${chosen.length}명</h2>${chosen.map(p=>`<div class="row"><b>${esc(p.nickname||p.real_name)}</b><button class="act" data-recruit="${esc(p.id)}" data-enabled="false">선임 취소</button></div>`).join('')||'<p>아직 선임한 코치가 없습니다.</p>'}</section><section class="panel"><h2>초기 FA·생성 코치 후보</h2>${coaches.map(p=>`<div class="row"><b>${esc(p.nickname||p.real_name)}</b><span>${esc(p.staff_role_name||'코치')} · ${money(p.salary)}</span><button class="act" data-recruit="${esc(p.id)}" data-enabled="true">선임</button></div>`).join('')||'<p>선임 가능한 코치가 없습니다.</p>'}</section><p class="err" id="coach-error"></p><button class="act" id="to-players" ${chosen.length?'':'disabled'}>2단계 · 선수단 구성</button></div>`,'/app/staff')
  document.querySelectorAll('[data-recruit]').forEach(button=>button.onclick=async()=>{try{await api('/recruitment-select',{id:current.id,person:button.dataset.recruit,enabled:button.dataset.enabled==='true'});onboarding()}catch(e){document.getElementById('coach-error').textContent=e.message}})
  document.getElementById('to-players').onclick=()=>go('/app/squad')
  await topbar()
}
async function requireCareer() {
  if(isOperator)return await career()||{id:0,name:'리그 운영',season:worldState.season,week:worldState.week,role:'viewer'}
  const current=await career();if(!current){go('/app/clubs');return null}return current
}
function legacyWidget(id, dash) {
  if (id === 'news') return (dash.news || []).map(item => `<div class="row"><b>${esc(item.headline)}</b></div>`).join('') || '<p>뉴스가 없습니다.</p>'
  if (id === 'inbox') return (dash.inbox || []).map(item => `<div class="row"><a href="/app/inbox">${esc(item.subject)}</a></div>`).join('') || '<p>우편이 없습니다.</p>'
  if (id === 'standings') return `<table><tr><th>순위</th><th>구단</th><th>승</th><th>패</th></tr>` + (dash.standings || []).map(row => `<tr class="${row.team === dash.club ? 'mine' : ''}"><td>${row.rank ?? '-'}</td><td><a href="/app/team/${encodeURIComponent(dash.league)}/${encodeURIComponent(row.team)}">${logoImg(dash.league, row.team)}${esc(row.team)}</a></td><td>${row.wins}</td><td>${row.losses}</td></tr>`).join('') + '</table>'
  if (id === 'next') {
    const next = dash.next_fixture
    return next ? `<a href="/app/match/${next.id}"><b>${esc(next.opponent)}</b></a><p>${next.season}시즌 ${next.week}주 · BO${next.best_of}<br/>${esc(next.competition)} / ${esc(next.stage)}</p>` : '<p>예정된 경기가 없습니다.</p>'
  }
  if (id === 'squad') return (dash.lineup || []).map(item => `<div class="row"><a href="/app/player/${esc(item.person.id)}">${face(item.person.id,Boolean(item.person.photo))}${esc(item.person.display_name || item.person.nickname || item.person.real_name)}</a><span>${esc(ROLE[item.person.role] || item.person.role)} ${item.rating ?? '-'}</span></div>`).join('')
  if (id === 'budget') return `<p>이적 예산 ${money(dash.transfer_budget)}</p><p>이번 시즌 사용 ${money(dash.transfer_spent)}</p><p>보유 ${money(dash.cash)}</p>`
  if (id === 'wages') return `<p>급여 예산 ${money(dash.wage_budget)}</p><p>연봉 합계 ${money(dash.annual_payroll)}</p>`
  if (id === 'schedule') return dash.next_fixture ? `<a href="/app/schedule">${dash.next_fixture.week}주 ${esc(dash.next_fixture.opponent)}</a>` : '<p>일정 없음</p>'
  if (id === 'form') return (dash.opponent_form || []).map(game => `<div class="row">${game.won ? '승' : '패'} ${esc(game.opponent)} ${(game.score || []).join(':')}</div>`).join('') || '<p>최근 경기가 없습니다.</p>'
  if (id === 'board') return `<p>구단주 ${dash.manage?.board ?? '-'} </p><p>팬 ${dash.manage?.fans ?? '-'}</p>`
  if (id === 'staff') return (dash.manage?.staff_limits || []).map(item => `<div class="row">${esc(item.name)} ${item.count}/${item.limit}</div>`).join('') || '<p>스태프 장부가 없습니다.</p>'
  if (id === 'medical') return (dash.manage?.contracts || []).filter(item => item.person?.kind === 'player').slice(0, 6).map(item => `<div class="row">${esc(item.person.display_name || item.person.nickname || '')} 피로 ${item.fatigue}</div>`).join('') || '<p>의료 기록이 없습니다.</p>'
  return ''
}
async function home() {
  const current = await requireCareer(); if (!current) return
  shell('<div class="loading-panel">구단 소식을 불러오는 중입니다.</div>', '/app/home')
  const [dash, manage] = await Promise.all([api('/dashboard?id=' + current.id), api('/management?id=' + current.id)])
  dash.manage = manage
  const card=(id,extra='')=>`<section class="panel widget-${id} ${extra}"><h2>${WIDGETS[id]}</h2>${widget(id,dash)}</section>`
  document.getElementById('view').innerHTML=`<div class="page-heading"><div><p class="eyebrow">CLUB OVERVIEW</p><h1>대시보드</h1><p>${esc(current.name)} · ${esc(dash.league)} · 이번 주 구단 소식</p></div><a class="text-link" href="/app/schedule">전체 일정 보기 ↗</a></div><div class="fm-overview"><div>${card('inbox','inbox-tall')}</div><div>${card('news')}${card('next')}${card('form')}</div><div>${card('standings')}${card('squad')}</div><div>${card('budget')}${card('wages')}${card('cash')}${card('board')}</div></div>`
  await topbar()
}
function cashGraph(points) {
  const values=(points||[]).map(p=>Number(p.cash)).filter(Number.isFinite)
  if(!values.length)return '<p class="empty">현금 변동 내역이 없습니다.</p>'
  let lo=Math.min(...values),hi=Math.max(...values);if(lo===hi){lo-=1;hi+=1}
  const coords=values.map((v,i)=>`${8+i*264/Math.max(1,values.length-1)},${100-(v-lo)/(hi-lo)*80}`).join(' ')
  return `<svg class="cash-chart" viewBox="0 0 280 120" role="img" aria-label="현금 변동 그래프"><path d="M8 20H272M8 60H272M8 100H272" stroke="#303446"/><polyline points="${coords}" fill="none" stroke="#ef67db" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/></svg><small>원장 기준 · ${values.length}개 시점</small>`
}
function widget(id,dash) {
  if(id==='cash')return cashGraph(dash.cash_history)
  if(id==='squad')return (dash.lineup||[]).map(p=>`<a class="player-line" href="/app/player/${esc(p.person.id)}">${face(p.person.id,Boolean(p.person.photo))}<span><b>${esc(nickname(p.person))}</b><small>${esc(ROLE[p.person.role]||p.person.role)} · ${p.kills??0}/${p.deaths??0}/${p.assists??0} · ${p.games??0}경기</small></span><strong class="rating">${p.rating==null?'—':Number(p.rating).toFixed(1)}</strong></a>`).join('')||'<p class="empty">선발 선수를 등록하세요.</p>'
  if(id==='budget')return `<small>사용 가능한 영입 예산</small><strong class="money-value">${money(dash.transfer_budget)}</strong><div class="metric-pair"><span>이번 시즌 지출</span><b>${money(dash.transfer_spent)}</b></div><div class="metric-pair"><span>보유 현금</span><b>${money(dash.cash)}</b></div>`
  if(id==='inbox')return `<div class="inbox-filter"><span class="selected">전체</span><span>새 우편 ${(dash.inbox||[]).filter(m=>!m.read).length}</span></div>`+(dash.inbox||[]).map(m=>`<a href="/app/inbox" class="mail-item ${m.read?'':'unread'}"><small>${m.season}시즌 · ${m.week}주 <span>${m.read?'읽음':'새 우편'}</span></small><b>${esc(m.subject)}</b><p>${esc((m.body||'').slice(0,85))}</p></a>`).join('')+'<a class="panel-link" href="/app/inbox">우편함 전체 보기 →</a>'
  if(id==='form')return '<small>다음 상대 · 최근 5경기</small><div class="form-strip">'+(dash.opponent_form||[]).map(g=>`<span class="form-result ${g.won?'win':'loss'}" title="${esc(g.opponent)}">${g.won?'승':'패'}</span>`).join('')+'</div>'+(!(dash.opponent_form||[]).length?'<p class="empty">기록된 경기가 없습니다.</p>':'')
  return legacyWidget(id,dash)
}
async function inbox() {
  const current = await requireCareer(); if (!current) return
  const [data,follows]=await Promise.all([api('/inbox?id='+current.id),api('/follows?id='+current.id)])
  const favorites=(follows.follows||[]).map(x=>'<span class="mail-follow-chip">'+esc(x.entity)+' · '+(x.kind==='competition'?'리그':x.kind==='player'?'선수':'구단')+'</span>').join('')
  shell(`<div class="page-heading"><h1>구단 우편함</h1><a class="act" href="/app/news">팔로우·리그 뉴스 열기</a></div><section class="panel"><h2>팔로우 중인 소식</h2><div class="mail-follow-list">${favorites||'<p class="empty">아직 팔로우한 대상이 없습니다. 리그·선수·구단에서 팔로우하세요.</p>'}</div></section><div class="panel"><h2>우편</h2>${data.messages.map(mail => `<div class="row"><div><b>${esc(mail.subject)}</b><p>${esc(mail.body || '')}</p></div><button class="act" data-mail="${mail.id}">읽음</button></div>`).join('') || '<p>우편이 없습니다.</p>'}</div>`, '/app/inbox')
  document.querySelectorAll('[data-mail]').forEach(button => button.onclick = () => api('/read-mail', {id:current.id, mail:Number(button.dataset.mail)}).then(() => inbox()))
  await topbar()
}
const newsState={scope:'home',league:''}
async function news() {
 const current=await requireCareer();if(!current)return
 const league=current.club_profile?.league||''
 if(!isOperator&&!newsState.league)newsState.league=league
 const [feed,follows,board]=await Promise.all([
   api('/news?id='+(isOperator?0:current.id)+'&scope='+encodeURIComponent(isOperator?'all':newsState.scope)+'&competition='+encodeURIComponent(newsState.league)),
   isOperator?Promise.resolve({follows:[]}):api('/follows?id='+current.id),
   api('/clubs')
 ])
 const tracked=follows.follows||[]
 const leagues=[...new Set((board.clubs||[]).map(c=>c.league).filter(Boolean))]
 const followed=(kind,entity)=>tracked.some(f=>f.kind===kind&&f.entity===entity)
 const filterTabs=(isOperator?[]:[['home','내 소식·리그 전체'],['league','리그 뉴스'],['following','팔로우 뉴스']]).map(([key,title])=>
   '<button class="news-filter-tab '+(newsState.scope===key?'selected':'')+'" data-news-scope="'+key+'">'+title+'</button>').join('')
 const leagueFilters=(isOperator?['',...leagues]:leagues).map(l=>'<div class="news-league-chip">'+
   '<button class="'+(newsState.league===l?'selected':'')+'" data-news-league="'+esc(l)+'">'+
   (l?leagueIcon(l)+'<b>'+esc(l)+'</b>':'<b>전체 리그</b>')+'</button>'+
   (isOperator?'':'<button class="news-follow-toggle '+(followed('competition',l)?'following':'')+'" data-news-follow="'+esc(l)+'">'+
     (followed('competition',l)?'팔로우 중 ✓':'＋ 팔로우')+'</button>')+'</div>').join('')
 const items=(feed.news||[]).map(n=>'<article class="headline-card">'+
   '<span class="headline-category">'+(n.own_team?'내 구단 · ':esc(n.competition)+' · ')+n.season+'시즌 '+n.week+'주</span>'+
   '<h3>'+esc(n.headline)+'</h3>'+ (isOperator?'<p>'+esc(n.body||'')+'</p>':'')+
   '<div class="headline-footer"><span>'+esc(n.label||'게임 내 뉴스')+'</span></div></article>').join('')
 const personal=tracked.filter(f=>f.kind==='player'||f.kind==='team').map(f=>
   '<button class="followed-person" data-news-unfollow="'+esc(f.kind)+'" data-news-entity="'+esc(f.entity)+'">'+esc(f.entity)+' · 팔로우 해제 ✕</button>').join('')
 shell('<div class="page-heading"><div><p class="eyebrow">NEWSROOM</p><h1>'+(isOperator?'전체 리그 뉴스 · 운영자':'리그 뉴스·팔로우')+'</h1>' +
  '<p>'+(isOperator?'모든 구단의 뉴스와 스토브리그 소식을 통합 열람합니다. 리그별로 필터링할 수 있습니다.':'내 구단과 현재 리그는 항상 뉴스에 포함됩니다. 선수·구단·리그를 추가 팔로우할 수 있습니다.')+'</p></div></div>'+
  '<div class="news-filter-tabs">'+filterTabs+'</div><div class="newsroom-grid"><section class="panel">'+
  '<h2>이번 주 헤드라인</h2><div class="news-headlines">'+(items||'<p class="empty">현재 등록된 뉴스가 없습니다. 경기를 진행하면 새로운 기사가 발행됩니다.</p>')+'</div></section>'+
  '<aside class="panel newsroom-follows"><h2>'+(isOperator?'리그별 뉴스 조회':'리그 팔로우')+'</h2><div class="league-follow-grid">'+leagueFilters+'</div>'+
  (isOperator?'':'<h2>팔로우한 선수·구단</h2>'+(personal||'<p class="empty">선수 프로필에서 팔로우할 수 있습니다.</p>'))+
  '</aside></div>','/app/news')
 document.querySelectorAll('[data-news-scope]').forEach(b=>b.onclick=()=>{newsState.scope=b.dataset.newsScope;news()})
 document.querySelectorAll('[data-news-league]').forEach(b=>b.onclick=()=>{newsState.league=b.dataset.newsLeague;news()})
 document.querySelectorAll('[data-news-follow]').forEach(b=>b.onclick=async()=>{
   const entity=b.dataset.newsFollow
   try{await api('/follows',{id:current.id,kind:'competition',entity,enabled:!followed('competition',entity)});await news()}
   catch(e){alert(e.message)}
 })
 document.querySelectorAll('[data-news-unfollow]').forEach(b=>b.onclick=()=>api('/follows',{
   id:current.id,kind:b.dataset.newsUnfollow,entity:b.dataset.newsEntity,enabled:false}).then(()=>news()).catch(e=>alert(e.message)))
 await topbar()
}
function nickname(person) {return person.nickname || person.nickname_ko || person.display_name || person.name || '이름 확인 중'}
function personLink(person) {
  return `<a href="/app/player/${esc(person.id)}">${face(person.id,Boolean(person.photo))}<span>${esc(nickname(person))}<small>${esc(person.real_name_ko || person.display_name_ko || person.real_name || '')}</small>${flagAndCountry(person)}</span></a>`
}
function rosterTable(people, records={}, development={}, contracts={}) {
  if(!people.length)return '<p class="empty">등록된 선수가 없습니다.</p>'
  return `<div class="table-scroll"><table class="roster-table"><thead><tr>${['선수 얼굴 · 닉네임 / 이름','구분','소속 팀','게임 레이팅','OVR','인지도','국적','포지션','연봉','시장가치','계약년도','만료'].map(t=>`<th>${t}</th>`).join('')}</tr></thead><tbody>${people.map(p=>{
    const c=contracts[p.id],d=development[p.id],r=records[p.id],eco=p.economics||{};const ratings=p.game_evaluation?.ratings||p.stats;const values=ratings?Object.values(ratings).filter(Number.isFinite):[];const ovr=d?.ovr??(values.length?Math.round(values.reduce((a,b)=>a+b,0)/values.length):null)
    const start=c?.start_turn?`${2026+Math.floor((c.start_turn-1)/150)}년 · ${Math.floor((c.start_turn-1)/150)+1}시즌`:'미기록'
    const expiry=c?`${2026+Math.floor((c.end_turn-1)/150)}년 · ${Math.floor((c.end_turn-1)/150)+1}시즌 ${((c.end_turn-1)%150)+1}주`:p.contract_end||'확인 중'
    const group=p.kind==='player'?(p.real_person?'실존 선수':'생성 선수'):(p.real_person?'실존 프런트':'생성 프런트');const assignment=rosterStatus(p)
    return `<tr><td>${personLink(p)}</td><td><span class="identity-tag ${p.real_person?'real':'generated'}">${group}</span><small>${esc(assignment)}</small></td><td>${logoImg(p.league,p.team)}${esc(p.team||'무소속')}</td><td><b class="rating">${eco.rating??'미평가'}</b><small>${r?.rating!=null?'게임 경기 평점 '+Number(r.rating).toFixed(1):'능력·경력 평가'}</small></td><td><b>${d?.ovr??eco.ovr??ovr??'미평가'}</b></td><td><b>${eco.fame??'미평가'}</b></td><td>${flagAndCountry(p)}</td><td>${esc(ROLE[p.role]||'확인 중')}</td><td>${money(c?.annual_salary??eco.annual_salary??p.salary)}<small>${c?'구단 계약':'연봉 추정'}</small></td><td>${money(eco.market_value)}</td><td>${start}</td><td>${esc(expiry)}${!c&&p.contract_estimated?'<small>예상</small>':''}</td></tr>`
  }).join('')}</tbody></table></div>`
}
async function squad(which) {
  const current=await requireCareer();if(!current)return
  const [data,manage,train,stats]=await Promise.all([api('/recruitment?id='+current.id),api('/management?id='+current.id),api('/training?id='+current.id),api('/analytics?id='+current.id+'&season='+current.season)])
  const index=(items,key='id')=>Object.fromEntries(items.map(x=>[key==='person'?x.person.id:x.id,x]));const records=index(stats.players||[]),dev=index(train.players||[],'person'),contracts=index((manage.contracts||[]).filter(c=>c.active),'person')
  const registered=(data.people||[]).filter(p=>p.kind==='player' || p.kind==='unclassified')
  const shown=registered.filter(p=>which==='academy'?p.assignment==='academy':['first','reserve'].includes(p.assignment))
  const extra=registered.filter(p=>which==='academy'?p.assignment==='candidate':p.assignment==='unclassified')
  const sort=(a,b)=>Object.keys(ROLE).indexOf(a.role)-Object.keys(ROLE).indexOf(b.role)||nickname(a).localeCompare(nickname(b),'ko')
  shell(`<div class="page-heading"><div><p class="eyebrow">SQUAD REGISTRATION</p><h1>${which==='academy'?'2군 · 육성 선수단':'1군 선수단'}</h1><p>${esc(current.name)} · ${shown.length}명</p></div><a class="text-link" href="/app/${which==='academy'?'squad':'academy'}">${which==='academy'?'1군 보기':'2군 보기'}</a></div><section class="panel">${rosterTable(shown.sort(sort),records,dev,contracts)}</section>${extra.length?`<section class="panel"><h2>${which==='academy'?'영입·육성 후보':'등록 분류 확인 중'}</h2>${rosterTable(extra.sort(sort),records,dev,contracts)}</section>`:''}${data.complete?'':'<p>경기 참가를 위해 각 포지션의 1군 주전 선수를 등록하세요.</p>'}`,which==='academy'?'/app/academy':'/app/squad')
  if(data.mode==='create' && !data.complete){
    const selectable=(data.people||[]).filter(p=>p.assignment==='candidate'&&p.kind==='player'&&p.solo?.path==='pro')
    document.getElementById('view').insertAdjacentHTML('afterbegin',`<section class="panel"><h2>창단 선수단 구성 · ${data.roster.length} / 5</h2><p>포지션마다 주전 한 명을 선택한 뒤 등록을 완료하세요. 아래 후보는 생성 선수입니다.</p>${data.roster.map(p=>`<div class="row">${personLink(p)}<b>${esc(ROLE[p.role])}</b><button class="act" data-recruit="${esc(p.id)}" data-enabled="false">선택 취소</button></div>`).join('')}${Object.entries(ROLE).map(([role,label])=>`<details class="recruit-role"><summary>${label} · 후보 ${selectable.filter(p=>p.role===role).length}명</summary>${selectable.filter(p=>p.role===role).map(p=>`<div class="row">${personLink(p)}<span>OVR ${dev[p.id]?.ovr??'미평가'} · 연봉 ${money(p.salary)}</span><button class="act" data-recruit="${esc(p.id)}" data-enabled="true" ${data.roster.some(r=>r.role===role)?'disabled':''}>주전 선택</button></div>`).join('')}</details>`).join('')}<button class="act" id="finalize-roster" ${data.roster.length===5?'':'disabled'}>주전 5명 등록 완료</button><p class="err" id="recruit-error"></p></section>`)
    const action=async(path,body)=>{try{await api(path,{id:current.id,...body});careerCache=null;draw()}catch(e){document.getElementById('recruit-error').textContent=e.message}}
    document.querySelectorAll('[data-recruit]').forEach(b=>b.onclick=()=>action('/recruitment-select',{person:b.dataset.recruit,enabled:b.dataset.enabled==='true'}))
    document.getElementById('finalize-roster').onclick=()=>action('/recruitment-finalize',{})
  }
  await topbar()
}
async function tactics() {
 const current=await requireCareer();if(!current)return
 const [data,registration]=await Promise.all([api('/plan?id='+current.id),api('/recruitment?id='+current.id)])
 const plan=data.plan,catalog=data.catalog,draft=JSON.parse(JSON.stringify(plan))
 draft.callers=draft.callers||{}
 const roster=(registration.roster||[]).filter(p=>p.kind==='player')
 const names={early:'초반',mid:'중반',late:'후반'}
 const options=(items,selected,attrs)=>'<div class="tactic-option-grid">'+items.map(x=>'<button type="button" class="tactic-option '+(x===selected?'selected':'')+'" '+attrs+'="'+esc(x)+'">'+esc(x)+'</button>').join('')+'</div>'
 const phases=['early','mid','late'].map((phase,index)=>'<section class="panel tactic-phase">'+
   '<div class="tactic-phase-title"><span class="tactic-phase-number">0'+(index+1)+'</span><div><h2>'+names[phase]+' 운영</h2><p>'+(index===0?'라인전·정글 동선':index===1?'전령·드래곤·교전': '바론·장로·후반 운영')+'</p></div></div>'+
   '<h3>경기 운영 전략</h3>'+options(catalog.orders[phase],plan[phase]?.order||'','data-tactic-order="'+phase+'" data-option')+
   '<h3>세부 지침</h3>'+options(catalog.subs[phase],plan[phase]?.sub||'','data-tactic-sub="'+phase+'" data-option')+'</section>').join('')
 const caller=key=>'<div class="tactic-callers"><h3>'+(key==='primary'?'메인 오더':'서브 오더')+'</h3><div class="tactic-caller-options">'+roster.map(p=>
   '<button type="button" class="tactic-caller '+(draft.callers?.[key]===p.id?'selected':'')+'" data-tactic-caller="'+key+'" data-person="'+esc(p.id)+'">'+
   face(p.id,Boolean(p.photo))+'<b>'+esc(nickname(p))+'</b><small>'+esc(ROLE[p.role]||p.role)+'</small></button>').join('')+'</div></div>'
 const lanes=Object.entries(catalog.laning).map(([role,values])=>
   '<div class="tactic-lane-row" id="tactic-'+role+'"><div class="tactic-lane-title"><b>'+esc(ROLE[role])+'</b><small>라인별 교전·압박 방식</small></div>'+
   options(values,draft.laning?.[role]||'','data-tactic-lane="'+role+'" data-option')+'</div>').join('')
 const positions={TOP:[19,26],JUNGLE:[38,46],MID:[55,50],ADC:[78,73],SUPPORT:[68,79]}
 const markers=Object.entries(positions).map(([role,pos])=>'<a class="rift-position rift-'+role.toLowerCase()+'" href="#tactic-'+role+'" style="left:'+pos[0]+'%;top:'+pos[1]+'%">'+esc(ROLE[role])+'</a>').join('')
 shell('<div class="page-heading"><div><p class="eyebrow">TACTICAL BOARD</p><h1>전술 센터</h1><p>실제 경기 중 사용할 오더·라인전 전략을 그래픽 보드에서 선택합니다.</p></div><button class="act" id="save-plan">전술 저장</button></div>'+
   '<div class="tactic-main-grid"><section class="panel tactic-map-panel"><h2>소환사의 협곡 · 팀 운영 지도</h2>'+
   '<div class="tactic-rift-map" role="img" aria-label="소환사의 협곡 5개 포지션 전술 배치">'+markers+'</div>'+
   '<div class="tactic-map-legend"><span>탑 · 상단</span><span>정글 · 합류</span><span>미드 · 중심</span><span>원딜·서폿 · 하단</span></div>'+
   '<p class="muted-note">포지션을 누르면 해당 전술 설정으로 이동합니다.</p></section>'+
   '<section class="panel"><h2>콜 지휘 체계</h2>'+caller('primary')+caller('secondary')+
   '<p class="muted-note">두 명의 서로 다른 1군 주전 선수를 선택해야 합니다.</p></section></div>'+
   '<div class="tactic-phases">'+phases+'</div><section class="panel"><h2>라인별 전략</h2>'+
   '<div class="tactic-lanes">'+lanes+'</div></section>'+
   '<div class="tactic-save-banner"><span>수정된 전략은 다음 경기 세트부터 적용됩니다.</span><button class="act" id="save-plan-bottom">전술 저장</button></div>','/app/tactics')
 const select=(kind,key,value,selector)=>{
   if(kind==='order'||kind==='sub')draft[key][kind]=value
   else if(kind==='lane')draft.laning[key]=value
   else draft.callers[key]=value
   document.querySelectorAll(selector).forEach(button=>button.classList.toggle('selected',(kind==='caller'?button.dataset.person:button.dataset.option)===value))
 }
 document.querySelectorAll('[data-tactic-order]').forEach(button=>button.onclick=()=>select('order',button.dataset.tacticOrder,button.dataset.option,'[data-tactic-order="'+button.dataset.tacticOrder+'"]'))
 document.querySelectorAll('[data-tactic-sub]').forEach(button=>button.onclick=()=>select('sub',button.dataset.tacticSub,button.dataset.option,'[data-tactic-sub="'+button.dataset.tacticSub+'"]'))
 document.querySelectorAll('[data-tactic-lane]').forEach(button=>button.onclick=()=>select('lane',button.dataset.tacticLane,button.dataset.option,'[data-tactic-lane="'+button.dataset.tacticLane+'"]'))
 document.querySelectorAll('[data-tactic-caller]').forEach(button=>button.onclick=()=>select('caller',button.dataset.tacticCaller,button.dataset.person,'[data-tactic-caller="'+button.dataset.tacticCaller+'"]'))
 const save=async()=>{if(!draft.callers.primary||!draft.callers.secondary||draft.callers.primary===draft.callers.secondary){
    alert('메인·서브 오더를 서로 다른 주전 선수로 지정하세요.');return}
   try{await api('/plan',{id:current.id,plan:draft});alert('전술이 저장되었습니다.')}catch(e){alert(e.message)}
 }
 document.getElementById('save-plan').onclick=save
 document.getElementById('save-plan-bottom').onclick=save
 await topbar()
}
async function training() {
  const current = await requireCareer(); if (!current) return
  await loadChampionMeta()
  const data = await api('/training?id=' + current.id)
  const rows = data.players.map(row => {
    const person = row.person
    const chips = row.pool.map(name => `<b class="champion-chip">${championIcon(name)}${esc(championKo(name))} · 숙련</b>`).join('')
    return `<div class="panel"><div class="row">${personLink(person)}<span>OVR ${row.ovr}</span><span>폭 ${row.pool.length}/6</span><span>이번 주 ${row.assigned === 'pool' ? '챔프폭' : 'OVR'}</span></div><div class="pool">${chips}</div><p>폭 안의 챔피언은 수준급, 밖은 그럭저럭입니다. 최소 2, 최대 6.</p><select data-person="${esc(person.id)}"><option value="auto" ${row.focus === 'auto' ? 'selected' : ''}>자동 배정</option><option value="ovr" ${row.focus === 'ovr' ? 'selected' : ''}>OVR</option><option value="pool" ${row.focus === 'pool' ? 'selected' : ''}>챔프폭</option></select></div>`
  }).join('')
  shell(`<button class="act" id="auto-all">전원 자동 배정</button>` + rows, '/app/training')
  document.getElementById('auto-all').onclick = () => api('/training', {id:current.id, person:'all', focus:'auto'}).then(() => draw())
  document.querySelectorAll('[data-person]').forEach(select => select.onchange = () => api('/training', {id:current.id, person:select.dataset.person, focus:select.value}).then(() => draw()).catch(error => alert(error.message)))
  document.querySelectorAll('a[href^="/app/player"]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); go(link.getAttribute('href')) }))
  await topbar()
}
async function managementPage(kind) {
  const current = await requireCareer(); if (!current) return
  const data = await api('/management?id=' + current.id)
  const departures = kind === 'medical' ? await api('/departure-requests?id=' + current.id) : {requests:[]}
  let body = ''
  if (!data.initialized) body = '<p>재정과 계약이 아직 열리지 않았습니다.</p>'
  else if (kind === 'finance') {
    const ledger=(data.ledger||[])
    let balance=Number(data.cash)||0
    const history=[{cash:balance}]
    for(const l of ledger){balance-=Number(l.amount)||0;history.unshift({cash:balance})}
    const cash=Math.max(1,Number(data.cash)||1),budget=Math.max(0,Number(data.transfer_budget)||0)
    const payroll=Number(data.annual_payroll)||0
    const merch=data.merchandise||{}
    body='<div class="page-heading"><h1>재정 센터</h1><p>이적 자금·현금·연봉·스폰서 수입을 시각화한 이번 시즌 회계</p></div>'+
      '<div class="finance-dash"><section class="panel"><h2>구단 유동성</h2><div class="finance-hero">'+money(data.cash)+'</div>'+
       cashGraph(history)+'<p class="muted-note">원장에 기록된 실제 게임 내 수입·지출만 사용</p></section>'+
      '<section class="panel"><h2>예산 배분</h2><div class="fm-finance-totals">'+
      [['이적 예산',budget],['연봉 약정',payroll],['굿즈 누적 순이익',Number(merch.profit)||0],['현금',cash]].map(([label,value])=>
       '<div class="finance-budget-row"><span>'+label+'</span><strong>'+money(value)+'</strong>'+
       '<div class="bar-track"><span style="width:'+Math.max(0,Math.min(100,value/cash*100))+'%"></span></div></div>').join('')+
      '</div><div class="budget-editor"><label>이적 예산 조정<input id="budget-transfer" type="number" min="0" value="'+budget+'"/></label>'+
       '<label>급여 예산<input id="budget-wage" type="number" min="0" value="'+Number(data.wage_budget||0)+'"/></label>'+
       '<button class="act" id="save-budget">예산 저장</button></div></section></div>'+
       '<section class="panel"><h2>회계 내역 · '+ledger.length+'건</h2>'+
       ledger.map(row=>'<div class="finance-ledger-line"><span>'+row.season+'시즌 '+row.week+'주 · '+esc(row.description)+'</span>'+
       '<b class="'+(row.amount>=0?'positive':'negative')+'">'+(row.amount>=0?'+':'')+money(row.amount)+'</b></div>').join('')+'</section>'
  } else if (kind === 'medical') {
    const players=(data.contracts||[]).filter(item=>item.person.kind==='player')
    const names=Object.fromEntries(players.map(x=>[x.person.id,nickname(x.person)]))
    const bar=(title,value,bad)=>'<div class="health-stat"><span>'+title+'</span><strong>'+value+'%</strong><div class="bar-track '+(bad?'warning':'')+'"><span style="width:'+Math.min(100,Math.max(0,value))+'%"></span></div></div>'
    body='<div class="page-heading"><h1>의료 센터</h1><p>피로·사기·부상 회복과 선발 기회에 관한 선수 면담을 한 화면에서 관리합니다.</p></div>'+
      '<div class="medical-board">'+players.map(item=>{
       const p=item.person
       return '<div class="panel medical-player-card"><div class="medical-player-head">'+personLink(p)+
         '<span class="health-status '+(item.injury_turns?'injured':'available')+'">'+(item.injury_turns?'부상 '+item.injury_turns+'주':'출전 가능')+'</span></div>'+
         bar('피로도',Number(item.fatigue)||0,Number(item.fatigue)>70)+bar('기분·사기',Number(item.morale)||0,Number(item.morale)<40)+
         '<div class="medical-actions">'+[['rest','휴식'],['rehab','재활'],['normal','일반 훈련']].map(([key,label])=>
         '<button class="act '+(item.treatment===key?'selected':'')+'" data-treat="'+esc(p.id)+'" data-mode="'+key+'">'+label+'</button>').join('')+'</div></div>'
       }).join('')+'</div><section class="panel"><h2>2군·후보 선수와의 면담</h2>'+
       (departures.requests.length?departures.requests.map(r=>'<div class="medical-departure"><b>'+esc(names[r.person_id]||'선수 정보 확인 중')+'</b>'+
        '<span>'+esc(r.reason)+' · 사기 '+(r.morale??'-')+'</span>'+
        '<button class="act" data-release="'+esc(r.person_id)+'" data-approve="true">FA 합의 방출</button>'+
        '<button class="act" data-release="'+esc(r.person_id)+'" data-approve="false">거절</button></div>').join(''):
         '<p class="empty">선수 방출 요청 없음</p>')+'</section>'
  } else if (kind === 'relations') {
    const contracts=data.contracts||[],pmap=Object.fromEntries(contracts.map(x=>[x.person.id,x.person]))
    const bonds=(data.relationships||[]).map(item=>{
      const a=pmap[item.first],b=pmap[item.second],trust=Number(item.trust)||0
      return '<div class="relation-card"><div class="relation-pair">'+
       (a?personLink(a):'<span>이전 소속 선수</span>')+
       '<span class="relation-connection">↔</span>'+
       (b?personLink(b):'<span>이전 소속 선수</span>')+'</div>'+
       '<div class="relation-trust"><span>상호 신뢰</span><strong>'+trust+'/100</strong>'+
       '<div class="bar-track '+(trust<40?'warning':'')+'"><span style="width:'+trust+'%"></span></div></div>'+
       '<div class="relation-actions">'+[['listen','대화·경청'],['roles','역할 조정'],['demand','강경 지시']].map(([way,label])=>
         '<button class="act" data-a="'+esc(item.first)+'" data-b="'+esc(item.second)+'" data-way="'+way+'">'+label+'</button>').join('')+
        '</div></div>'
    }).join('')
    body='<div class="page-heading"><h1>선수단 관계</h1><p>선수 사진·이름·신뢰도·갈등 조정 기능을 확인합니다.</p></div>'+
      '<div class="relation-grid">'+(bonds||'<p class="empty">기록된 관계가 없습니다.</p>')+'</div>'
  } else if (kind === 'staff') {
    const limits=(data.staff_limits||[])
    body='<div class="page-heading"><h1>프런트·코칭스태프 정원</h1><p>감독·수석코치·코치·분석관·의료 인력의 현재 인원과 허용 정원</p></div>'+
      '<div class="staff-grid">'+limits.map(x=>'<div class="panel staff-position-card"><h2>'+esc(x.name)+'</h2>'+
       '<div class="staff-number">'+x.count+'<small> / '+x.limit+'명</small></div>'+
       '<div class="bar-track"><span style="width:'+Math.min(100,x.count/Math.max(1,x.limit)*100)+'%"></span></div></div>').join('')+
      '</div><section class="panel"><h2>스태프 충원</h2><button class="act" id="staff-find">스태프 후보 찾기</button></section>'
  } else {
    const v=data.vision;const goalList=audience=>(v.goals[audience]||[]).map(g=>`<div class="vision-goal"><div><b>${esc(g.title)}</b><small>${esc(g.deadline)}</small></div><span>${esc(g.progress)}</span><strong class="${g.met?'goal-met':'goal-pending'}">${esc(g.status)}</strong></div>`).join('')
    body=`<div class="page-heading"><div><p class="eyebrow">CLUB VISION & SUPPORT</p><h1>구단 비전 · 민심</h1><p>${v.season}시즌 · 구단주와 팬이 감독에게 바라는 목표</p></div></div><div class="grid3"><section class="panel"><h2>구단주 신임</h2><strong class="money-value">${v.board} / 100</strong><p>${esc(v.board_mood)}</p></section><section class="panel"><h2>팬 민심</h2><strong class="money-value">${v.fans} / 100</strong><p>${esc(v.fan_mood)}</p></section></div><section class="panel"><h2>구단주 요구사항</h2>${goalList('board')}</section><section class="panel"><h2>팬 요구사항</h2>${goalList('fans')}</section><section class="panel"><h2>민심 변화와 이유</h2>${v.history.length?v.history.map(h=>`<div class="row"><small>${h.season}시즌 ${h.week}주</small><b>${esc(h.reason)}</b><span>구단주 ${h.board_delta>0?'+':''}${h.board_delta} · 팬 ${h.fan_delta>0?'+':''}${h.fan_delta}</span></div>`).join(''):'<p class="empty">아직 기록된 민심 변화가 없습니다.</p>'}</section>`

  }
  const path = {finance:'/app/finance', medical:'/app/medical', relations:'/app/relations', staff:'/app/staff', vision:'/app/vision'}[kind]
  shell(body, path)
  const budget = document.getElementById('save-budget')
  if (budget) budget.onclick = () => api('/management', {id:current.id, action:'budget', transfer_budget:Number(document.getElementById('budget-transfer').value), wage_budget:Number(document.getElementById('budget-wage').value)}).then(() => draw()).catch(error => alert(error.message))
  document.querySelectorAll('[data-release]').forEach(button => button.onclick = async () => {
    const approve=button.dataset.approve==='true'
    if(!confirm(approve?'선수와 합의해 계약을 종료하고 FA로 전환할까요?':'선수의 FA 요청을 거절할까요?'))return
    try {
      await api('/departure-decision',{id:current.id,person:button.dataset.release,approve})
      await managementPage('medical')
    } catch(error) {alert(error.message)}
  })
  document.querySelectorAll('[data-treat]').forEach(button => button.onclick = () => api('/management', {id:current.id, action:'treatment', person:button.dataset.treat, treatment:button.dataset.mode}).then(() => draw()).catch(error => alert(error.message)))
  document.querySelectorAll('[data-way]').forEach(button => button.onclick = () => api('/management', {id:current.id, action:'mediate', first:button.dataset.a, second:button.dataset.b, approach:button.dataset.way}).then(() => draw()).catch(error => alert(error.message)))
  const find = document.getElementById('staff-find')
  if (find) find.onclick = () => api('/staff-candidates', {id:current.id}).then(() => alert('스태프 후보를 만들었습니다.')).catch(error => alert(error.message))
  await topbar()
}
let calendarPage=0
async function schedule() {
 const current=await requireCareer();if(!current)return
 const data=await api('/fixtures?id='+current.id)
 const all=data.fixtures||[]
 const season=current.season
 const currentWeek=current.week
 const fixtures=all.filter(g=>g.season===season)
 const maxPage=Math.ceil(150/14)-1
 if(calendarPage<0||calendarPage>maxPage)calendarPage=Math.floor((currentWeek-1)/14)
 const start=calendarPage*14+1
 const cells=Array.from({length:14},(_,i)=>{
   const week=start+i;if(week>150)return '<div class="calendar-cell calendar-unused"></div>'
   const games=fixtures.filter(g=>g.week===week)
   const status=week===currentWeek?'current-week':week<currentWeek?'past-week':'future-week'
   return '<div class="calendar-cell '+status+'"><div class="calendar-cell-heading"><b>'+week+'주</b><small>'+
       (week===currentWeek?'이번 주':'시즌 '+season)+'</small></div>'+
      (games.length?games.map(g=>'<a class="calendar-match '+(g.state==='finished'?'played':g.state==='queued'?'ready':'scheduled')+'" href="/app/match/'+g.id+'">'+
           logoImg(current.club_profile?.league||'',g.opponent)+'<span><b>'+esc(displayTeam(current.club_profile?.league||'',g.opponent))+'</b><small>'+
           esc(g.competition||'정규 시즌')+' · BO'+g.best_of+' · '+(g.state==='finished'?'종료':g.state==='queued'?'진행':'예정')+'</small></span></a>').join(''):
       '<div class="calendar-rest">경기 없음 <small>훈련·휴식</small></div>')+'</div>'
 }).join('')
 const nextGame=fixtures.filter(g=>g.state!=='finished'&&g.week>=currentWeek).sort((a,b)=>a.week-b.week)[0]
 const ended=fixtures.filter(g=>g.state==='finished').length
 shell('<div class="page-heading"><div><p class="eyebrow">SEASON PLANNER</p><h1>시즌 경기 캘린더</h1><p>'+season+'시즌 · 실제 날짜가 아닌 게임 주차 기준</p></div></div>'+
  '<div class="calendar-summary"><div><small>현재</small><strong>'+currentWeek+'주</strong></div><div><small>진행 경기</small><strong>'+ended+'경기</strong></div><div><small>다음 상대</small><strong>'+esc(nextGame?displayTeam(current.club_profile?.league||'',nextGame.opponent):'미정')+'</strong></div></div>'+
  '<section class="panel calendar-panel"><div class="calendar-toolbar"><div><h2>시즌 일정 · '+start+'~'+Math.min(150,start+13)+'주</h2><small>승패·예정 경기와 휴식 주간을 카드로 확인합니다</small></div>'+
  '<div class="calendar-controls"><button data-calendar-prev '+(calendarPage===0?'disabled':'')+'>〈 이전</button><button data-calendar-now>이번 주</button><button data-calendar-next '+(calendarPage===maxPage?'disabled':'')+'>다음 〉</button></div></div>'+
  '<div class="calendar-weekheaders">'+['첫 번째','두 번째','세 번째','네 번째','다섯 번째','여섯 번째','일곱 번째'].map(day=>'<span>'+day+' 주차 칸</span>').join('')+'</div>'+
  '<div class="calendar-grid">'+cells+'</div>'+
  '<div class="calendar-legend"><span><i class="dot-pending"></i> 예정</span><span><i class="dot-complete"></i> 종료</span><span><i class="dot-current"></i> 이번 주</span></div>'+
  '<p class="muted-note">현재 경기 엔진은 요일이 아닌 주차로 움직입니다. 달력의 열은 날짜가 아니라 주차 카드를 정렬한 시각적 그리드이며 임의의 경기 날짜를 만들지 않습니다.</p></section>','/app/schedule')
 const jump=n=>{calendarPage=Math.max(0,Math.min(maxPage,n));schedule()}
 const prev=document.querySelector('[data-calendar-prev]'),next=document.querySelector('[data-calendar-next]'),now=document.querySelector('[data-calendar-now]')
 if(prev)prev.onclick=()=>jump(calendarPage-1)
 if(next)next.onclick=()=>jump(calendarPage+1)
 if(now)now.onclick=()=>jump(Math.floor((currentWeek-1)/14))
 document.querySelectorAll('.calendar-match').forEach(a=>a.onclick=e=>{e.preventDefault();go(a.getAttribute('href'))})
 await topbar()
}
async function match(id) {
  await loadChampionMeta()
  const current = await requireCareer(); if (!current) return
  const data = await api('/fixtures?id=' + current.id)
  const game = data.fixtures.find(item => item.id === id)
  if (!game) { shell('<p>경기를 찾지 못했습니다.</p>', '/app/schedule'); return }
  const series = game.series || {}
  let controls = `<p>${esc(game.competition)} ${esc(game.stage)} · ${esc(series.phase || game.state)}</p>`
  if (series.phase === 'choice') controls += `<button class="act" data-choice="priority" data-value="first">선픽</button><button class="act" data-choice="priority" data-value="second">후픽</button><button class="act" data-choice="side" data-value="blue">블루</button><button class="act" data-choice="side" data-value="red">레드</button>`
  if (series.phase === 'draft') {
    const champs = await api('/champions')
    controls += `<input id="champ" type="hidden"/><div class="champion-search"><input id="champion-pick-filter" placeholder="한국어 챔피언 이름 검색"/><span id="selected-champion">챔피언을 선택하세요</span><button class="act" id="pick">선택</button><button class="act" id="auto">남은 픽 자동</button></div><div class="champion-select-grid">${champs.champions.map(item => `<button class="champion-select-card" data-champ="${esc(item.name)}" data-name="${esc(championKo(item.name))}">${championIcon(item.name)}<span>${esc(championKo(item.name))}</span></button>`).join('')}</div>`
  }
  if (series.phase === 'swap') controls += `<p>스왑은 30초입니다. 역할 번호를 바꿉니다.</p><input id="swap-a" value="0"/><input id="swap-b" value="1"/><button class="act" id="swap">스왑</button>`
  if (series.phase === 'feedback') controls += `<input id="note" maxlength="300" placeholder="세트 피드백"/><button class="act" id="note-save">전달</button>`
  if (game.result) controls += `<p>결과 ${(game.result.score || []).join(':')}</p>`
  shell(`<div class="panel"><h2>${esc(game.opponent)}</h2>${controls}</div>`, '/app/match/' + id)
  document.querySelectorAll('[data-choice]').forEach(button => button.onclick = () => api('/draft-choice', {id, category:button.dataset.choice, value:button.dataset.value, manual:true}).then(() => draw()).catch(error => alert(error.message)))
  const pick = document.getElementById('pick')
  if (pick) pick.onclick = () => api('/draft-action', {id, champion:document.getElementById('champ').value.trim(), version:series.draft_version}).then(() => draw()).catch(error => alert(error.message))
  document.querySelectorAll('[data-champ]').forEach(button => button.onclick = () => {
    document.getElementById('champ').value=button.dataset.champ
    document.getElementById('selected-champion').textContent=button.dataset.name
    document.querySelectorAll('[data-champ]').forEach(c=>c.classList.toggle('selected',c===button))
  })
  const championFilter=document.getElementById('champion-pick-filter')
  if(championFilter)championFilter.oninput=()=>document.querySelectorAll('[data-champ]').forEach(button=>{
    button.hidden=!((button.dataset.name+' '+button.dataset.champ).toLowerCase().includes(championFilter.value.toLowerCase()))
  })
  const auto = document.getElementById('auto')
  if (auto) auto.onclick = () => api('/draft-auto', {id, version:series.draft_version}).then(() => draw()).catch(error => alert(error.message))
  const swap = document.getElementById('swap')
  if (swap) swap.onclick = () => api('/draft-swap', {id, first:Number(document.getElementById('swap-a').value), second:Number(document.getElementById('swap-b').value), version:series.swap_version}).then(() => draw()).catch(error => alert(error.message))
  const note = document.getElementById('note-save')
  if (note) note.onclick = () => api('/set-feedback', {id, note:document.getElementById('note').value}).then(() => draw()).catch(error => alert(error.message))
  await topbar()
}
async function players(query='',page=0,origin='all') {
  const current=await requireCareer();if(!current)return
  const data=await api('/people?id='+current.id+'&kind=player&origin='+origin+'&page='+page+'&query='+encodeURIComponent(query))
  const rows=data.people.filter(p=>origin==='all'||(origin==='real'?p.real_person:!p.real_person))
  shell(`<div class="panel"><h1>선수 데이터베이스</h1><p>전체 ${data.total}명 · ${page+1} / ${Math.max(1,Math.ceil(data.total/data.page_size))}페이지</p><form id="player-search" class="roster-controls"><input id="q" aria-label="선수 검색" placeholder="한국어 이름 · 닉네임 · 구단" value="${esc(query)}"/><button class="act">검색</button><select id="origin"><option value="all">실존·생성 전체</option><option value="real">실존 선수</option><option value="generated">생성 선수</option></select></form>${rosterTable(rows)}<div class="roster-controls"><button class="act" id="prev-page" ${page===0?'disabled':''}>이전</button><span>${page+1}페이지</span><button class="act" id="next-page" ${(page+1)*data.page_size>=data.total?'disabled':''}>다음</button></div></div>`,'/app/players')
  document.getElementById('origin').value=origin
  document.getElementById('player-search').onsubmit=e=>{e.preventDefault();players(document.getElementById('q').value,0,document.getElementById('origin').value)}
  document.getElementById('origin').onchange=e=>players(query,page,e.target.value)
  document.getElementById('prev-page').onclick=()=>players(query,page-1,origin)
  document.getElementById('next-page').onclick=()=>players(query,page+1,origin)
  await topbar()
}
function rosterStatus(person) {
  if(person.kind==='coach'||person.kind==='staff') return '코칭스태프 · 프런트'
  const assignment=String(person.assignment||person.squad||'')
  const secondTeam=Boolean(person.academy_affiliation||person.squad==='academy'||
    ['LCK CL','LDL'].includes(person.league))
  if(assignment==='first')return secondTeam?'2군 주전':'1군 주전'
  if(assignment==='reserve')return secondTeam?'2군 후보':'1군 후보'
  if(assignment==='academy')return '2군'
  if(assignment==='candidate')return '영입 후보'
  if(assignment==='prospect')return '육성 유망주'
  if(assignment==='trial')return '입단 테스트'
  if(assignment==='departed')return '계약 종료'
  if(assignment==='free'||!person.team)return 'FA · 무소속'
  if(assignment==='unclassified'||!assignment)return person.team?'명단 확인 중':'FA · 무소속'
  return '명단 확인 중'
}
function playerAttributePanel(analysis) {
  if(!analysis?.sections?.length)return '<section class="panel"><h2>세부 능력치</h2><p class="empty">게임 내 평가 데이터가 없습니다.</p></section>'
  return '<div class="fm-attribute-sections">'+analysis.sections.map(section=>
    '<section class="panel fm-attribute-card"><header><h2>'+esc(section.title)+'</h2><span>1~20</span></header>'+
    '<div class="fm-attribute-list">'+section.attributes.map(item=>{
      const level=Math.max(1,Math.min(20,Number(item.value)||1))
      const tone=level>=16?'elite':level>=12?'strong':level>=8?'average':'develop'
      return '<div class="fm-attribute-row"><span>'+esc(item.name)+'</span><div class="fm-attribute-bar"><i style="width:'+(level*5)+'%" class="'+tone+'"></i></div><b class="'+tone+'">'+level+'</b></div>'
    }).join('')+'</div></section>'
  ).join('')+'</div><p class="muted-note player-model-note">'+esc(analysis.note||'게임 내 시뮬레이션 평가입니다.')+'</p>'
}
function playerSeasonPanel(season) {
  if(!season?.available)return '<section class="panel"><h2>시즌 경기 성적</h2><p class="empty">'+esc(season?.reason||'기록된 경기 결과가 없습니다.')+'</p><p class="muted-note">솔로랭크와 프로 경기는 별도 기록이며, 출전하지 않은 경기의 통계를 만들어 표시하지 않습니다.</p></section>'
  const metrics=[['출전 세트',season.games+'세트'],['승리 / 패배',season.wins+'승 / '+season.losses+'패'],
    ['세트 승률',season.win_rate+'%'],['KDA',season.kda],['킬 / 데스 / 어시',season.kills+' / '+season.deaths+' / '+season.assists],
    ['평균 CS',season.avg_cs],['평균 피해량',Number(season.avg_damage).toLocaleString('ko-KR')],
    ['평균 골드',Number(season.avg_gold).toLocaleString('ko-KR')],['평균 게임 평점',season.rating]]
  const recent=(season.recent||[]).map(m=>'<div class="fm-recent-match"><span class="'+(m.won?'won':'lost')+'">'+(m.won?'승':'패')+'</span><div><b>'+esc(m.opponent||'상대 구단')+'</b><small>'+m.week+'주 · '+esc(championKo(m.champion)||m.champion||'챔피언 기록 없음')+'</small></div><strong>'+m.kills+' / '+m.deaths+' / '+m.assists+'</strong></div>').join('')
  return '<section class="panel fm-match-performance"><h2>'+season.season+'시즌 · 공식 게임 기록</h2><div class="fm-season-metrics">'+metrics.map(([label,value])=>'<div><small>'+esc(String(label))+'</small><strong>'+esc(String(value))+'</strong></div>').join('')+'</div><h3>최근 출전 기록</h3><div class="fm-recent-matches">'+(recent||'<p class="empty">최근 세트가 없습니다.</p>')+'</div><p class="muted-note">'+esc(season.note||'완료된 게임 내 프로 경기 기록만 집계합니다.')+'</p></section>'
}
function playerProfileSummary(analysis,scout) {
  const strengths=analysis?.strengths||[],weaknesses=analysis?.weaknesses||[]
  return '<section class="panel fm-player-scout"><h2>스카우트 요약</h2><div class="fm-scout-stars"><div><small>현재 능력</small>'+scoutStars(scout?.current_stars)+'</div><div><small>성장 잠재력</small>'+scoutStars(scout?.potential_stars)+'</div></div>'+
   '<h3>경기 내 강점</h3><div class="fm-trait-tags">'+strengths.map(x=>'<span class="positive">'+esc(x)+'</span>').join('')+'</div>'+
   '<h3>보완할 점</h3><div class="fm-trait-tags">'+weaknesses.map(x=>'<span>'+esc(x)+'</span>').join('')+'</div>'+
   '<p class="muted-note">능력치 강·약점은 게임 내 추정 평가입니다. 스카우트 별점은 구단 관찰 능력에 따라 달라질 수 있습니다.</p></section>'
}
function scoutStars(value) {
  if (value == null) return '<span class="unknown-rating">미평가</span>'
  const n=Math.round(Number(value)*2)/2
  const full=Math.floor(n), half=n%1!==0
  return `<span class="scout-stars" aria-label="5점 만점 ${n.toFixed(1)}점">${'★'.repeat(full)}${half?'½':''}<span class="stars-empty">${'☆'.repeat(Math.max(0,5-full-(half?1:0)))}</span><small>${n.toFixed(1)} / 5.0</small></span>`
}
function ratingGrid(values) {
  return `<div class="ability-grid">${Object.entries(values||{}).map(([key,v])=>`<div class="ability-line"><div><span>${esc(key)}</span><b>${Number(v).toFixed(0)}</b></div><div class="ability-track"><i style="width:${Math.max(0,Math.min(100,Number(v)||0))}%"></i></div></div>`).join('')||'<p>평가 데이터가 없습니다.</p>'}</div>`
}
function frontRoleLabel(person) {
  const key=String(person.staff_role||'')
  const dict={OWNER:'구단주',MANAGER:'감독',HEAD_COACH:'수석코치',COACH:'코치',GM:'단장',ANALYST:'분석관',DOCTOR:'팀 닥터',COMMUNITY:'홍보 담당'}
  if(dict[key])return dict[key]
  const raw=String(person.raw_role||'').toLowerCase()
  if(raw.includes('head')||raw.includes('수석'))return '수석코치'
  if(raw.includes('감독')||raw.includes('manager')&&!raw.includes('general'))return '감독'
  if(raw.includes('단장')||raw.includes('general manager'))return '단장'
  if(raw.includes('analyst')||raw.includes('분석'))return '분석관'
  if(raw.includes('doctor')||raw.includes('닥터'))return '팀 닥터'
  return person.kind==='coach'?'코치':'프런트'
}
async function frontDirectory(query='',page=0) {
  const careerItem=await requireCareer()
  if(!careerItem)return
  const data=await api('/people?id='+careerItem.id+'&kind=staff&page='+page+'&query='+encodeURIComponent(query))
  const rows=(data.people||[]).filter(p=>p.kind==='coach'||p.kind==='staff')
  const contents=rows.map(p=>'<tr><td>'+personLink(p)+'</td><td>'+esc(frontRoleLabel(p))+'</td><td>'+flagAndCountry(p)+'</td><td>'+esc(p.team||'FA / 무소속')+'</td><td>'+(p.real_person?'실존 프런트·코칭스태프':'생성 프런트·코칭스태프')+'</td></tr>').join('')
  shell('<div class="page-heading"><div><p class="eyebrow">CLUB PERSONNEL DATABASE</p><h1>프런트 · 코칭스태프 DB</h1><p>구단주와 감독은 구단 정보에서 확인하고, 코치·단장·분석관 등은 여기서 검색합니다.</p></div></div><section class="panel"><form id="front-search" class="roster-controls"><input id="front-q" placeholder="프런트 이름 또는 닉네임 검색" value="'+esc(query)+'"/><button class="act">검색</button></form><div class="table-scroll"><table class="roster-table"><thead><tr><th>이름 · 닉네임</th><th>직책</th><th>국적</th><th>소속팀</th><th>분류</th></tr></thead><tbody>'+contents+'</tbody></table></div>'+(rows.length?'':'<p class="empty">검색된 프런트 인물이 없습니다.</p>')+'<div class="roster-controls"><button class="act" id="front-prev" '+(page===0?'disabled':'')+'>이전</button><span>'+(page+1)+'페이지</span><button class="act" id="front-next" '+((page+1)*data.page_size>=data.total?'disabled':'')+'>다음</button></div></section>','/app/front-database')
  document.getElementById('front-search').onsubmit=e=>{e.preventDefault();frontDirectory(document.getElementById('front-q').value,0)}
  document.getElementById('front-prev').onclick=()=>frontDirectory(query,page-1)
  document.getElementById('front-next').onclick=()=>frontDirectory(query,page+1)
  await topbar()
}
async function player(id, tab) {
  const current=await requireCareer();if(!current)return
  const [detail,train,manage]=await Promise.all([api('/person?id='+current.id+'&person='+encodeURIComponent(id)),isOperator?Promise.resolve({players:[]}):api('/training?id='+current.id).catch(()=>({players:[]})),isOperator?Promise.resolve({}):api('/management?id='+current.id).catch(()=>({}))])
  if(tab==='overview'||tab==='stats')await loadChampionMeta()
  const person=detail.person,scout=detail.scouting?.scout,agency=detail.scouting?.agency,eco=detail.person?.economics||{}
  const analysis=detail.player_analysis?.attributes||null
  const performance=detail.player_analysis?.season||null
  const statusLabel=rosterStatus(person)
  const follows=isOperator?{follows:[]}:await api('/follows?id='+current.id)
  const following=(follows.follows||[]).some(f=>f.kind==='player'&&f.entity===person.nickname)
  const development=(train.players||[]).find(row=>row.person.id===id)
  const contract=(manage.contracts||[]).find(row=>row.person.id===id)
  const tabs=[['overview','선수 개요'],['stats','시즌 성적'],['report','스카우트 보고'],['personal','개인 정보'],['contract','계약'],['history','이력'],['career','커리어'],['compare','선수 비교']]
  const editEnabled=detail.can_edit_attributes===true&&person.kind==='player'
  if(editEnabled)tabs.push(['edit','능력치 편집'])
  const links=`<div class="tabs player-tabs">${tabs.map(([k,l])=>`<a class="${tab===k?'on':''}" href="/app/player/${esc(id)}/${k}">${l}</a>`).join('')}</div>`
  const joined=person.team?logoImg(person.league,person.team)+esc(displayTeam(person.league,person.team))+' · '+esc(person.league||''):'FA · 무소속'
  const isPlayer=person.kind==='player'
  const statsCount=analysis?.count||0
  const roleName=ROLE[person.role]||person.role||'포지션 미등록'
  const joinedText=person.team?logoImg(person.league,person.team)+
    '<a href="/app/team/'+encodeURIComponent(person.league||'')+'/'+encodeURIComponent(person.team)+'">'+esc(displayTeam(person.league,person.team))+'</a>'+
    '<span class="fm-player-league">'+esc(person.league||'')+'</span>':'<span>FA · 무소속</span>'
  const top='<header class="player-profile-heading fm-player-profile-heading">'+
    '<div class="player-profile-face">'+face(person.id,Boolean(person.photo))+'</div>'+
    '<div class="fm-player-heading-info"><p class="eyebrow">'+
       (isPlayer?'선수 프로필 · PLAYER REPORT':'구단 프런트 · STAFF REPORT')+'</p>'+
       '<h1>'+esc(person.nickname||person.display_name||person.real_name||'선수')+'</h1>'+
       '<p class="fm-player-subname">'+esc(person.real_name||'본명 정보 미등록')+
          ' · '+esc(roleName)+'</p>'+
       '<div class="fm-player-identity">'+flagAndCountry(person)+
          '<span class="fm-squad-badge">'+esc(statusLabel)+'</span></div>'+
       '<div class="player-team-line">'+joinedText+'</div>'+
       (!isOperator?'<button class="act player-follow-btn" id="player-follow">'+
         (following?'★ 선수 뉴스 팔로우 중':'☆ 선수 뉴스 팔로우')+'</button>':'')+
       (editEnabled?'<a class="act fm-editor-shortcut" href="/app/player/'+encodeURIComponent(id)+'/edit">⚙ 능력치 편집 · 운영자</a>':'')+
     '</div>'+
     '<div class="fm-player-head-stats">'+
       '<div><small>개인 솔로랭크</small><strong>'+esc(person.solo?.label||'기록 없음')+'</strong></div>'+
       '<div><small>소속 선수단</small><strong>'+esc(statusLabel)+'</strong></div>'+
       (isPlayer?'<div><small>게임 레이팅</small><strong>'+(eco.rating??'미평가')+' / 99</strong></div>':'')+
       (isPlayer?'<div><small>인지도</small><strong>'+(eco.fame??'미평가')+' / 100</strong></div>':'')+
       (isPlayer?'<div><small>게임 내 개별 능력</small><strong>'+
          (analysis?analysis.overall+' / 20':'평가 없음')+'</strong></div>':'')+
       (isPlayer?'<div><small>세부 평가 항목</small><strong>'+statsCount+'개</strong></div>':'')+
       (development?'<div><small>훈련 OVR</small><strong>'+development.ovr+'</strong></div>':'')+
     '</div></header>'
  let main=''
  if(tab==='overview') {
    if(!isPlayer) main='<div class="player-info-grid"><section class="panel"><h2>프런트 정보</h2>'+
      '<p>'+esc(frontRoleLabel(person))+'</p><p>'+flagAndCountry(person)+'</p>'+
      '<p>구단: '+joinedText+'</p></section></div>'
    else main='<div class="fm-player-dashboard">'+
      '<div class="fm-player-dashboard-main"><div class="fm-section-head"><h2>개별 능력치 · '+statsCount+
        '개</h2><span>FM 스타일 게임 능력 · 1~20</span></div>'+
        playerAttributePanel(analysis)+playerSeasonPanel(performance)+'</div>'+
      '<aside class="fm-player-dashboard-side">'+playerProfileSummary(analysis,scout)+
       '<section class="panel"><h2>포지션 · 역할 숙련</h2>'+
         '<div class="fm-position-primary"><span>'+esc(roleName)+'</span><strong>주 포지션</strong></div>'+
         '<p class="muted-note">'+esc(analysis?.role?.note||'등록된 포지션만 확인할 수 있습니다.')+'</p>'+
         '<h3>선수단 소속</h3><div class="fm-role-detail"><b>'+esc(statusLabel)+'</b>'+
           '<span>'+joinedText+'</span></div></section>'+
       '<section class="panel"><h2>계약 · 정보</h2><div class="fm-quickfacts">'+
         '<div><span>국적</span>'+flagAndCountry(person)+'</div>'+
         '<div><span>연봉</span><b>'+money(contract?.annual_salary??eco.annual_salary??person.salary)+'</b></div>'+
         '<div><span>시장가치</span><b>'+money(eco.market_value)+'</b></div>'+
         '<div><span>인지도</span><b>'+(eco.fame??'미평가')+' / 100</b></div>'+
         '<div><span>굿즈 순이익 예상</span><b>'+money(eco.merch_annual_profit)+'</b></div>'+
         '<div><span>계약 종료</span><b>'+esc(person.contract_end||'확인 중')+'</b></div>'+
         '<div><span>출전 세트</span><b>'+String(performance?.games||0)+'세트</b></div>'+
         '</div></section></aside></div>'
  }
  else if(tab==='stats') main=playerSeasonPanel(performance)+
    (isPlayer?'<section class="panel"><h2>능력치 · 시즌 성적의 차이</h2><p class="muted-note">'+
      '개별 능력은 게임 평가 모델의 추정값이고, KDA·CS·피해량은 실제로 진행된 LFM 경기만 집계합니다. '+
      '솔로랭크 전적은 프로 경기 성적에 포함하지 않습니다.</p></section>':'')
  else if(tab==='personal') main=`<section class="panel"><h2>개인 정보</h2><div class="info-pairs"><p>영문 닉네임 <b>${esc(person.nickname||'기록 없음')}</b></p><p>본명 <b>${esc(person.real_name||'기록 없음')}</b></p><p>국적 <b>${flagAndCountry(person)}</b></p><p>리그 <b>${esc(person.league||'무소속')}</b></p><p>지역 <b>${esc(person.region||person.nationality_name_ko||'정보 없음')}</b></p><p>포지션 <b>${esc(ROLE[person.role]||person.role||'정보 없음')}</b></p><p>솔로랭크 <b>${esc(person.solo?.label||'정보 없음')}</b></p></div></section>`
  else if(tab==='contract') {
    const expiryYear=contract?.expiry_season?2025+contract.expiry_season:null
    const expiryText=contract?.expiry_season?
      expiryYear+'년 · '+contract.expiry_season+'시즌 '+((contract.end_turn-1)%150+1)+'주':
      person.contract_end||'정보 없음'
    const minimum=Number(contract?.agent_asking_salary??contract?.annual_salary??0)
    const canRenew=!isOperator&&person.kind==='player'&&contract?.active===true&&contract.renewal_eligible===true
    const renewalPanel=canRenew?
      '<section class="panel"><h2>재계약 협상 · 에이전트</h2>'+
      '<p class="muted-note">계약 만료 시즌의 스토브리그입니다. 요구 연봉과 잔여 급여 예산을 확인하세요.</p>'+
      '<div class="row"><span>현재 연봉 <b>'+money(contract.annual_salary)+'</b></span>'+
      '<span>에이전트 최소 요구 <b>'+money(minimum)+'</b></span></div>'+
      '<div class="row"><label>제안 연봉<input id="player-renew-salary" type="number" min="'+minimum+'" step="100000" value="'+minimum+'"></label>'+
      '<label>계약 연장 기간<select id="player-renew-years"><option value="1">1시즌</option><option value="2">2시즌</option><option value="3">3시즌</option></select></label>'+
      '<button class="act" id="player-renew-submit">재계약 제안</button></div></section>':
      (!isOperator&&person.kind==='player'&&contract?.active?
       '<section class="panel"><h2>재계약 안내</h2><p>계약 만료 시즌('+
        esc(expiryYear??'확인 중')+'년)의 스토브리그(1~10주 또는 145~150주)에만 재계약할 수 있습니다.</p></section>':'')
    main='<section class="panel"><h2>계약 · 연봉 · 시장가치</h2><div class="info-pairs">'+
      '<p>계약 종료 <b>'+esc(expiryText)+'</b></p>'+
      '<p>연봉 <b>'+money(contract?.annual_salary??eco.annual_salary??person.salary)+'</b></p>'+
      '<p>계약 분류 <b>'+(contract?'구단 계약':'성적·인지도 기준 연봉 추정')+'</b></p>'+
      '<p>시장가치 <b>'+money(eco.market_value)+'</b></p>'+
      '<p>굿즈 연매출 예상 <b>'+money(eco.merch_annual_sales)+'</b></p>'+
      '<p>굿즈 연간 순이익 예상 <b>'+money(eco.merch_annual_profit)+'</b></p>'+
      '<p>계약 기간 <b>'+(contract?contract.remaining_turns+'주 남음':'구단 계약 정보 없음')+'</b></p>'+
      '<p>현재 상태 <b>'+(contract?(contract.active?'계약 중':'계약 종료'):'외부 구단 또는 FA')+'</b></p>'+
      '</div><h3>FM 게임 평가 기준</h3>'+
      '<p>'+esc(eco.criteria?.rating||'능력치·경기 성적 기준')+'</p>'+
      '<p>'+esc(eco.criteria?.fame||'경기 출전·인지도 기준')+'</p>'+
      '<p>'+esc(eco.criteria?.salary||'성적·인지도 기준 게임 연봉 추정')+'</p>'+
      '<p>'+esc(eco.criteria?.market_value||'레이팅·인지도·굿즈 판매 기대 수익 기준')+'</p></section>'+
      renewalPanel
  }
  else if(tab==='history') main=`<section class="panel"><h2>선수 이력</h2><p>현재 소속 ${joined}</p><p>최초 등록 구단: ${esc(person.registered_team||person.team||'정보 없음')}</p><p class="muted-note">경기·이적 기록은 커리어 진행에 따라 누적됩니다.</p></section>`
  else if(tab==='report') main='<div class="report-grid">'+
     '<section class="panel scout-report-card"><p class="eyebrow">PRIVATE SCOUTING</p>'+
       '<h2>구단 스카우트 보고서</h2><p>현재 능력</p>'+scoutStars(scout?.current_stars)+
       '<p>성장 잠재력</p>'+scoutStars(scout?.potential_stars)+
       '<div class="info-pairs"><p>평가 시즌 <b>'+(scout?.season||'-')+'시즌</b></p>'+
       '<p>스카우트 역량 <b>'+(scout?.scout_skill??'-')+' / 20</b></p>'+
       '<p>보고 신뢰도 <b>'+esc(scout?.confidence||'미평가')+'</b></p></div>'+
       '<p class="muted-note">'+esc(scout?.summary||'스카우팅 기록 없음')+'</p></section>'+
     '<section class="panel"><p class="eyebrow">ANNUAL REPORT</p><h2>기관 연례 평가</h2>'+
       scoutStars(agency?.current_stars)+
       '<p>'+(agency?.season||'-')+'시즌 · 연 1회 발표</p>'+
       '<p class="muted-note">'+esc(agency?.summary||'아직 발표된 평가가 없습니다.')+'</p></section></div>'+
     '<div class="fm-section-head"><h2>개별 능력치 · '+(analysis?.count||0)+'개</h2>'+
       '<span>1~20 · 게임 내 평가 모델</span></div>'+
     playerAttributePanel(analysis)
  else if(tab==='career') main=`<section class="panel"><h2>현재 선수 경력</h2><div class="info-pairs"><p>등록 구단 <b>${esc(person.team||'FA')}</b></p><p>선수단 분류 <b>${esc(statusLabel)}</b></p><p>프로 여부 <b>${esc(person.solo?.path_name||'확인되지 않음')}</b></p><p>개인 랭크 <b>${esc(person.solo?.label||'기록 없음')}</b></p></div><p class="muted-note">솔로랭크 성적과 공식 프로 경기 성적은 별도로 집계됩니다.</p></section>`
  else if(tab==='compare') {
    const result=await api('/player-comparisons?id='+current.id+'&person='+encodeURIComponent(id))
    main=`<section class="panel"><h2>동일 포지션 선수 비교</h2><p>${esc(ROLE[person.role]||person.role||'')} 포지션 · 게임 내 능력 수치가 가까운 선수</p><div class="table-scroll"><table><thead><tr><th>선수</th><th>구단</th><th>종합</th><th>기준 선수 대비</th><th>상세 보기</th></tr></thead><tbody>${(result.comparisons||[]).map(p=>`<tr><td><b>${esc(p.nickname)}</b></td><td>${esc(p.team)}</td><td>${p.rating}</td><td class="${p.gap>=0?'positive-gap':'negative-gap'}">${p.gap>0?'+':''}${p.gap}</td><td><a href="/app/player/${encodeURIComponent(p.id)}/compare">비교 대상 열기</a></td></tr>`).join('')}</tbody></table></div></section><section class="panel"><h2>기준 선수 능력치</h2>${playerAttributePanel(analysis)}</section>`
  }
  else if(tab==='edit'&&editEnabled) {
    const profile=detail.attributes
    if(!profile?.groups?.length){
      main='<section class="panel"><h2>선수 능력치 편집</h2><p class="err">능력치 자료를 불러오지 못했습니다.</p></section>'
    } else {
      const formSections=profile.groups.map(group=>
        '<fieldset class="fm-admin-stat-group"><legend>'+esc(group.name)+'</legend>'+
        group.keys.map(key=>'<label class="fm-admin-stat-field"><span>'+esc(key)+'</span>'+
          '<input type="number" required inputmode="numeric" min="1" max="20" step="1" data-attribute="'+esc(key)+'" value="'+Number(profile.ratings[key])+'"/><small> / 20</small></label>').join('')+
        '</fieldset>').join('')
      main='<section class="panel fm-attribute-editor"><p class="eyebrow">LEAGUE OPERATOR · PLAYER DATABASE</p>'+
        '<h2>'+esc(person.nickname||person.real_name||'선수')+' · 개별 능력치 수정</h2>'+
        '<p>운영자만 변경할 수 있습니다. 저장한 수치는 다른 감독 계정에서도 조회되며 게임 내 스카우팅 기본 능력치에 적용됩니다.</p>'+
        '<div class="fm-editor-meta"><span>수정 버전 '+profile.revision+'</span>'+
          '<span>마지막 변경 '+esc(profile.updated_at||'아직 수정하지 않음')+'</span>'+
          '<span>게임 능력치 / 최대 20</span></div>'+
        '<form id="operator-attribute-form"><div class="fm-admin-stats-grid">'+formSections+'</div>'+
        '<div class="fm-editor-footer"><p id="player-stat-editor-message" role="status">실존 선수의 공식 실력이 아닌 게임 내 능력치입니다.</p>'+
        '<button class="act fm-editor-save" type="submit">30개 능력치 저장</button></div></form></section>'
    }
  }
  else return go('/app/player/'+encodeURIComponent(id)+'/overview')
  shell(`<div class="player-profile">${top}${links}${main}<div class="player-footer"><a href="/app/players">선수 DB로 돌아가기</a>${person.team?`<a href="/app/team/${encodeURIComponent(person.league||'')}/${encodeURIComponent(person.team)}">구단 보기</a>`:''}</div></div>`,'/app/player/'+id)
  const fb=document.getElementById('player-follow')
  if(fb)fb.onclick=()=>api('/follows',{id:current.id,kind:'player',entity:person.nickname,enabled:!following})
    .then(()=>player(id,tab)).catch(e=>alert(e.message))
  const renewButton=document.getElementById('player-renew-submit')
  if(renewButton)renewButton.onclick=async()=>{
    const salary=Number(document.getElementById('player-renew-salary').value)
    const years=Number(document.getElementById('player-renew-years').value)
    if(!confirm('에이전트 조건으로 재계약을 제안할까요?'))return
    try {
      renewButton.disabled=true
      await api('/management',{id:current.id,action:'renew',person:id,annual_salary:salary,years})
      await player(id,'contract')
    } catch(error) {
      alert(error.message)
      renewButton.disabled=false
    }
  }
  const editor=document.getElementById('operator-attribute-form')
  if(editor)editor.onsubmit=async event=>{
    event.preventDefault()
    const msg=document.getElementById('player-stat-editor-message')
    const button=editor.querySelector('button[type=submit]')
    try{
      const ratings={}
      editor.querySelectorAll('input[data-attribute]').forEach(input=>{
        const value=Number(input.value)
        if(!Number.isInteger(value)||value<1||value>20)throw Error('모든 선수 능력치는 1~20의 정수여야 합니다.')
        ratings[input.dataset.attribute]=value
      })
      if(Object.keys(ratings).length!==30)throw Error('30개 능력치를 모두 입력하세요.')
      button.disabled=true
      msg.textContent='선수별 능력치를 저장하는 중입니다.'
      await api('/operator/person-attributes',{person:id,ratings})
      go('/app/player/'+encodeURIComponent(id)+'/overview')
    }catch(error){
      msg.textContent=error.message
      button.disabled=false
    }
  }
  await topbar()
}
function seasonStanding(row) {
  if(!row)return {rank:'미집계',played:0,wins:0,losses:0,sets_won:0,sets_lost:0,diff:0}
  return {...row,diff:(row.sets_won||0)-(row.sets_lost||0),rank:row.rank==null?'미집계':row.rank+'위'}
}
function leagueStandingsTable(rows,league,currentTeam='') {
  return `<div class="table-scroll"><table class="league-table"><thead><tr><th>순위</th><th>구단</th><th>경기</th><th>승</th><th>패</th><th>세트 득실</th><th>득실차</th></tr></thead><tbody>${(rows||[]).map((r,i)=>`<tr class="${r.team===currentTeam?'mine':''}"><td>${r.rank==null?'—':r.rank}</td><td>${logoImg(league,r.team)}<a href="/app/team/${encodeURIComponent(league)}/${encodeURIComponent(r.team)}">${esc(displayTeam(league,r.team))}</a></td><td>${r.played||0}</td><td>${r.wins||0}</td><td>${r.losses||0}</td><td>${r.sets_won||0}:${r.sets_lost||0}</td><td>${(r.sets_won||0)-(r.sets_lost||0)>0?'+':''}${(r.sets_won||0)-(r.sets_lost||0)}</td></tr>`).join('')}</tbody></table></div>${(rows||[]).every(r=>!r.played)?'<p class="muted-note">아직 완료된 경기가 없습니다. 첫 경기 이후 순위가 확정됩니다.</p>':''}`
}
function frontOfficeCard(p) {
  const role=String(p.role_key||'')
  const hasNationality=p.show_nationality!==false && role!=='OWNER' && role!=='EXECUTIVE'
  const country=hasNationality?flagAndCountry(p):''
  const details=role==='OWNER'?'구단 소유·운영 조직':role==='EXECUTIVE'?'대표자':role==='MANAGER'?'담당 감독':'프런트·코치진'
  return '<div class="front-person"><div class="front-role">'+esc(p.role||'직책 미확인')+'</div><strong>'+esc(p.name||'정보 미등록')+'</strong>'+country+'<small>'+esc(details)+'</small></div>'
}
function frontOfficePanel(data) {
  const positions=[...(data.front_office||[])]
  if(!positions.some(p=>p.role_key==='OWNER'))positions.unshift({role:'구단주',name:'정보 미등록',role_key:'OWNER'})
  if(!positions.some(p=>p.role_key==='MANAGER'))positions.push({role:'감독',name:'부임 감독 미등록',role_key:'MANAGER'})
  return `<div class="front-office-grid">${positions.map(frontOfficeCard).join('')}</div>`
}
function resultStrip(games) {
  return (games||[]).map(g=>`<div class="form-result-row"><span class="${g.won?'win':'loss'}">${g.won?'승':'패'}</span><div><b>${esc(g.opponent)}</b><small>${g.season}시즌 ${g.week}주 · 세트 ${(g.score||[]).join(':')}</small></div></div>`).join('')||'<p class="empty">아직 종료된 공식 경기가 없습니다.</p>'
}
function latestTeamNews(data) {
  return (data.news||[]).map(n=>`<div class="fm-news-row"><small>${n.season}시즌 ${n.week}주 · 구단 소식</small><b>${esc(n.headline)}</b><p>${esc((n.body||'').slice(0,145))}</p></div>`).join('')||'<p class="empty">아직 등록된 구단 뉴스가 없습니다.</p>'
}
async function team(league,name,tab) {
  const data=await api('/club-dossier?league='+encodeURIComponent(league)+'&team='+encodeURIComponent(name))
  const idn=data.identity,s=seasonStanding(data.standing)
  const myCareer=isOperator?null:await career()
  const follows=myCareer?await api('/follows?id='+myCareer.id):{follows:[]}
  const isFollowed=(follows.follows||[]).some(f=>f.kind==='team'&&f.entity===name)
  const active=tab==='staff'?'front':tab
  const tabs=[['overview','구단 개요'],['roster','1군·2군'],['front','프런트'],['finance','재정'],['matches','경기'],['news','뉴스'],['history','구단 역사'],...(isOperator?[['editor','운영자 수정']]:[])]
  const links=`<div class="tabs team-tabs">${tabs.map(([k,l])=>`<a class="${active===k?'on':''}" href="/app/team/${encodeURIComponent(league)}/${encodeURIComponent(name)}/${k}">${l}</a>`).join('')}</div>`
  const table=leagueStandingsTable(data.standings||[],league,name)
  const rowNotes=`<div class="fm-metrics"><div><small>리그 순위</small><strong>${esc(s.rank)}</strong></div><div><small>경기</small><strong>${s.played}</strong></div><div><small>승 / 패</small><strong>${s.wins}승 ${s.losses}패</strong></div><div><small>세트 득실</small><strong>${s.sets_won}:${s.sets_lost} (${s.diff>0?'+':''}${s.diff})</strong></div><div><small>담당 감독</small><strong>${esc(data.manager||'정보 미등록')}</strong></div></div>`
  const teamPlayers=(data.players||[]).filter(p=>p.kind==='player')
  const rosterCards=teamPlayers.filter(p=>p.assignment!=='reserve').slice(0,5).map(p=>`<a class="fm-player-line" href="/app/player/${encodeURIComponent(p.id)}">${face(p.id,Boolean(p.photo))}<span><small>${esc(ROLE[p.role]||p.role||'선수')}</small><b>${esc(nickname(p))}</b></span></a>`).join('')||'<p class="empty">1군 주전 선수단이 등록되지 않았습니다.</p>'
  const finance=data.finances?.initialized?`<div class="fm-finance-totals"><div><small>보유 현금</small><strong>${money(data.finances.cash)}</strong></div><div><small>이적 예산</small><strong>${money(data.finances.transfer_budget)}</strong></div><div><small>연봉 총액</small><strong>${money(data.finances.annual_payroll)}</strong></div></div>${cashGraph(data.cash_history||[])}`:'<p class="empty">이 구단의 재정 내역은 공개되지 않았거나 아직 기록이 없습니다.</p>'
  let main=''
  if(active==='overview')main=`<div class="fm-club-dashboard"><section class="panel fm-dashboard-standing"><h2>리그 순위 <a href="/app/league/${encodeURIComponent(league)}">리그 상세</a></h2>${table}</section><section class="panel fm-dashboard-squad"><h2>이번 시즌 1군 · ${teamPlayers.length}명</h2>${rosterCards}<a class="panel-link" href="/app/team/${encodeURIComponent(league)}/${encodeURIComponent(name)}/roster">전체 명단 보기</a></section><section class="panel fm-dashboard-front"><h2>프런트·코칭스태프</h2>${frontOfficePanel(data)}</section><section class="panel fm-dashboard-news"><h2>구단 뉴스</h2>${latestTeamNews(data)}</section><section class="panel fm-dashboard-finance"><h2>재정 흐름</h2>${finance}</section><section class="panel fm-dashboard-form"><h2>최근 공식 경기</h2>${resultStrip(data.recent||[])}</section></div>`
  else if(active==='roster')main=`<section class="panel"><h2>1군 선수 · ${teamPlayers.length}명</h2>${rosterTable(teamPlayers)}</section><section class="panel"><h2>2군 육성 선수 · ${(data.academy||[]).length}명</h2>${rosterTable((data.academy||[]).filter(p=>p.kind==='player'))}</section>`
  else if(active==='front')main=`<section class="panel"><h2>프런트 및 코칭스태프</h2><p class="muted-note">선수와 구분하여 구단주, 감독, 수석코치, 코치, 단장 및 실무진을 직책별로 표시합니다.</p>${frontOfficePanel(data)}</section><section class="panel"><h2>구단 운영 정보</h2><p>담당 감독 · ${esc(data.manager||'미등록')}</p><p>구단주·운영 주체 · ${esc(data.owner||'미등록')}</p><p>대표이사·운영 대표 · ${esc(data.owner_info?.representative||'공개 정보 없음')}</p></section>`
  else if(active==='finance')main=`<div class="fm-club-finance"><section class="panel"><h2>재정 요약</h2>${finance}</section><section class="panel"><h2>거래 원장</h2>${(data.finances?.ledger||[]).map(n=>`<div class="row"><span>${n.season}시즌 ${n.week}주 · ${esc(n.description)}</span><b>${money(n.amount)}</b></div>`).join('')||'<p class="empty">표시할 거래 원장이 없습니다.</p>'}</section></div>`
  else if(active==='matches')main=`<section class="panel"><h2>${data.season||''}시즌 공식 경기 결과</h2>${resultStrip(data.recent||[])}</section><section class="panel"><h2>시즌 성적</h2>${rowNotes}</section>`
  else if(active==='news')main=`<section class="panel"><h2>구단 소식</h2>${latestTeamNews(data)}</section>`
  else if(active==='history')main=clubHistoryPanel(data.history)
  else if(active==='editor'&&isOperator)main='<section class="panel"><h2>운영자 구단 정보 수정</h2><p>구단의 원래 식별자는 유지되며, 새 이름과 로고가 화면과 향후 역사에 반영됩니다.</p><form id="operator-club-editor"><label>새 구단명<input type="text" name="name" minlength="2" maxlength="48" value="'+esc(data.display_name||name)+'" required/></label><label>대표 로고 변경(선택)<input type="file" name="logo" accept="image/png,image/jpeg,image/webp"/></label><button class="act" type="submit">구단 변경 사항 저장</button><p class="err" id="editor-error"></p></form></section>'+clubHistoryPanel(data.history)
  else return go('/app/team/'+encodeURIComponent(league)+'/'+encodeURIComponent(name)+'/overview')
  shell(`<div class="fm-team-page"><header class="fm-team-header">${logoImg(idn.league,idn.team)}<div><p class="eyebrow">CLUB INFORMATION · ${esc(idn.league)}</p><h1>${esc(data.display_name||idn.team)}</h1>${myCareer?'<button class="act" id="follow-this-team">'+(isFollowed?'★ 구단 뉴스 팔로우 중':'☆ 구단 뉴스 팔로우')+'</button>':''}<p>${esc(data.season||'현재')}시즌 · 1군 ${teamPlayers.length}명 · 2군 ${(data.academy||[]).length}명 · 프런트 ${(data.front_office||[]).length}명</p></div><a href="/app/league/${encodeURIComponent(league)}" class="act">${esc(league)} 리그 보기</a></header>${rowNotes}${links}${main}</div>`,'/app/team/'+encodeURIComponent(league)+'/'+encodeURIComponent(name))
  document.documentElement.style.setProperty('--team',idn.color||'#17324d')
  const editor=document.getElementById('operator-club-editor')
  if(editor)editor.onsubmit=async e=>{e.preventDefault();try{
    const newName=editor.elements.name.value.trim()
    const file=editor.elements.logo.files[0]
    const update={league,team:name,name:newName}
    if(file)update.logo_data=await readClubLogo(file)
    await api('/operator/club-identity',update)
    media.brandings=null;careerCache=null;draw()
  }catch(error){document.getElementById('editor-error').textContent=error.message}}
  const followButton=document.getElementById('follow-this-team')
  if(followButton)followButton.onclick=()=>api('/follows',{id:myCareer.id,kind:'team',entity:name,enabled:!isFollowed})
    .then(()=>team(league,name,tab)).catch(e=>alert(e.message))
  if(token()&&careerId())await topbar()
}
async function readClubLogo(file) {
  if(!file)return ''
  if(file.size>80000 || !['image/png','image/jpeg','image/webp'].includes(file.type))
    throw Error('80KB 이하 PNG, JPEG, WebP 로고만 업로드할 수 있습니다.')
  return await new Promise((resolve,reject)=>{
    const reader=new FileReader()
    reader.onload=()=>resolve(String(reader.result||''))
    reader.onerror=()=>reject(Error('이미지 파일을 읽지 못했습니다.'))
    reader.readAsDataURL(file)
  })
}
function clubHistoryPanel(history){
  return '<section class="panel"><h2>구단 역사 · 변경 기록</h2>'+
    ((history||[]).length?history.map(h=>'<div class="club-timeline-event"><small>'+h.season+'시즌 '+h.week+'주</small><b>'+esc(h.headline)+'</b><p>'+esc(h.details||'')+'</p></div>').join(''):
     '<p class="empty">아직 기록된 개명·스폰서·프랜차이즈 변경 이력이 없습니다.</p>')+
    '</section>'
}
async function sponsorsPage(){
 const current=await requireCareer();if(!current)return
 const data=await api('/sponsor-offers?id='+current.id)
 const existing=data.contracts||[],offers=(data.offers||[]).filter(o=>o.status==='offered')
 const now=current.season
 const active=existing.filter(c=>c.end_season>=now)
 const main=active.find(c=>c.tier==='main'),support=active.filter(c=>c.tier==='support')
 const banner=(record,title)=>record?
  '<div class="sponsor-record"><strong>'+esc(record.company)+'</strong><span>'+esc(title)+'</span><b>'+money(record.amount)+'</b><small>'+record.start_season+'~'+record.end_season+'시즌</small></div>':
  '<div class="sponsor-record empty-sponsor"><strong>아직 계약 없음</strong><small>'+esc(title)+'</small></div>'
 const offersByTier=tier=>offers.filter(o=>o.tier===tier).map(o=>
   '<article class="sponsor-offer-card"><small>'+esc(o.region)+' · '+(tier==='main'?'메인':'지역·장비·식음료 파트너')+'</small><h3>'+esc(o.company)+'</h3><strong>'+money(o.amount)+'</strong><p>게임 시뮬레이션 가상 후원 계약</p><button class="act" data-sponsor="'+o.id+'">계약 수락</button></article>').join('')||
    '<p class="empty">'+(tier==='main'?'이 시즌에는 메인 스폰서 제안이 없습니다.':'새로운 보조 스폰서 제안이 없습니다.')+'</p>'
 shell('<div class="page-heading"><div><p class="eyebrow">PARTNERSHIPS</p><h1>구단 스폰서십</h1><p>메인 파트너 1곳 · 보조 파트너 최대 '+data.max_support+'곳. 약팀·2군도 지역 후원을 받을 수 있습니다.</p></div></div><div class="sponsor-tier-grid"><section class="panel"><h2>메인 스폰서 · 1개 슬롯</h2>'+banner(main,'메인 계약')+'<h3>새 메인 제안</h3><div class="sponsor-offers">'+offersByTier('main')+'</div></section><section class="panel"><h2>보조 스폰서 · '+support.length+'/'+data.max_support+'</h2><div class="sponsor-support-list">'+(support.map(c=>banner(c,'보조 계약')).join('')||'<p class="empty">계약 중인 보조 스폰서가 없습니다.</p>')+'</div><h3>새 보조 제안</h3><div class="sponsor-offers">'+offersByTier('support')+'</div></section></div><p class="muted-note">'+esc(data.notice||'실제 후원 관계가 아닙니다.')+'</p>','/app/sponsors')
 document.querySelectorAll('[data-sponsor]').forEach(btn=>btn.onclick=async()=>{
   if(!confirm('게임 내 가상 스폰서 계약을 수락하시겠습니까?'))return
   try{await api('/sponsor-accept',{id:current.id,offer:Number(btn.dataset.sponsor)});careerCache=null;await sponsorsPage()}
   catch(e){alert(e.message)}
 })
 await topbar()
}
async function clubIdentityHistory(){
 const current=await requireCareer();if(!current)return
 const league=current.club_profile?.league||''
 const data=await api('/club-identity?league='+encodeURIComponent(league)+'&team='+encodeURIComponent(current.name))
 shell('<div class="page-heading"><h1>구단의 역사</h1><p>선택·창단 시 구단명과 로고가 영구 확정됩니다. 이후에는 운영자만 수정할 수 있습니다.</p></div>'+clubHistoryPanel(data.history),'/app/club-history')
 await topbar()
}
async function leagueIndex() {
  const [board,current]=await Promise.all([api('/clubs'),isOperator?Promise.resolve(null):career()])
  const mine=current?.club_profile?.league||''
  const leagues=[...new Set((board.clubs||[]).map(c=>c.league).filter(Boolean))]
    .sort((a,b)=>(a===mine?-1:b===mine?1:0)||(leagueInfo(a)[2]===leagueInfo(b)[2]?a.localeCompare(b):leagueInfo(a)[2]==='1부'?-1:1))
  const cards=leagues.map(league=>{
    const [flag,region,level]=leagueInfo(league)
    const teams=board.clubs.filter(c=>c.league===league)
    return '<a class="league-choice-card '+(league===mine?'my-league':'')+'" href="/app/league/'+encodeURIComponent(league)+'"><div>'+leagueIcon(league)+'<div><b>'+esc(league)+'</b><span>'+esc(region)+' · '+esc(level)+(league===mine?' · 내 리그':'')+'</span></div></div><p>참가 구단 '+teams.length+'개 · 순위·일정·구단 정보 보기</p></a>'
  }).join('')
  shell('<div class="page-heading"><div><p class="eyebrow">LEAGUES</p><h1>리그 둘러보기</h1><p>내 리그부터 확인하고, 로고를 눌러 다른 리그의 순위·팀·경기 일정을 볼 수 있습니다.</p></div></div><div class="fm-league-index">'+cards+'</div>','/app/leagues')
  await topbar()
}
async function leagueOverview(league) {
  const data=await api('/league-overview?league='+encodeURIComponent(league))
  const standings=data.standings||[],completed=(data.fixtures||[]).filter(g=>g.state==='finished'),upcoming=(data.fixtures||[]).filter(g=>g.state!=='finished')
  const games=fixtures=>fixtures.map(g=>'<div class="fm-match-item"><small>'+g.season+'시즌 '+g.week+'주 · '+esc(g.stage||'정규 시즌')+'</small><div><b>'+esc(displayTeam(league,g.home))+'</b><strong>'+(g.score?g.score.join(' : '):'VS')+'</strong><b>'+esc(displayTeam(league,g.away))+'</b></div></div>').join('')||'<p class="empty">아직 등록된 경기가 없습니다.</p>'
  const teams=(data.clubs||[]).map(c=>'<a class="fm-league-club" href="/app/team/'+encodeURIComponent(league)+'/'+encodeURIComponent(c.team)+'">'+logoImg(league,c.team)+'<span>'+esc(displayTeam(league,c.team))+'</span><small>'+(c.kind==='user'?'유저 감독':'AI 구단')+'</small></a>').join('')
  const headlines=(data.franchise_news||[]).map(n=>'<div class="fm-news-row"><small>'+n.season+'시즌 · 프랜차이즈 소식</small><b>'+esc(n.headline)+'</b></div>').join('')
  shell('<div class="fm-league-page"><header class="fm-team-header">'+leagueIcon(league)+'<div><p class="eyebrow">'+esc(leagueInfo(league)[1])+' · '+esc(leagueInfo(league)[2])+'</p><h1>'+esc(league)+'</h1><p>'+data.season+'시즌 '+data.week+'주차 · 참가 구단 '+(data.clubs||[]).length+'팀</p></div><a class="act" href="/app/leagues">리그 목록</a></header><div class="fm-league-metrics"><div><small>참가 구단</small><strong>'+(data.clubs||[]).length+'</strong></div><div><small>종료 경기</small><strong>'+completed.length+'</strong></div><div><small>예정 경기</small><strong>'+upcoming.length+'</strong></div></div><div class="fm-league-dashboard"><section class="panel fm-league-ranking"><h2>'+esc(league)+' 순위표</h2>'+leagueStandingsTable(standings,league)+'</section><section class="panel fm-league-games"><h2>최근 경기 결과</h2>'+games(completed.slice(-8).reverse())+'<h2>다음 일정</h2>'+games(upcoming.slice(0,8))+'</section><section class="panel fm-league-clubs"><h2>참가 구단 · 클릭해서 이동</h2><div class="fm-league-club-list">'+(teams||'<p class="empty">참가 구단이 없습니다.</p>')+'</div></section>'+(headlines?'<section class="panel fm-league-clubs"><h2>리그 주요 소식</h2>'+headlines+'</section>':'')+'</div></div>','/app/leagues')
  await topbar()
}
const soloState={region:'KR',scope:'all',role:'',page:0}
function soloTier(label){
 if(label.startsWith('챌린저'))return ['챌린저','challenger','👑']
 if(label.startsWith('그랜드마스터'))return ['그랜드마스터','grandmaster','💎']
 if(label.startsWith('마스터'))return ['마스터','master','✦']
 return [label.split(' ')[0],'regular','◆']
}
async function solo() {
 const current=await requireCareer();if(!current)return
 const params=new URLSearchParams({id:current.id,region:soloState.region,role:soloState.role,scope:soloState.scope})
 const data=await api('/solo-ladder?'+params.toString())
 const rows=data.rows||[], page=soloState.page;
 const visible=rows.slice(page*100,(page+1)*100)
 const tabs=(values,key,selected,labels={})=>'<div class="solo-control-tabs">'+values.map(v=>
   '<button class="solo-filter '+(v===selected?'selected':'')+'" data-solo-'+key+'="'+esc(v)+'">'+esc(labels[v]??v??'전체')+'</button>').join('')+'</div>'
 const link=row=>'<a class="solo-player-name" href="/app/player/'+encodeURIComponent(row.id)+'">'+face(row.id,true)+'<span><b>'+esc(row.nickname)+'</b><small>'+esc(ROLE[row.role]||row.role)+' · '+esc(row.club||'솔로랭크 전용')+'</small></span></a>'
 const medal=row=>{const [name,type,symbol]=soloTier(row.label)
   return '<span class="solo-rank-icon '+type+'">'+symbol+'</span><span class="solo-rank-text"><b>'+name+'</b><small>'+esc(row.label)+'</small></span>'}
 const actions=row=>row.path==='amateur'?
   '<button class="act" data-solo-talk="'+esc(row.id)+'">유망주 면담</button>':
   row.path==='prospect'&&row.career_id===current.id&&row.debut_ready?
   '<button class="act" data-solo-debut="'+esc(row.id)+'">프로 데뷔</button>':''
 const roster=(data.mine||[]).map(row=>'<div class="solo-roster-person">'+link(row)+medal(row)+actions(row)+'</div>').join('')||'<p class="empty">아직 영입한 솔로랭크 유망주가 없습니다. 일반인 필터에서 선수를 탐색하고 면담하세요.</p>'
 const lines=visible.map(row=>'<div class="solo-ladder-row">'+
   '<strong class="solo-placement">#'+row.rank+'</strong>'+link(row)+
   '<div class="solo-tier-cell">'+medal(row)+'</div>'+
   '<div class="solo-games">'+(row.games||0)+'게임<small>'+esc(row.path_name)+'</small></div>'+
   actions(row)+'</div>').join('')||'<p class="empty">선택한 지역과 조건의 랭크 선수가 없습니다.</p>'
 shell('<div class="page-heading"><div><p class="eyebrow">RANKED SOLO / DUO</p><h1>솔로랭크 · 상위 500인</h1><p>프로 경기와 독립적인 지역별 개인 랭크 · 프로 선수는 마스터 이상 유지</p></div></div>'+
   '<section class="panel solo-dashboard"><h2>서버 지역</h2>'+tabs(data.regions||[],'region',soloState.region)+
   '<div class="solo-dual-controls"><div><h3>랭크 범위</h3>'+tabs(['all','mine','amateur'],'scope',soloState.scope,{all:'지역 전체',mine:'내 구단만',amateur:'일반인·유망주'})+'</div>'+
   '<div><h3>포지션</h3>'+tabs(['','TOP','JUNGLE','MID','ADC','SUPPORT'],'role',soloState.role,{'':'전체','TOP':'탑','JUNGLE':'정글','MID':'미드','ADC':'원딜','SUPPORT':'서포터'})+'</div></div></section>'+
   '<div class="solo-multi-column"><section class="panel"><h2>'+esc(data.region)+' 서버 개인 랭킹 · '+rows.length+'명 조회</h2>'+
   '<div class="solo-rank-board">'+lines+'</div><div class="solo-pagination">'+
   Array.from({length:Math.ceil(rows.length/100)},(_,i)=>'<button class="'+(i===page?'selected':'')+'" data-solo-page="'+i+'">'+(i+1)+'</button>').join('')+'</div></section>'+
   '<section class="panel solo-my-prospects"><h2>내 팀의 육성·면담 선수</h2><p class="muted-note">일반인을 면담해 2군 유망주로 만들고 성장시키면 프로 데뷔시킬 수 있습니다.</p>'+roster+'</section></div>','/app/solo')
 const change=(name,value)=>{soloState[name]=value;soloState.page=0;solo()}
 document.querySelectorAll('[data-solo-region]').forEach(b=>b.onclick=()=>change('region',b.dataset.soloRegion))
 document.querySelectorAll('[data-solo-role]').forEach(b=>b.onclick=()=>change('role',b.dataset.soloRole))
 document.querySelectorAll('[data-solo-scope]').forEach(b=>b.onclick=()=>change('scope',b.dataset.soloScope))
 document.querySelectorAll('[data-solo-page]').forEach(b=>b.onclick=()=>{soloState.page=Number(b.dataset.soloPage);solo()})
 document.querySelectorAll('[data-solo-talk]').forEach(b=>b.onclick=()=>api('/solo-talk',{id:current.id,person:b.dataset.soloTalk})
    .then(()=>solo()).catch(e=>alert(e.message)))
 document.querySelectorAll('[data-solo-debut]').forEach(b=>b.onclick=()=>api('/solo-debut',{id:current.id,person:b.dataset.soloDebut})
    .then(()=>solo()).catch(e=>alert(e.message)))
 await topbar()
}
async function transfers() {
  const current = await requireCareer(); if (!current) return
  const [offers, activity,ai] = await Promise.all([api('/transfer-offers?id=' + current.id), api('/transfer-activity?id=' + current.id), api('/ai-transfer-decisions?league='+encodeURIComponent(current.club_profile?.league||'')).catch(()=>({decisions:[]}))])
  shell(`<div class="panel"><h2>이적 제안</h2><input id="pid" placeholder="선수 id"/><input id="salary" value="0"/><input id="fee" value="0"/><button class="act" id="quote">제안</button>${offers.offers.map(item => `<div class="row">#${item.id} ${esc(item.state)} 연봉 ${money(item.annual_salary)} 이적료 ${money(item.fee)}<button class="act" data-offer="${item.id}" data-choice="accept">수락</button><button class="act" data-offer="${item.id}" data-choice="decline">거절</button><button class="act" data-offer="${item.id}" data-choice="cancel">취소</button></div>`).join('')}</div><div class="panel"><h2>AI 구단의 이적 판단</h2><p>예상 경기 기여도와 인지도·굿즈 순이익, 연봉 부담을 비교해 영입합니다.</p>${(ai.decisions||[]).slice(0,20).map(d=>'<div class="row"><b>'+esc(d.club)+' · '+esc(d.player)+'</b><span>'+esc(d.decision==='signed-free-agent'?'FA 영입 확정':'영입 관심')+'</span><small>레이팅 '+d.rating+' · 인지도 '+d.fame+' · 굿즈 예상 순이익 '+money(d.merch_profit)+' · 연봉 '+money(d.salary)+'</small></div>').join('')||'<p>AI 구단의 이적 판단 기록이 아직 없습니다.</p>'}</div><div class="panel"><h2>이적 기록</h2>${activity.events.map(item => `<div class="row">${esc(item.buyer_name || '')} ${money(item.fee)}</div>`).join('')}</div>`, '/app/transfers')
  document.getElementById('quote').onclick = () => api('/transfer-offer', {id:current.id, person:document.getElementById('pid').value.trim(), annual_salary:Number(document.getElementById('salary').value), fee:Number(document.getElementById('fee').value), years:2, pitch:'development'}).then(() => draw()).catch(error => alert(error.message))
  document.querySelectorAll('[data-offer]').forEach(button => button.onclick = () => api('/transfer-response', {id:current.id, offer:Number(button.dataset.offer), choice:button.dataset.choice}).then(() => draw()).catch(error => alert(error.message)))
  await topbar()
}
async function shortlist() {
  const current = await requireCareer(); if (!current) return
  const data = await api('/shortlist?id=' + current.id)
  shell(`<div class="panel"><h2>영입 명단</h2>${(data.people || []).map(person => `<div class="row">${personLink(person)}<button class="act" data-off="${esc(person.id)}">제외</button></div>`).join('') || '<p>명단이 비어 있습니다. 선수 프로필에서 담을 수 있습니다.</p>'}</div>`, '/app/shortlist')
  document.querySelectorAll('[data-off]').forEach(button => button.onclick = () => api('/shortlist', {id:current.id, person:button.dataset.off, enabled:false}).then(() => draw()))
  await topbar()
}
async function competition(selected='') {
  const current=await requireCareer();if(!current)return
  const [data,q]=await Promise.all([api('/competitions?id='+current.id+(selected?'&league='+encodeURIComponent(selected):'')),api('/qualification?season='+current.season)])
  shell(`<div class="page-heading"><div><p class="eyebrow">COMPETITIONS & QUALIFICATION</p><h1>대회 · 국제대회 진출권</h1><p>${current.season}시즌 · 2026 규정 적용</p></div></div><section class="panel"><h2>리그별 현황</h2><select id="league-picker">${data.leagues.map(l=>`<option ${l===data.league?'selected':''}>${esc(l)}</option>`).join('')}</select>${widget('standings',{standings:data.standings,club:current.name,league:data.league})}</section><section class="panel"><h2>지역별 출전권</h2><div class="table-scroll"><table><thead><tr><th>리그</th><th>First Stand</th><th>MSI 출전권</th><th>MSI 본선 직행</th><th>월즈 기본</th><th>월즈 현재 확정</th><th>추가 시드 상태</th></tr></thead><tbody>${q.allocations.map(r=>`<tr><td>${esc(r.league)}</td><td>${r.first_stand_slots}</td><td>${r.msi_slots}</td><td>${r.msi_bracket_slots}${r.msi_second_seed_pending?' · 2시드 대기':''}</td><td>${r.worlds_base}</td><td>${r.worlds_confirmed_slots}</td><td>${r.worlds_champion_pending?'MSI 우승팀의 자국 플레이오프 진출 확인 대기':r.worlds_extra_seed?'추가 지역 시드 확보':r.worlds_champion_slot?'MSI 우승팀 출전권 확보':'국제대회 결과 대기'}</td></tr>`).join('')}</tbody></table></div><p>First Stand: MSI 2번 시드 본선 직행 혜택. MSI: 우승팀 월즈 조건부 진출, 차순위 지역 추가 시드.</p><a class="text-link" href="${q.source}" target="_blank" rel="noopener">공식 규정 보기 ↗</a></section><section class="panel"><h2>국제대회 일정</h2>${q.events.map(e=>`<div class="event-card"><b>${esc(e.name)} · ${e.entrants}팀</b><p>${current.season}시즌 ${e.start_week}주 ~ ${e.end_week}주</p><small>${esc(e.format)}</small></div>`).join('')}</section><section class="panel"><h2>등록된 경기 규정</h2>${data.rules.map(r=>`<div class="row"><b>${esc(r.competition)}</b><span>${esc(r.stage)} · BO${r.best_of}</span></div>`).join('')}</section>`,'/app/competition')
  document.getElementById('league-picker').onchange=e=>competition(e.target.value)
  await topbar()
}
async function historyPage(season=0,selectedLeague='LCK') {
  const data=await api('/honors'+(season?'?season='+encodeURIComponent(season):''))
  const all=data.awards||[]
  const league=data.leagues.includes(selectedLeague)?selectedLeague:(data.leagues[0]||'LCK')
  const local=all.filter(a=>a.league===league)
  const teams=[['퍼스트 팀',1],['세컨드 팀',2],['써드 팀',3]].map(([title,rank])=>
    '<section class="panel"><h2>'+title+'</h2>'+Object.entries(ROLE).map(([role,label])=>{
      const a=local.find(a=>a.category==='all_pro'&&a.role===role&&a.award_rank===rank)
      return '<div class="row"><b>'+esc(label)+'</b><span>'+(a?'<a href="/app/player/'+encodeURIComponent(a.person_id)+'">'+esc(a.person_name)+'</a> · '+esc(a.club):'기록 부족 · 미선정')+'</span><small>'+(a?esc(a.status==='final'?'시즌 수상':'잠정 집계'):'')+'</small></div>'
    }).join('')+'</section>').join('')
  const single=(type,title)=>{
    const a=local.find(a=>a.category===type)
    return '<section class="panel"><h2>'+title+'</h2>'+(a?'<div class="row"><b>'+esc(a.person_name)+'</b><span>'+esc(a.club)+'</span><small>'+esc(a.status==='final'?'수상 확정':'잠정 집계')+'</small></div>':'<p>자격을 충족한 경기 기록이 없습니다.</p>')+'</section>'
  }
  const mvp=all.find(a=>a.category==='worlds_mvp')
  const worlds='<section class="panel"><h2>월즈 MVP</h2>'+(mvp?'<div class="row"><b>'+esc(mvp.person_name)+'</b><span>'+esc(mvp.club)+'</span></div>':'<p>월즈 결승 경기 기록을 기다리고 있습니다.</p>')+'</section>'
  const filters='<section class="panel"><div class="roster-controls"><label>시즌 <select id="history-season">'+data.seasons.map(s=>'<option value="'+s+'" '+(s===data.season?'selected':'')+'>'+s+'시즌</option>').join('')+'</select></label><label>리그 <select id="history-league">'+data.leagues.map(s=>'<option value="'+esc(s)+'" '+(s===league?'selected':'')+'>'+esc(s)+'</option>').join('')+'</select></label></div></section>'
  shell('<div class="page-heading"><div><p class="eyebrow">HALL OF FAME</p><h1>리그 역사관</h1><p>'+data.season+'시즌 · '+(data.finalized?'수상 확정':'시즌 진행 중')+'</p></div></div>'+filters+'<div class="grid3">'+teams+'</div><div class="grid3">'+single('coach','올해의 감독')+single('rookie','올해의 신인')+worlds+'</div><p>'+esc(data.rules)+'</p>','/app/history')
  document.getElementById('history-season').onchange=e=>historyPage(Number(e.target.value),document.getElementById('history-league').value)
  document.getElementById('history-league').onchange=e=>historyPage(data.season,e.target.value)
  await topbar()
}
async function dataHub() {
 const current=await requireCareer();if(!current)return
 await loadChampionMeta()
 const data=await api('/analytics?id='+current.id+'&season='+current.season)
 const champs=data.champions||[]
 const tiles=champs.map(c=>'<div class="champ-meta-card">'+championIcon(c.champion)+
  '<div class="champ-meta-name"><b>'+esc(championKo(c.champion))+'</b><small>픽 '+c.games+' · 밴 '+c.bans+'</small></div>'+
  '<div class="champ-meta-tier tier-'+esc(c.tier)+'">'+esc(c.tier)+'</div>'+
  '<div class="champ-meta-figures"><div><small>승률</small><b>'+(c.win_rate==null?'기록 없음':c.win_rate+'%')+'</b></div>'+
   '<div><small>픽률</small><b>'+c.pick_rate+'%</b></div><div><small>밴률</small><b>'+c.ban_rate+'%</b></div></div>'+
  '<div class="champ-meter"><span style="width:'+Math.min(100,Number(c.presence)||0)+'%"></span></div>'+
  '<small>'+esc(c.tier_source||'')+'</small></div>').join('')
 const maxBan=Math.max(1,...champs.map(c=>c.bans))
 const bands=champs.filter(c=>c.bans>0).sort((a,b)=>b.bans-a.bans).slice(0,8).map(c=>
   '<div class="champ-ban-row">'+championIcon(c.champion)+'<span>'+esc(championKo(c.champion))+'</span>'+
   '<div class="champ-ban-bar"><span style="width:'+(c.bans/maxBan*100)+'%"></span></div><b>'+c.bans+'</b></div>').join('')
 shell('<div class="page-heading"><div><p class="eyebrow">CHAMPION DATA LAB</p><h1>챔피언 메타·픽밴 분석</h1><p>게임 내 수집 경기 기준 · '+esc(data.patch||CHAMP_PATCH)+' 패치</p></div><a class="act" href="/app/solo">지역별 솔로랭크 500위 보기</a></div>'+
  '<div class="fm-league-metrics"><div><small>분석 시리즈</small><strong>'+data.series+'</strong></div><div><small>게임 세트</small><strong>'+data.sets+'</strong></div><div><small>기준 패치</small><strong>'+esc(data.patch||CHAMP_PATCH)+'</strong></div></div>'+
  '<div class="data-hub-layout"><section class="panel"><h2>챔피언 티어·승률·픽률·밴률</h2>'+
   '<p class="muted-note">'+esc(data.sample_notice||'리그 전체가 아닌 내 경기 데이터입니다.')+'</p>'+
   (tiles?'<div class="champ-meta-grid">'+tiles+'</div>':'<p class="empty">아직 완료한 경기가 없습니다. 경기 결과가 누적되면 실제 게임 내 픽·밴 통계가 표시됩니다.</p>')+'</section>'+
   '<section class="panel"><h2>가장 많이 밴한 챔피언</h2>'+(bands||'<p class="empty">밴 기록이 없습니다.</p>')+
   '<h2>솔로랭크 랭킹</h2><p>KR · CN · EUW · NA 등 지역별 500위 랭킹과 내 구단 선수별 순위를 확인하세요.</p>'+
   '<a class="act" href="/app/solo">개인 랭크 데이터 이동</a></section></div>','/app/data')
 await topbar()
}
const communityState={league:'',category:'all',page:0,query:''}
async function community(postId) {
  const current=await requireCareer();if(!current)return
  const league=communityState.league||current.club_profile?.league||'LCK'
  if(postId){
    const data=await api('/community-post?post='+postId)
    const p=data.post
    const comments=(p.comments_list||[]).map(c=>
      '<div class="row community-comment"><div><b>'+esc(c.author?.name||'팬')+'</b>'+
      '<small> · '+esc(c.full_time||'')+'</small><p>'+esc(c.body)+'</p></div></div>').join('')
    shell('<div class="page-heading"><div><p class="eyebrow">FAN COMMUNITY · '+esc(p.league)+'</p>'+
      '<h1>'+esc(p.title)+'</h1><p>'+esc(p.category_name)+' · '+p.game_time+
      ' · 작성자 '+esc(p.author?.name||'팬')+'</p></div><a class="act" href="/app/community">게시판으로</a></div>'+
      '<section class="panel"><p>'+esc(p.body)+'</p><p class="muted-note">추천 '+p.up+
      ' · 비추천 '+p.down+' · 조회 '+p.views+' · NPC 팬 게시글</p></section>'+
      '<section class="panel"><h2>팬 댓글 '+(p.comments_list||[]).length+'개</h2>'+
      (comments||'<p class="empty">아직 댓글이 없습니다.</p>')+'</section>','/app/community')
    await topbar();return
  }
  const params=new URLSearchParams({league,category:communityState.category,
    page:String(communityState.page),query:communityState.query})
  const data=await api('/community?'+params.toString())
  communityState.page=data.page
  const categories=[['all','전체'],['popular','인기'],...Object.entries(data.categories||{})]
  const tabs=categories.map(([id,label])=>
    '<button class="act community-chip '+(communityState.category===id?'selected':'')+
    '" data-community-category="'+esc(id)+'">'+esc(label)+'</button>').join('')
  const leagueChoices=(data.leagues||[]).map(l=>
    '<option value="'+esc(l)+'" '+(l===league?'selected':'')+'>'+esc(l)+'</option>').join('')
  const rows=(data.posts||[]).map(p=>
    '<a class="row community-post" href="/app/community/'+p.id+'"><div>'+
    '<small>'+esc(p.category_name)+' · '+esc(p.author?.name||'팬')+
    ' · '+esc(p.game_time)+'</small><h3>'+esc(p.title)+'</h3></div>'+
    '<span>추천 '+p.up+' · 댓글 '+p.comments+' · 조회 '+p.views+'</span></a>').join('')
  shell('<div class="page-heading"><div><p class="eyebrow">FAN COMMUNITY</p>'+
    '<h1>'+esc(league)+' 팬 게시판</h1>'+
    '<p>경기·계약·이적·감독 결정에 따른 NPC 팬의 칭찬, 불만, 욕설, 밈, 토론. 모든 반응은 게임 내 가상 게시글입니다.</p>'+
    '</div></div><section class="panel"><div class="row"><label>리그 선택 <select id="community-league">'+
    leagueChoices+'</select></label><strong>게시글 '+data.total+'개</strong></div>'+
    '<div class="community-categories">'+tabs+'</div>'+
    '<form class="row" id="community-search"><input id="community-query" type="search" maxlength="100" placeholder="게시글 검색" value="'+esc(communityState.query)+'"/>'+
    '<button class="act" type="submit">검색</button></form></section>'+
    '<section class="panel"><h2>팬 반응</h2>'+
    (rows||'<p class="empty">아직 이 조건에 맞는 게시글이 없습니다.</p>')+
    '</section><div class="row community-pagination">'+
    '<button class="act" id="community-prev" '+(data.page===0?'disabled':'')+'>이전</button>'+
    '<span>'+(data.page+1)+' / '+Math.max(1,Math.ceil(data.total/data.page_size))+' 페이지</span>'+
    '<button class="act" id="community-next" '+((data.page+1)*data.page_size>=data.total?'disabled':'')+'>다음</button>'+
    '</div>','/app/community')
  document.getElementById('community-league').onchange=e=>{
    communityState.league=e.target.value;communityState.page=0;community()
  }
  document.querySelectorAll('[data-community-category]').forEach(button=>button.onclick=()=>{
    communityState.category=button.dataset.communityCategory;communityState.page=0;community()
  })
  document.getElementById('community-search').onsubmit=e=>{
    e.preventDefault()
    communityState.query=document.getElementById('community-query').value.trim()
    communityState.page=0;community()
  }
  document.getElementById('community-prev').onclick=()=>{communityState.page--;community()}
  document.getElementById('community-next').onclick=()=>{communityState.page++;community()}
  await topbar()
}
async function draw() {
  const path = location.pathname.slice(BASE.length) || "/"
  if (!token()) { login(); return }
  if (!Object.keys(media.colors).length) {
    const [colors, logos] = await Promise.all([fetch(BASE + '/media/club-colors.json').then(r => r.ok?r.json():{}).catch(()=>({})), fetch(BASE + '/media/club-assets.json').then(r => r.ok?r.json():{}).catch(()=>({}))])
    media = {colors, logos, brandings:null,academyParents:{},leagueLogos:{}}
  }
  try {
    worldState=await api('/world');isOperator=worldState.operator===true
    if(media.brandings===null) {
      const visual=await api('/club-brandings')
      media.brandings=visual.brandings||{}
      media.academyParents=visual.academy_parents||{}
      media.leagueLogos=await fetch(BASE+'/media/league-logos.json').then(r=>r.ok?r.json():{}).catch(()=>({}))
    }
    if(isOperator){const observed=await career();if(path==='/app/operator')return await operatorDesk();if(path==='/app/manager')return go('/app/operator');if(!observed&&(path==='/app/home'||path==='/'))return await operatorDesk();if(!observed&&path==='/app/schedule')return await worldSchedule();if(!observed&&!['/app/clubs','/app/history','/app/players','/app/leagues','/app/sponsors','/app/competition','/app/news','/app/community'].includes(path)&&!/^\/app\/(player|team|league|entity)\//.test(path))return go('/app/clubs')}
    if(!managerProfile)managerProfile=await api('/manager-profile')
    if(!isOperator && !managerProfile.complete && path!=='/app/manager')return go('/app/manager')
    if(path==='/app/manager')return await managerSetup()
    if (path === '/' || path === '/app' || path === '/app/') return await continueCareer()
    const entityPath=path.match(/^\/app\/entity\/(manager|owner)\/(\d+)$/)
    if(entityPath){const item=await api('/entity?kind='+entityPath[1]+'&entity='+entityPath[2]);shell(`<div class="page-heading"><div><p class="eyebrow">${entityPath[1]==='owner'?'CLUB OWNER':'MANAGER'}</p><h1>${esc(item.name)}</h1></div></div><section class="panel"><h2>${esc(item.club||item.company||'인물 정보')}</h2>${Object.entries(item.stats||{}).map(([key,value])=>`<div class="metric-pair"><span>${esc(key)}</span><b>${value} / 20</b></div>`).join('')}</section>`,path);await topbar();return}
    if (path === '/app/clubs') return await clubs()
    if (path === '/app/onboarding') return await onboarding()
    if (path === '/app/home') return await home()
    if (path === '/app/inbox') return await inbox()
    if (path === '/app/news') return await news()
    if (path === '/app/squad') return await squad('first')
    if (path === '/app/academy') return await squad('academy')
    if (path === '/app/tactics') return await tactics()
    if (path === '/app/training') return await training()
    if (path === '/app/staff') return await managementPage('staff')
    if (path === '/app/front-database') return await frontDirectory()
    if (path === '/app/medical') return await managementPage('medical')
    if (path === '/app/relations') return await managementPage('relations')
    if (path === '/app/finance') return await managementPage('finance')
    if (path === '/app/vision') return await managementPage('vision')
    if (path === '/app/schedule') return await schedule()
    if (path === '/app/history') return await historyPage()
    if (path === '/app/players') return await players()
    if (path === '/app/solo') return await solo()
    if (path === '/app/transfers') return await transfers()
    if (path === '/app/shortlist') return await shortlist()
    if (path === '/app/competition') return go('/app/leagues')
    if (path === '/app/leagues') return await leagueIndex()
    if (path === '/app/sponsors') return await sponsorsPage()
    if (path === '/app/club-identity-settings') return go('/app/club-history')
    if (path === '/app/club-history') return await clubIdentityHistory()
    const leaguePath=path.match(/^\/app\/league\/(.+)$/)
    if(leaguePath)return await leagueOverview(decodeURIComponent(leaguePath[1]))
    if (path === '/app/data') return await dataHub()
    let matchPath = path.match(/^\/app\/match\/(\d+)$/)
    if (matchPath) return await match(Number(matchPath[1]))
    let personPath = path.match(/^\/app\/player\/([^/]+)(?:\/([^/]+))?$/)
    if (personPath) return await player(decodeURIComponent(personPath[1]), personPath[2] || 'overview')
    let teamPath = path.match(/^\/app\/team\/([^/]+)\/([^/]+)(?:\/([^/]+))?$/)
    if (teamPath) return await team(decodeURIComponent(teamPath[1]), decodeURIComponent(teamPath[2]), teamPath[3] || 'overview')
    let postPath = path.match(/^\/app\/community(?:\/(\d+))?$/)
    if (postPath) return await community(postPath[1] ? Number(postPath[1]) : 0)
    go('/app/home')
  } catch (error) {
    shell(`<p class="err">${esc(error.message)}</p>`, path)
  }
}
document.addEventListener('click',event=>{const a=event.target.closest('a[href]');if(!a||event.ctrlKey||event.metaKey||event.button!==0)return;let href=a.getAttribute('href');if(href.startsWith(BASE+'/app')||href.startsWith('/app')){event.preventDefault();event.stopImmediatePropagation();document.querySelectorAll('details[open]').forEach(d=>d.open=false);go(href)}},true)
new MutationObserver(()=>{if(!BASE)return;document.querySelectorAll('a[href^="/app"],img[src^="/media"]').forEach(el=>{const attr=el.tagName==='A'?'href':'src';el.setAttribute(attr,BASE+el.getAttribute(attr))})}).observe(document.getElementById('app'),{childList:true,subtree:true})
window.addEventListener('popstate', draw)

// The authoritative season/week lives on the server, never in each player's
// browser. Every logged-in tab detects the operator's update without user action.
// Reloading the current URL also refetches match schedules, rosters, finances,
// news, community and other derived views; a partial topbar redraw is insufficient.
let worldSyncBusy=false
let worldSyncReloading=false
async function syncGlobalTurn() {
  if(!token()||worldSyncBusy||worldSyncReloading)return
  worldSyncBusy=true
  try {
    const fresh=await api('/world')
    if(!worldState){worldState=fresh;return}
    if(fresh.version===worldState.version&&fresh.season===worldState.season&&fresh.week===worldState.week)return
    worldSyncReloading=true
    worldState=fresh
    careerCache=null
    window.location.reload()
  } catch(_error) {
    // Offline clients will catch up on their next successful check.
  } finally {worldSyncBusy=false}
}
// At most about one second of sync delay in foreground tabs. Browsers may
// throttle hidden tabs, so catch up immediately on focus/visibility restore.
setInterval(syncGlobalTurn,1000)
window.addEventListener('focus',syncGlobalTurn)
window.addEventListener('pageshow',syncGlobalTurn)
document.addEventListener('visibilitychange',()=>{if(!document.hidden)syncGlobalTurn()})
draw()
