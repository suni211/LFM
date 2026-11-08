const BASE = location.pathname.startsWith('/rift') ? '/rift' : ''
const NAV = [
  ['홈', '/app/home', '경기'],
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
  ['리그', '/app/leagues', '대회'],
  ['선수 DB', '/app/players', '대회'],
  ['솔로랭크', '/app/solo', '대회'],
  ['이적', '/app/transfers', '영입'],
  ['영입 명단', '/app/shortlist', '영입'],
  ['재정', '/app/finance', '구단'],
  ['데이터', '/app/data', '구단'],
  ['스폰서', '/app/sponsors', '구단'],
  ['구단 로고', '/app/club-identity-settings', '구단'],
  ['비전', '/app/vision', '구단'],
  ['커뮤니티', '/app/community', '구단']
]
const WIDGETS = {cash:'현금 흐름',
  news: '뉴스', inbox: '우편', standings: '리그 순위', next: '다음 경기', squad: '선수단',
  budget: '이적 예산', wages: '급여', schedule: '일정', staff: '스태프', medical: '의료',
  board: '구단주·팬', form: '최근 경기'
}
const ROLE = {TOP:'탑', JUNGLE:'정글', MID:'미드', ADC:'원딜', SUPPORT:'서포터'}
let media = {colors:{}, logos:{}, brandings:null}
let careerCache = null
let managerProfile = null
let isOperator = false
let worldState = null

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
  const name=raw||entry?.[1]||'국적 미등록'
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
function face(id, available=true) { if(!available)return '<span class="face-frame"><span class="face-placeholder" title="등록된 얼굴 없음">●</span></span>';return `<span class="face-frame"><img class="face" alt="선수 얼굴" src="${BASE}/media/portraits/${esc(id)}.png" onerror="this.style.display='none';this.nextElementSibling.hidden=false"/><span class="face-placeholder" hidden title="등록된 얼굴 없음">●</span></span>` }
function logoImg(league, team, overrideBrand=null) {
  const key=league+'\n'+team
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
 return '<span class="league-emblem league-emblem-'+tone+'" title="'+esc(region+' '+level)+'"><span class="league-emblem-flag">'+flag+'</span><strong>'+esc(league.length>8?league.slice(0,3).toUpperCase():league)+'</strong></span>'
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
  const categories=isOperator?[['리그 관리',['home','clubs','competition','schedule']],['인물 · 구단',['players']]]:[['구단',['home','inbox','news','finance','vision','community','staff','front-database']],['선수단',['squad','academy','medical','relations','players','solo']],['전술·훈련',['tactics','training']],['영입',['transfers','shortlist']],['대회·경기',['schedule','leagues','competition','data']],...(isOperator?[['운영',['clubs']]]:[])]
  const selected=NAV.find(n=>n[1]===path)?.[0]||'구단 관리'
  const menu=categories.map(([label,keys])=>`<details class="nav-category"><summary>${label}<span>⌄</span></summary><div class="dropdown">${keys.map(key=>{const item=NAV.find(n=>n[1]==='/app/'+key)||[key==='clubs'?(isOperator?'구단 조회':'구단 선택'):key,'/app/'+key];return `<a href="${item[1]}" class="${path===item[1]?'on':''}">${item[0]}</a>`}).join('')}</div></details>`).join('')
  document.getElementById('app').innerHTML=`<div id="shell"><header id="masthead"><div id="top"></div><nav id="navigation"><a class="brand" href="/app/home">R/M<span>RIFT MANAGER</span></a>${menu}${isOperator?'<span class="account-link">운영자 · 구단 운영 불가</span>':'<a class="account-link" href="/app/manager">감독 프로필</a>'}<button id="logout" aria-label="로그아웃">로그아웃</button></nav></header><main id="view" aria-label="${esc(selected)}">${body}</main></div>`
  document.getElementById('logout').onclick=()=>{localStorage.removeItem('rift-token');localStorage.removeItem('rift-career');careerCache=null;location.href=BASE+'/'}
}
async function topbar() {
  const current=isOperator?null:await career();const world=await api('/world');const bar=document.getElementById('top');if(!bar)return
  const league=current?.club_profile?.league||'',name=isOperator?'리그 운영':current?displayTeam(league,current.name):'구단 선택'
  document.documentElement.style.setProperty('--team',teamColor(league,name))
  const fixtures=current?(await api('/fixtures?id='+current.id)).fixtures:[]
  const due=(fixtures||[]).find(g=>g.state==='queued')
  bar.innerHTML=`<div class="club-identity">${current?careerLogo(current):logoImg(league,name)}<div><b>${esc(name)}</b><small>${esc(league)} · 온라인 리그</small></div></div><div class="search-wrap"><label class="sr-only" for="global-search">통합 검색</label><input id="global-search" placeholder="선수, 스태프, 구단 검색" autocomplete="off"/><div id="search-results" hidden></div></div><div class="week"><small>현재 시즌</small><b>${world.season}시즌 ${world.week}주차</b></div>${isOperator?'':`<button class="continue" id="vote">${due?'경기 진행':world.ready?'준비 완료':'다음으로'} <span>❯❯</span></button>`}`
  if(!isOperator)document.getElementById('vote').onclick=async()=>{try{if(due)return go('/app/match/'+due.id);if(!current)return go('/app/clubs');careerCache=null;const fresh=await career();await api('/advance',{id:fresh.id,version:fresh.version});careerCache=null;draw()}catch(e){alert(e.message)}}
  const input=document.getElementById('global-search'),results=document.getElementById('search-results');let generation=0,timer
  input.oninput=()=>{const g=++generation;clearTimeout(timer);results.hidden=true;const q=input.value.trim();if(!q)return;timer=setTimeout(async()=>{try{const data=await api('/search?query='+encodeURIComponent(q));if(g!==generation||!results.isConnected)return;results.innerHTML=(data.results||[]).map(item=>{const href=item.kind==='team'?'/app/team/'+encodeURIComponent(item.league)+'/'+encodeURIComponent(item.team):item.kind==='manager'||item.kind==='owner'?'/app/entity/'+item.kind+'/'+encodeURIComponent(item.id):'/app/player/'+encodeURIComponent(item.id);return `<a href="${href}"><b>${esc(item.label)}</b><small>${esc(item.subtitle)}</small></a>`}).join('')||'<p>검색 결과가 없습니다.</p>';results.hidden=false}catch(e){if(g===generation){results.innerHTML='<p>검색을 다시 시도해 주세요.</p>';results.hidden=false}}},180)}
  input.onkeydown=e=>{if(e.key==='Escape')results.hidden=true};input.onblur=()=>setTimeout(()=>{results.hidden=true},160)
}
function login() {
  document.getElementById('app').innerHTML = `<div class="entry"><section class="entry-story"><span class="entry-mark">R/M · CAREER MODE</span><h1>당신의 팀.<br><em>당신의 역사.</em></h1><p>하부 리그의 작은 구단에서 출발해 국제 무대까지 올라가세요.</p><div class="entry-facts"><span>104 WEEKS / SEASON</span><span>CLUB MANAGEMENT</span><span>ONLINE CAREER</span></div></section><form class="login" id="gate"><small>MANAGER ACCESS</small><h1>RIFT MANAGER</h1><p>감독 계정을 만들고 커리어를 시작하세요.</p><p class="err" id="err" role="alert"></p><label for="name">계정 이름</label><input id="name" autocomplete="username" maxlength="30" required placeholder="계정 ID"/><label for="password">비밀번호 · 10~128자</label><input id="password" type="password" autocomplete="current-password" minlength="10" maxlength="128" required placeholder="비밀번호"/><div class="entry-actions"><button class="act" type="button" id="in">로그인</button><button class="act" type="button" id="up">새 감독 계정 만들기</button></div><small>감독 닉네임은 가입 후 영문 2~20자로 설정합니다.</small></form></div>`
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
async function operatorDesk(path='/app/home') {
  const data=await api('/operator/world'),q=data.qualification
  const fixtures=data.fixtures.map(g=>`<tr><td>${g.season}시즌 ${g.week}주</td><td>${esc(g.competition)} · ${esc(g.stage)}</td><td>${esc(g.team)} vs ${esc(g.opponent)}</td><td>BO${g.best_of}</td><td>${esc({scheduled:'예정',queued:'진행 중',finished:'종료',failed:'처리 확인 필요'}[g.state]||g.state)}</td></tr>`).join('')
  shell(`<div class="page-heading"><div><p class="eyebrow">LEAGUE OPERATIONS</p><h1>${path==='/app/schedule'?'전체 경기 일정':'리그 운영 현황'}</h1><p>운영자 전용 · 팀을 맡거나 선수단·전술을 조작할 수 없습니다.</p></div></div><div class="grid3"><section class="panel"><h2>온라인 리그</h2><b>${data.world.season}시즌 ${data.world.week}주</b></section><section class="panel"><h2>구단</h2><b>${data.clubs.length}개 · 유저 구단 ${data.clubs.filter(c=>c.kind==='user').length}개</b></section><section class="panel"><h2>등록 경기</h2><b>${data.fixtures.length}경기</b></section></div><section class="panel"><h2>국제대회 일정</h2>${q.events.map(e=>`<div class="event-card"><b>${esc(e.name)} · ${e.entrants}팀</b><p>${data.world.season}시즌 ${e.start_week}주 ~ ${e.end_week}주</p><small>${esc(e.format)}</small></div>`).join('')}</section><section class="panel"><h2>서버에 등록된 경기 일정</h2>${fixtures?`<div class="table-scroll"><table><thead><tr><th>시즌 · 주차</th><th>대회</th><th>대진</th><th>방식</th><th>상태</th></tr></thead><tbody>${fixtures}</tbody></table></div>`:'<p class="empty">아직 생성된 경기 일정이 없습니다.</p>'}</section><p><a class="act" href="/app/competition">리그 순위·출전권 보기</a> · <a href="/app/clubs">구단 조회</a></p>`,path)
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
  const proposals=isOperator?board.clubs.map(c=>({team_key:c.team_key,team:c.team,league:c.league,power:c.power,available:!c.claimed||c.kind==='ai',description:'운영자 구단 조회'})):(jobOffers.offers||[])
  const open=mine.careers.map(c=>`<div class="row">${careerLogo(c)}<b>${esc(c.name)}</b><span>${esc(c.club_profile?.league||'')} · ${c.season}시즌 ${c.week}주</span><button class="act" data-open="${c.id}">이어하기</button></div>`).join('')
  const available=proposals.map(c=>`<div class="club-choice ${c.available?'':'club-locked'}">${logoImg(c.league,c.team)}<div><b>${esc(displayTeam(c.league,c.team))}</b><small>${esc(c.league)} · 파워 ${c.power??'미집계'} · ${isOperator?'운영자 조회':'부임 제안 '+c.ordinal+'/5'}</small><p>${esc(c.description||'')}</p></div><button class="act" data-team="${esc(c.team_key)}" ${c.available?'':'disabled'}>${c.available?'제안 수락':'부임 마감'}</button></div>`).join('')
  const leagues=board.leagues||[]
  shell(`<div class="page-heading"><div><p class="eyebrow">START YOUR CAREER</p><h1>감독 커리어 시작</h1><p>하위 리그 또는 파워랭킹이 낮은 구단에서 시작하세요. 최상위 강팀은 경력이 필요합니다.</p></div></div>${open?`<section class="panel"><h2>내 커리어</h2>${open}</section>`:''}<div class="career-choice-grid"><section class="panel club-creation"><h2>2부 리그 신생 구단 창단</h2><p>구단 이름, 3자 영문 약자, 전용 로고와 홈 컬러를 설정하세요.</p><form id="new-club"><label>구단 이름<input name="clubName" required minlength="2" maxlength="40" placeholder="예: Rising Phoenix"/></label><label>약자 (영문 대문자 3자)<input name="short" required maxlength="3" minlength="3" pattern="[A-Z]{3}" placeholder="RPH" style="text-transform:uppercase"/></label><label>참가할 2부 리그<select name="league">${leagues.map(l=>`<option value="${esc(l)}" ${l==='LCK CL'?'selected':''}>${esc(l)}</option>`).join('')}</select></label><label>홈 컬러<input name="color" type="color" value="#254a7a"/></label><label>엠블럼 모양<select name="emblem"><option value="shield">방패</option><option value="star">별</option><option value="crown">왕관</option><option value="bolt">번개</option><option value="diamond">다이아몬드</option></select></label><label>구단 로고 이미지 (선택, PNG/JPEG/WebP · 최대 80KB)<input name="logo" type="file" accept="image/png,image/jpeg,image/webp"/></label><p class="muted-note">로고 파일이 없으면 선택한 색상과 약자로 기본 엠블럼을 만듭니다.</p><button class="act" type="submit">신생 구단 창단 및 코치 영입</button><p class="err" id="club-err" role="alert"></p></form></section><section class="panel"><h2>신인 감독에게 도착한 제안 · ${proposals.length}개 구단</h2><p>각 구단이 신인 감독에게 부임을 제안했습니다. 하나를 수락하거나 2부 구단을 직접 창단할 수 있습니다.</p><div class="club-choice-list">${available}</div></section></div>`,'/app/clubs')
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
  if(isOperator)return {id:0,name:'리그 운영',season:worldState.season,week:worldState.week,role:'viewer'}
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
  const data = await api('/inbox?id=' + current.id)
  shell(`<div class="panel"><h2>우편</h2>${data.messages.map(mail => `<div class="row"><div><b>${esc(mail.subject)}</b><p>${esc(mail.body || '')}</p></div><button class="act" data-mail="${mail.id}">읽음</button></div>`).join('') || '<p>우편이 없습니다.</p>'}</div>`, '/app/inbox')
  document.querySelectorAll('[data-mail]').forEach(button => button.onclick = () => api('/read-mail', {id:current.id, mail:Number(button.dataset.mail)}).then(() => inbox()))
  await topbar()
}
async function news() {
  const current = await requireCareer(); if (!current) return
  const data = await api('/news?id=' + current.id)
  shell(`<div class="panel"><h2>뉴스</h2>${(data.news || []).map(item => `<article class="row"><div><b>${esc(item.headline)}</b><p>${esc(item.body || '')}</p></div></article>`).join('') || '<p>기사가 없습니다.</p>'}</div>`, '/app/news')
  await topbar()
}
function nickname(person) {return person.nickname || person.nickname_ko || person.display_name || person.name || '이름 확인 중'}
function personLink(person) {
  return `<a href="/app/player/${esc(person.id)}">${face(person.id,Boolean(person.photo))}<span>${esc(nickname(person))}<small>${esc(person.real_name_ko || person.display_name_ko || person.real_name || '')}</small>${flagAndCountry(person)}</span></a>`
}
function rosterTable(people, records={}, development={}, contracts={}) {
  if(!people.length)return '<p class="empty">등록된 선수가 없습니다.</p>'
  return `<div class="table-scroll"><table class="roster-table"><thead><tr>${['선수 얼굴 · 닉네임 / 이름','구분','소속 팀','레이팅','OVR','국적','포지션','계약금액 (연봉)','계약년도','만료'].map(t=>`<th>${t}</th>`).join('')}</tr></thead><tbody>${people.map(p=>{
    const c=contracts[p.id],d=development[p.id],r=records[p.id];const ratings=p.game_evaluation?.ratings||p.stats;const values=ratings?Object.values(ratings).filter(Number.isFinite):[];const ovr=d?.ovr??(values.length?Math.round(values.reduce((a,b)=>a+b,0)/values.length):null)
    const start=c?.start_turn?`${2026+Math.floor((c.start_turn-1)/104)}년 · ${Math.floor((c.start_turn-1)/104)+1}시즌`:'미기록'
    const expiry=c?`${2026+Math.floor((c.end_turn-1)/104)}년 · ${Math.floor((c.end_turn-1)/104)+1}시즌 ${((c.end_turn-1)%104)+1}주`:p.contract_end||'확인 중'
    const group=p.kind==='player'?(p.real_person?'실존 선수':'생성 선수'):(p.real_person?'실존 프런트':'생성 프런트');const assignment={first:'주전',reserve:'교체',academy:'2군',candidate:'영입 후보',unclassified:'분류 확인 중'}[p.assignment]||''
    return `<tr><td>${personLink(p)}</td><td><span class="identity-tag ${p.real_person?'real':'generated'}">${group}</span><small>${esc(assignment)}</small></td><td>${logoImg(p.league,p.team)}${esc(p.team||'무소속')}</td><td>${r?.rating!=null?`<b class="rating">${Number(r.rating).toFixed(1)}</b><small>${r.games}경기</small>`:'기록 없음'}</td><td><b>${ovr??'미평가'}</b></td><td>${flagAndCountry(p)}</td><td>${esc(ROLE[p.role]||'확인 중')}</td><td>${money(c?.annual_salary??p.salary)}${c||p.salary_estimated?'<small>게임 계약</small>':''}</td><td>${start}</td><td>${esc(expiry)}${!c&&p.contract_estimated?'<small>예상</small>':''}</td></tr>`
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
  const current = await requireCareer(); if (!current) return
  const [data,registration]=await Promise.all([api('/plan?id='+current.id),api('/recruitment?id='+current.id)])
  const plan = data.plan
  const catalog = data.catalog
  const phaseName = {early:'초반 운영', mid:'중반 운영', late:'후반 운영'}
  const phases = ['early','mid','late'].map(phase => `<div class="panel"><h2>${phaseName[phase]}</h2><label>운영 전략</label><select data-phase="${phase}" data-key="order">${catalog.orders[phase].map(item => `<option ${plan[phase].order === item ? 'selected' : ''}>${esc(item)}</option>`).join('')}</select><label>운영 세부 지침</label><select data-phase="${phase}" data-key="sub">${catalog.subs[phase].map(item => `<option ${plan[phase].sub === item ? 'selected' : ''}>${esc(item)}</option>`).join('')}</select></div>`).join('')
  const lanes = Object.entries(catalog.laning).map(([role, options]) => `<div class="row"><b>${ROLE[role]}</b><select data-lane="${role}">${options.map(item => `<option ${plan.laning[role] === item ? 'selected' : ''}>${esc(item)}</option>`).join('')}</select></div>`).join('')
  const callerOptions=key=>'<option value="">담당 선수 선택</option>'+(registration.roster||[]).map(p=>`<option value="${esc(p.id)}" ${plan.callers?.[key]===p.id?'selected':''}>${esc(nickname(p))} · ${esc(ROLE[p.role]||p.role)}</option>`).join('')
  const callers=`<section class="panel"><h2>오더 담당 선수</h2><div class="caller-selects"><label>오더 담당<select id="primary-caller">${callerOptions('primary')}</select></label><label>부오더 담당<select id="secondary-caller">${callerOptions('secondary')}</select></label></div><p>오더 담당이 교전을 지휘하고, 사망 중에는 부오더 담당이 이어받습니다.</p></section>`
  shell(callers + phases + `<div class="panel"><h2>초반 라인전</h2>${lanes}<button class="act" id="save-plan">전술 저장</button><p>담당 선수와 운영 전략을 저장하면 다음 세트부터 적용됩니다.</p></div>`, '/app/tactics')
  document.getElementById('save-plan').onclick = async () => {
    const primary=document.getElementById('primary-caller').value,secondary=document.getElementById('secondary-caller').value
    if(!primary||!secondary||primary===secondary)return alert('오더와 부오더를 맡을 서로 다른 주전 선수를 선택하세요.')
    const next = {callers:{primary,secondary},early:{}, mid:{}, late:{}, laning:{}}
    document.querySelectorAll('[data-phase]').forEach(select => { next[select.dataset.phase][select.dataset.key] = select.value })
    document.querySelectorAll('[data-lane]').forEach(select => { next.laning[select.dataset.lane] = select.value })
    try { await api('/plan', {id:current.id, plan:next}); alert('전술을 저장했습니다.') } catch (error) { alert(error.message) }
  }
  await topbar()
}
async function training() {
  const current = await requireCareer(); if (!current) return
  const data = await api('/training?id=' + current.id)
  const rows = data.players.map(row => {
    const person = row.person
    const chips = row.pool.map(name => `<b>${esc(name)} 수준급</b>`).join('')
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
    body = `<div class="panel"><h2>재정</h2><p>보유 ${money(data.cash)}</p><p>이적 예산 ${money(data.transfer_budget)}</p><p>급여 예산 ${money(data.wage_budget)}</p><p>연봉 합계 ${money(data.annual_payroll)}</p><p>구단주 ${data.board} / 팬 ${data.fans}</p><label>이적 예산</label><input id="budget-transfer" value="${data.transfer_budget}"/><label>급여 예산</label><input id="budget-wage" value="${data.wage_budget}"/><button class="act" id="save-budget">예산 저장</button></div><div class="panel"><h2>원장</h2>${(data.ledger || []).map(row => `<div class="row">${row.season}시즌 ${row.week}주 ${esc(row.description)} ${money(row.amount)}</div>`).join('')}</div>`
  } else if (kind === 'medical') {
    body = `<div class="panel"><h2>의료</h2>${(data.contracts || []).filter(item => item.person.kind === 'player').map(item => `<div class="row">${personLink(item.person)}<span>피로 ${item.fatigue} 사기 ${item.morale} 부상 ${item.injury_turns}</span><button class="act" data-treat="${esc(item.person.id)}" data-mode="rest">휴식</button><button class="act" data-treat="${esc(item.person.id)}" data-mode="rehab">재활</button><button class="act" data-treat="${esc(item.person.id)}" data-mode="normal">일반</button></div>`).join('')}</div>`
    body += `<div class="panel"><h2>선수 면담 · FA 방출 요청</h2><p>출전 기회를 원하는 후보·2군 선수의 요청입니다. 감독이 방출에 동의하면 FA로 전환됩니다.</p>${departures.requests.map(r=>`<div class="row"><b>${esc(r.person_id)}</b><span>${esc(r.reason)} · 사기 ${r.morale ?? '-'}</span><button class="act" data-release="${esc(r.person_id)}" data-approve="true">합의 방출</button><button class="act" data-release="${esc(r.person_id)}" data-approve="false">요청 거절</button></div>`).join('')||'<p class="empty">현재 방출을 요청한 선수가 없습니다.</p>'}</div>`
  } else if (kind === 'relations') {
    body = `<div class="panel"><h2>관계</h2>${(data.relationships || []).map(item => `<div class="row">${esc(item.first)} · ${esc(item.second)} 신뢰 ${item.trust}<button class="act" data-a="${esc(item.first)}" data-b="${esc(item.second)}" data-way="listen">대화</button></div>`).join('') || '<p>관계가 없습니다.</p>'}</div>`
  } else if (kind === 'staff') {
    body = `<div class="panel"><h2>스태프 정원</h2>${(data.staff_limits || []).map(item => `<div class="row">${esc(item.name)} ${item.count}/${item.limit}</div>`).join('')}<button class="act" id="staff-find">후보 생성</button></div>`
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
  document.querySelectorAll('[data-way]').forEach(button => button.onclick = () => api('/management', {id:current.id, action:'mediate', first:button.dataset.a, second:button.dataset.b, approach:'listen'}).then(() => draw()).catch(error => alert(error.message)))
  const find = document.getElementById('staff-find')
  if (find) find.onclick = () => api('/staff-candidates', {id:current.id}).then(() => alert('스태프 후보를 만들었습니다.')).catch(error => alert(error.message))
  await topbar()
}
async function schedule() {
  const current = await requireCareer(); if (!current) return
  const data = await api('/fixtures?id=' + current.id)
  shell(`<div class="panel"><h2>일정</h2>${data.fixtures.map(game => `<div class="row"><a href="/app/match/${game.id}">${game.season}시즌 ${game.week}주 ${esc(game.opponent)}</a><span>${esc(game.competition)} ${esc(game.state)}</span></div>`).join('') || '<p>일정이 없습니다.</p>'}</div>`, '/app/schedule')
  document.querySelectorAll('a[href^="/app/match"]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); go(link.getAttribute('href')) }))
  await topbar()
}
async function match(id) {
  const current = await requireCareer(); if (!current) return
  const data = await api('/fixtures?id=' + current.id)
  const game = data.fixtures.find(item => item.id === id)
  if (!game) { shell('<p>경기를 찾지 못했습니다.</p>', '/app/schedule'); return }
  const series = game.series || {}
  let controls = `<p>${esc(game.competition)} ${esc(game.stage)} · ${esc(series.phase || game.state)}</p>`
  if (series.phase === 'choice') controls += `<button class="act" data-choice="priority" data-value="first">선픽</button><button class="act" data-choice="priority" data-value="second">후픽</button><button class="act" data-choice="side" data-value="blue">블루</button><button class="act" data-choice="side" data-value="red">레드</button>`
  if (series.phase === 'draft') {
    const champs = await api('/champions')
    controls += `<input id="champ" placeholder="챔피언"/><button class="act" id="pick">선택</button><button class="act" id="auto">남은 픽 자동</button><div class="pool">${champs.champions.slice(0, 40).map(item => `<button class="act" data-champ="${esc(item.name)}">${esc(item.name)}</button>`).join('')}</div>`
  }
  if (series.phase === 'swap') controls += `<p>스왑은 30초입니다. 역할 번호를 바꿉니다.</p><input id="swap-a" value="0"/><input id="swap-b" value="1"/><button class="act" id="swap">스왑</button>`
  if (series.phase === 'feedback') controls += `<input id="note" maxlength="300" placeholder="세트 피드백"/><button class="act" id="note-save">전달</button>`
  if (game.result) controls += `<p>결과 ${(game.result.score || []).join(':')}</p>`
  shell(`<div class="panel"><h2>${esc(game.opponent)}</h2>${controls}</div>`, '/app/match/' + id)
  document.querySelectorAll('[data-choice]').forEach(button => button.onclick = () => api('/draft-choice', {id, category:button.dataset.choice, value:button.dataset.value, manual:true}).then(() => draw()).catch(error => alert(error.message)))
  const pick = document.getElementById('pick')
  if (pick) pick.onclick = () => api('/draft-action', {id, champion:document.getElementById('champ').value.trim(), version:series.draft_version}).then(() => draw()).catch(error => alert(error.message))
  document.querySelectorAll('[data-champ]').forEach(button => button.onclick = () => { document.getElementById('champ').value = button.dataset.champ })
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
  const person=detail.person,scout=detail.scouting?.scout,agency=detail.scouting?.agency
  const development=(train.players||[]).find(row=>row.person.id===id)
  const contract=(manage.contracts||[]).find(row=>row.person.id===id)
  const tabs=[['overview','선수 개요'],['personal','개인 정보'],['contract','계약'],['history','이력'],['report','스카우트 보고'],['career','커리어'],['compare','선수 비교']]
  const links=`<div class="tabs player-tabs">${tabs.map(([k,l])=>`<a class="${tab===k?'on':''}" href="/app/player/${esc(id)}/${k}">${l}</a>`).join('')}</div>`
  const values=person.game_evaluation?.ratings||person.stats||{}
  const joined=person.team?`${logoImg(person.league,person.team)}${esc(person.team)} · ${esc(person.league||'')}`:'FA · 무소속'
  const top=`<div class="player-profile-heading"><div class="player-profile-face">${face(person.id,Boolean(person.photo))}</div><div><p class="eyebrow">${person.kind==='player'?'PLAYER DATABASE':'FRONT OFFICE DATABASE'} / ${esc(person.staff_role_name||frontRoleLabel(person))}</p><h1>${esc(person.nickname||person.display_name||person.real_name||'선수')}</h1><p>${esc(person.real_name||'이름 정보 없음')} · ${esc(ROLE[person.role]||person.role||'포지션 미상')}</p><p>${flagAndCountry(person)}</p><p class="player-team-line">${joined}</p><div class="player-overview-stats"><span>솔로랭크 <strong>${esc(person.solo?.label||'기록 없음')}</strong></span><span>소속 <strong>${esc(person.assignment||person.squad||'미등록')}</strong></span>${development?`<span>OVR <strong>${development.ovr}</strong></span>`:''}</div></div></div>`
  let main=''
  if(tab==='overview') main=`<div class="player-info-grid"><section class="panel"><h2>현재 능력</h2>${ratingGrid(values)}</section><section class="panel"><h2>구단 스카우팅 요약</h2><p>현재 실력</p>${scoutStars(scout?.current_stars)}<p>예상 잠재력</p>${scoutStars(scout?.potential_stars)}<p class="muted-note">${esc(scout?.summary||'스카우팅 기록 없음')}</p></section><section class="panel"><h2>커리어 정보</h2><p>역할: ${esc(ROLE[person.role]||person.role||'미상')}</p><p>국적: ${flagAndCountry(person)}</p><p>구단: ${joined}</p><p>게임 내 소속: ${esc(person.assignment||'등록 정보 없음')}</p><p>계약: ${esc(person.contract_end||'기록 없음')}</p></section></div>`
  else if(tab==='personal') main=`<section class="panel"><h2>개인 정보</h2><div class="info-pairs"><p>영문 닉네임 <b>${esc(person.nickname||'기록 없음')}</b></p><p>본명 <b>${esc(person.real_name||'기록 없음')}</b></p><p>국적 <b>${flagAndCountry(person)}</b></p><p>리그 <b>${esc(person.league||'무소속')}</b></p><p>지역 <b>${esc(person.region||person.nationality_name_ko||'정보 없음')}</b></p><p>포지션 <b>${esc(ROLE[person.role]||person.role||'정보 없음')}</b></p><p>솔로랭크 <b>${esc(person.solo?.label||'정보 없음')}</b></p></div></section>`
  else if(tab==='contract') main=`<section class="panel"><h2>계약 및 연봉</h2><div class="info-pairs"><p>계약 종료 <b>${esc(person.contract_end||'정보 없음')}</b></p><p>게임 내 연봉 <b>${contract?money(contract.annual_salary):money(person.salary)}</b></p><p>계약 기간 <b>${contract?contract.remaining_turns+'주 남음':'구단 계약 정보 없음'}</b></p><p>현재 상태 <b>${contract?(contract.active?'계약 중':'계약 종료'):'외부 구단 또는 FA'}</b></p></div></section>`
  else if(tab==='history') main=`<section class="panel"><h2>선수 이력</h2><p>현재 소속 ${joined}</p><p>최초 등록 구단: ${esc(person.registered_team||person.team||'정보 없음')}</p><p class="muted-note">내부 DB 출처 코드 대신 실제 경기 및 이적 기록을 표시할 예정입니다.</p></section>`
  else if(tab==='report') main=`<div class="report-grid"><section class="panel scout-report-card"><p class="eyebrow">PRIVATE SCOUTING</p><h2>내 구단 스카우터 보고서</h2><p>현재 능력</p>${scoutStars(scout?.current_stars)}<p>잠재력</p>${scoutStars(scout?.potential_stars)}<div class="info-pairs"><p>평가 시즌 <b>${scout?.season||'-'}시즌</b></p><p>평가 역량 <b>${scout?.scout_skill??'-'} / 20</b></p><p>보고 신뢰도 <b>${esc(scout?.confidence||'미평가')}</b></p></div><p class="muted-note">${esc(scout?.summary||'스카우팅 자료가 없습니다.')}</p></section><section class="panel"><p class="eyebrow">ANNUAL REPORT</p><h2>기관 연례 평가</h2><p>${esc(agency?.source||'게임 내 가상 평가 기관')}</p>${scoutStars(agency?.current_stars)}<p>${esc(agency?.season||'-')}시즌 · 연 1회 발표</p><p class="muted-note">${esc(agency?.summary||'아직 발표된 평가가 없습니다.')}</p></section></div><section class="panel"><h2>세부 능력치</h2>${ratingGrid(values)}<p class="muted-note">세부 수치는 게임 데이터입니다. 스카우트 별점은 관찰 능력에 따라 다르게 산출됩니다.</p></section>`
  else if(tab==='career') main=`<section class="panel"><h2>현재 선수 경력</h2><div class="info-pairs"><p>등록 구단 <b>${esc(person.team||'FA')}</b></p><p>선수단 분류 <b>${esc(person.assignment||person.squad||'기록 없음')}</b></p><p>프로 여부 <b>${esc(person.solo?.path_name||'확인되지 않음')}</b></p><p>개인 랭크 <b>${esc(person.solo?.label||'기록 없음')}</b></p></div><p class="muted-note">솔로랭크 성적과 공식 프로 경기 성적은 별도로 집계됩니다.</p></section>`
  else if(tab==='compare') {
    const result=await api('/player-comparisons?id='+current.id+'&person='+encodeURIComponent(id))
    main=`<section class="panel"><h2>동일 포지션 선수 비교</h2><p>${esc(ROLE[person.role]||person.role||'')} 포지션 · 게임 내 능력 수치가 가까운 선수</p><div class="table-scroll"><table><thead><tr><th>선수</th><th>구단</th><th>종합</th><th>기준 선수 대비</th><th>상세 보기</th></tr></thead><tbody>${(result.comparisons||[]).map(p=>`<tr><td><b>${esc(p.nickname)}</b></td><td>${esc(p.team)}</td><td>${p.rating}</td><td class="${p.gap>=0?'positive-gap':'negative-gap'}">${p.gap>0?'+':''}${p.gap}</td><td><a href="/app/player/${encodeURIComponent(p.id)}/compare">비교 대상 열기</a></td></tr>`).join('')}</tbody></table></div></section><section class="panel"><h2>기준 선수 능력치</h2>${ratingGrid(values)}</section>`
  } else return go('/app/player/'+encodeURIComponent(id)+'/overview')
  shell(`<div class="player-profile">${top}${links}${main}<div class="player-footer"><a href="/app/players">선수 DB로 돌아가기</a>${person.team?`<a href="/app/team/${encodeURIComponent(person.league||'')}/${encodeURIComponent(person.team)}">구단 보기</a>`:''}</div></div>`,'/app/player/'+id)
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
  const labels={real:'실존 프런트·코칭스태프',generated:'생성 프런트·코칭스태프',verified:'출처 확인됨',simulation:'게임 내 운영진','registered-coach':'등록된 코치진',user:'유저 감독',game:'게임 내 직책'}
  const source=labels[p.source]||'직책 등록'
  const link=typeof p.source_url==='string'&&/^https:\/\//.test(p.source_url)?'<a class="front-source" href="'+esc(p.source_url)+'" target="_blank" rel="noopener">정보 출처</a>':''
  const role=String(p.role_key||'')
  const hasNationality=p.show_nationality!==false && role!=='OWNER' && role!=='EXECUTIVE'
  const country=hasNationality?flagAndCountry(p):''
  const details=role==='OWNER'?'구단 소유·운영 조직':role==='EXECUTIVE'?'대표자':role==='MANAGER'?'담당 감독':'프런트·코치진'
  return '<div class="front-person"><div class="front-role">'+esc(p.role||'직책 미확인')+'</div><strong>'+esc(p.name||'정보 미등록')+'</strong>'+country+'<small>'+esc(details)+'</small><small>'+esc(source)+'</small>'+link+'</div>'
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
  shell(`<div class="fm-team-page"><header class="fm-team-header">${logoImg(idn.league,idn.team)}<div><p class="eyebrow">CLUB INFORMATION · ${esc(idn.league)}</p><h1>${esc(data.display_name||idn.team)}</h1><p>${esc(data.season||'현재')}시즌 · 1군 ${teamPlayers.length}명 · 2군 ${(data.academy||[]).length}명 · 프런트 ${(data.front_office||[]).length}명</p></div><a href="/app/league/${encodeURIComponent(league)}" class="act">${esc(league)} 리그 보기</a></header>${rowNotes}${links}${main}</div>`,'/app/team/'+encodeURIComponent(league)+'/'+encodeURIComponent(name))
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
  const offers=(data.offers||[]).filter(o=>o.status==='offered')
  const active=(data.contracts||[]).map(o=>'<div class="sponsor-company"><strong>'+esc(o.company)+'</strong><span>'+o.start_season+'~'+o.end_season+'시즌 · 가상 스폰서</span><b>'+money(o.amount)+'</b></div>').join('')
  const choices=offers.map(o=>'<div class="sponsor-company"><div><small>시즌 '+o.season+' · 지역 '+esc(o.region)+'</small><strong>'+esc(o.company)+'</strong><span>계약 금액 '+money(o.amount)+'</span></div><button class="act" data-sponsor="'+o.id+'">가상 제안 수락</button></div>').join('')
  shell('<div class="page-heading"><div><p class="eyebrow">SPONSORSHIP</p><h1>스폰서 제안</h1><p>성적과 구단 성장에 따라 지역 기업 이름을 활용한 게임 내 가상 제안이 도착합니다.</p></div></div><section class="panel"><h2>새로운 계약 제안</h2>'+ (choices||'<p class="empty">현재 도착한 새 스폰서 제안이 없습니다. 시즌 성적을 쌓아 보세요.</p>')+'<p class="muted-note">'+esc(data.notice||'실제 기업과의 후원 관계가 아닙니다.')+'</p></section><section class="panel"><h2>스폰서 변경 이력</h2>'+(active||'<p class="empty">체결된 가상 계약이 없습니다.</p>')+'</section>','/app/sponsors')
  document.querySelectorAll('[data-sponsor]').forEach(btn=>btn.onclick=async()=>{
    if(!confirm('게임 내 가상 스폰서 제안을 수락하시겠습니까?'))return
    try{await api('/sponsor-accept',{id:current.id,offer:Number(btn.dataset.sponsor)});careerCache=null;draw()}
    catch(e){alert(e.message)}
  })
  await topbar()
}
async function clubLogoSettings(){
  const current=await requireCareer();if(!current)return
  const league=current.club_profile?.league||''
  const team=current.name
  const data=await api('/club-identity?league='+encodeURIComponent(league)+'&team='+encodeURIComponent(team))
  const history=clubHistoryPanel(data.history)
  shell('<div class="page-heading"><div><p class="eyebrow">CLUB IDENTITY</p><h1>구단 로고 설정</h1><p>구단을 선택하거나 창단한 후 팀명은 변경할 수 없습니다. 유저 감독은 본인 구단의 로고만 변경할 수 있습니다.</p></div></div><section class="panel club-brand-manager"><div>'+logoImg(league,team)+'</div><div><h2>'+esc(data.display_name)+'</h2><p>'+esc(league)+' · 확정된 구단명</p><form id="club-logo-form"><label>대표 구단 로고 선택 · 최대 80KB<input type="file" name="logo" accept="image/png,image/jpeg,image/webp" required/></label><button class="act" type="submit">구단 로고 저장</button></form><p id="club-brand-error" class="err"></p></div></section>'+history,'/app/club-identity-settings')
  document.getElementById('club-logo-form').onsubmit=async e=>{e.preventDefault();try{
    const logo_data=await readClubLogo(e.target.elements.logo.files[0])
    if(!logo_data)throw Error('로고 이미지를 선택하세요.')
    await api('/club-logo',{id:current.id,logo_data})
    media.brandings=null;careerCache=null;draw()
  }catch(error){document.getElementById('club-brand-error').textContent=error.message}}
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
async function solo() {
  const current = await requireCareer(); if (!current) return
  const data = await api('/solo-ladder?id=' + current.id)
  shell(`<div class="panel"><h2>솔로랭크</h2>${(data.rows || []).slice(0, 40).map(row => `<div class="row">${personLink({id:row.id, display_name:row.nickname})}<span>${esc(row.label)} ${esc(row.path_name)}</span>${row.path === 'amateur' ? `<button class="act" data-talk="${esc(row.id)}">대화</button>` : ''}</div>`).join('')}</div>`, '/app/solo')
  document.querySelectorAll('[data-talk]').forEach(button => button.onclick = () => api('/solo-talk', {id:current.id, person:button.dataset.talk}).then(() => draw()).catch(error => alert(error.message)))
  await topbar()
}
async function transfers() {
  const current = await requireCareer(); if (!current) return
  const [offers, activity] = await Promise.all([api('/transfer-offers?id=' + current.id), api('/transfer-activity?id=' + current.id)])
  shell(`<div class="panel"><h2>이적 제안</h2><input id="pid" placeholder="선수 id"/><input id="salary" value="0"/><input id="fee" value="0"/><button class="act" id="quote">제안</button>${offers.offers.map(item => `<div class="row">#${item.id} ${esc(item.state)} 연봉 ${money(item.annual_salary)} 이적료 ${money(item.fee)}<button class="act" data-offer="${item.id}" data-choice="accept">수락</button><button class="act" data-offer="${item.id}" data-choice="decline">거절</button><button class="act" data-offer="${item.id}" data-choice="cancel">취소</button></div>`).join('')}</div><div class="panel"><h2>이적 기록</h2>${activity.events.map(item => `<div class="row">${esc(item.buyer_name || '')} ${money(item.fee)}</div>`).join('')}</div>`, '/app/transfers')
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
async function dataHub() {
  const current = await requireCareer(); if (!current) return
  const data = await api('/analytics?id=' + current.id + '&season=' + current.season)
  shell(`<div class="panel"><h2>데이터</h2><p>세트 ${data.sets} · 시리즈 ${data.series}</p>${(data.players || []).map(player => `<div class="row">${esc(player.name)} ${player.games}경기 ${player.kills}/${player.deaths}/${player.assists} 평점 ${player.rating}</div>`).join('') || '<p>끝난 경기 기록이 없습니다.</p>'}</div>`, '/app/data')
  await topbar()
}
async function community(postId) {
  const current = await requireCareer(); if (!current) return
  const league = current.club_profile?.league || 'LCK'
  if (postId) {
    const data = await api('/community-post?post=' + postId)
    const post = data.post
    shell(`<div class="panel"><a href="/app/community">목록</a><h2>${esc(post.title)}</h2><p>${esc(post.body || '')}</p>${(post.comments_list || []).map(comment => `<div class="row">${esc(comment.body)}</div>`).join('')}</div>`, '/app/community')
  } else {
    const data = await api('/community?league=' + encodeURIComponent(league))
    shell(`<div class="panel"><h2>${esc(data.league)} 팬 게시판</h2>${data.posts.map(post => `<div class="row"><a href="/app/community/${post.id}">${esc(post.title)}</a><span>${esc(post.category_name)}</span></div>`).join('')}</div>`, '/app/community')
  }
  document.querySelectorAll('a[href^="/app"]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); go(link.getAttribute('href')) }))
  await topbar()
}
async function draw() {
  const path = location.pathname.slice(BASE.length) || "/"
  if (!token()) { login(); return }
  if (!Object.keys(media.colors).length) {
    const [colors, logos] = await Promise.all([fetch(BASE + '/media/club-colors.json').then(r => r.ok?r.json():{}).catch(()=>({})), fetch(BASE + '/media/club-assets.json').then(r => r.ok?r.json():{}).catch(()=>({}))])
    media = {colors, logos, brandings:null}
  }
  try {
    worldState=await api('/world');isOperator=worldState.operator===true
    if(media.brandings===null) {
      const visual=await api('/club-brandings')
      media.brandings=visual.brandings||{}
    }
    if(isOperator){careerCache=null;localStorage.removeItem('rift-career');if(path==='/app/manager')return go('/app/home');if(path==='/app/home'||path==='/'||path==='/app/schedule')return await operatorDesk(path==='/app/schedule'?path:'/app/home');if(!['/app/clubs','/app/competition','/app/players'].includes(path)&&!/^\/app\/(player|team|entity)\//.test(path))return go('/app/home')}
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
    if (path === '/app/players') return await players()
    if (path === '/app/solo') return await solo()
    if (path === '/app/transfers') return await transfers()
    if (path === '/app/shortlist') return await shortlist()
    if (path === '/app/competition') return go('/app/leagues')
    if (path === '/app/leagues') return await leagueIndex()
    if (path === '/app/sponsors') return await sponsorsPage()
    if (path === '/app/club-identity-settings') return await clubLogoSettings()
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
draw()
