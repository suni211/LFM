const BASE = location.pathname.startsWith('/rift') ? '/rift' : ''
const NAV = [
  ['홈', '/app/home', '경기'],
  ['우편', '/app/inbox', '경기'],
  ['뉴스', '/app/news', '경기'],
  ['1군', '/app/squad', '선수단'],
  ['2군', '/app/academy', '선수단'],
  ['전술', '/app/tactics', '선수단'],
  ['훈련', '/app/training', '선수단'],
  ['스태프', '/app/staff', '선수단'],
  ['의료', '/app/medical', '선수단'],
  ['관계', '/app/relations', '선수단'],
  ['일정', '/app/schedule', '대회'],
  ['선수 DB', '/app/players', '대회'],
  ['솔로랭크', '/app/solo', '대회'],
  ['이적', '/app/transfers', '영입'],
  ['영입 명단', '/app/shortlist', '영입'],
  ['재정', '/app/finance', '구단'],
  ['대회', '/app/competition', '구단'],
  ['데이터', '/app/data', '구단'],
  ['비전', '/app/vision', '구단'],
  ['커뮤니티', '/app/community', '구단']
]
const WIDGETS = {cash:'현금 흐름',
  news: '뉴스', inbox: '우편', standings: '리그 순위', next: '다음 경기', squad: '선수단',
  budget: '이적 예산', wages: '급여', schedule: '일정', staff: '스태프', medical: '의료',
  board: '구단주·팬', form: '최근 경기'
}
const ROLE = {TOP:'탑', JUNGLE:'정글', MID:'미드', ADC:'원딜', SUPPORT:'서포터'}
let media = {colors:{}, logos:{}}
let careerCache = null
let managerProfile = null
let isOperator = false
let worldState = null

function esc(value) {
  return String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]))
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
function logoImg(league, team) {
  const item = media.logos[league + '\n' + team]
  if (!item || !item.logo) return `<span class="club-monogram" aria-label="${esc(team)}">${esc((team||'RM').slice(0,2))}</span>`
  return `<img class="logo" alt="" style="background:${esc(item.background || '#dce3ed')}" src="${BASE}/media/${esc(item.logo)}"/>`
}
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
  const categories=isOperator?[['리그 관리',['home','clubs','competition','schedule']],['인물 · 구단',['players']]]:[['구단',['home','inbox','news','finance','vision','community']],['선수단',['squad','academy','staff','medical','relations','players','solo']],['전술·훈련',['tactics','training']],['영입',['transfers','shortlist']],['대회·경기',['schedule','competition','data']],...(isOperator?[['운영',['clubs']]]:[])]
  const selected=NAV.find(n=>n[1]===path)?.[0]||'구단 관리'
  const menu=categories.map(([label,keys])=>`<details class="nav-category"><summary>${label}<span>⌄</span></summary><div class="dropdown">${keys.map(key=>{const item=NAV.find(n=>n[1]==='/app/'+key)||[key==='clubs'?(isOperator?'구단 조회':'구단 선택'):key,'/app/'+key];return `<a href="${item[1]}" class="${path===item[1]?'on':''}">${item[0]}</a>`}).join('')}</div></details>`).join('')
  document.getElementById('app').innerHTML=`<div id="shell"><header id="masthead"><div id="top"></div><nav id="navigation"><a class="brand" href="/app/home">R/M<span>RIFT MANAGER</span></a>${menu}${isOperator?'<span class="account-link">운영자 · 구단 운영 불가</span>':'<a class="account-link" href="/app/manager">감독 프로필</a>'}<button id="logout" aria-label="로그아웃">로그아웃</button></nav></header><main id="view" aria-label="${esc(selected)}">${body}</main></div>`
  document.getElementById('logout').onclick=()=>{localStorage.removeItem('rift-token');localStorage.removeItem('rift-career');careerCache=null;location.href=BASE+'/'}
}
async function topbar() {
  const current=isOperator?null:await career();const world=await api('/world');const bar=document.getElementById('top');if(!bar)return
  const league=current?.club_profile?.league||'',name=isOperator?'리그 운영':current?.name||'구단 선택'
  document.documentElement.style.setProperty('--team',teamColor(league,name))
  const fixtures=current?(await api('/fixtures?id='+current.id)).fixtures:[]
  const due=(fixtures||[]).find(g=>g.state==='queued')
  bar.innerHTML=`<div class="club-identity">${logoImg(league,name)}<div><b>${esc(name)}</b><small>${esc(league)} · 온라인 리그</small></div></div><div class="search-wrap"><label class="sr-only" for="global-search">통합 검색</label><input id="global-search" placeholder="선수, 스태프, 구단 검색" autocomplete="off"/><div id="search-results" hidden></div></div><div class="week"><small>현재 시즌</small><b>${world.season}시즌 ${world.week}주차</b></div>${isOperator?'':`<button class="continue" id="vote">${due?'경기 진행':world.ready?'준비 완료':'다음으로'} <span>❯❯</span></button>`}`
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
  shell(`<div class="continue-landing"><p class="eyebrow">CONTINUE CAREER</p><div class="continue-club">${logoImg(league,selected.name)}<div><h1>${esc(selected.name)}</h1><p>${esc(league)} · ${selected.season}시즌 ${selected.week}주차</p><strong>리그 순위 · ${esc(position)}</strong></div></div><div class="continue-actions"><button class="act" id="resume">이어하기</button><a class="act" href="/app/manager">감독 프로필</a></div></div>`, '/app/home')
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
  shell(`<div class="page-heading"><div><p class="eyebrow">MANAGER PROFILE</p><h1>${profile.complete?'감독 프로필':'감독 만들기'}</h1><p>닉네임과 이름을 정하고 능력치 60점을 배분하세요.</p></div></div><form id="manager-setup" class="panel manager-setup"><label>닉네임<input name="nickname" autocomplete="nickname" maxlength="30" required value="${esc(profile.nickname)}" placeholder="English nickname (e.g. Raven)" pattern="[A-Za-z]{2,20}" title="영문 2~20자"/></label><label>감독 이름<input name="managerName" autocomplete="name" maxlength="30" required value="${esc(profile.name)}" placeholder="감독 이름"/></label><h2>감독 능력치 <span id="stat-total"></span></h2><p>각 능력치 1~20 · 합계 60</p>${profile.attributes.map(key=>`<label class="stat-allocation"><span>${esc(key)}</span><input type="range" min="1" max="20" step="1" data-stat="${esc(key)}" value="${profile.stats[key]}"/><output>${profile.stats[key]}</output></label>`).join('')}<p class="err" id="manager-error" role="alert"></p><button class="act" id="save-manager">${owned?'프로필 저장':'저장하고 구단 선택'}</button></form>`,'/app/manager')
  const form=document.getElementById('manager-setup'),inputs=[...form.querySelectorAll('[data-stat]')],button=document.getElementById('save-manager')
  const update=()=>{const total=inputs.reduce((sum,i)=>sum+Number(i.value),0);inputs.forEach(i=>i.nextElementSibling.value=i.value);document.getElementById('stat-total').textContent=`${total} / 60 · ${total===60?'배분 완료':total<60?(60-total)+'점 남음':(total-60)+'점 초과'}`;button.disabled=total!==60}
  inputs.forEach(i=>i.oninput=update);update()
  form.onsubmit=async event=>{event.preventDefault();if(!form.reportValidity()||button.disabled)return;button.disabled=true;try{managerProfile=await api('/manager-profile',{nickname:form.elements.nickname.value.trim(),name:form.elements.managerName.value.trim(),stats:Object.fromEntries(inputs.map(i=>[i.dataset.stat,Number(i.value)]))});careerCache=null;go(owned?'/app/home':'/app/clubs')}catch(e){document.getElementById('manager-error').textContent=e.message;update()}}
  await topbar()
}
async function clubs() {
  shell('<h1>구단</h1><div id="view2"></div>', '/app/clubs')
  const [mine, board] = await Promise.all([api('/careers'), api('/clubs')])
  if(mine.careers.length && !isOperator)return go('/app/home')
  const open = mine.careers.map(item => `<div class="row"><button class="act" data-open="${item.id}">${esc(item.name)}</button><span>${esc(item.club_profile?.league || '')} · ${item.season}시즌 ${item.week}주 · ${item.role}</span></div>`).join('') || '<p>맡은 구단이 없습니다.</p>'
  const take = board.clubs.filter(club=>isOperator || !club.claimed || club.kind==='ai').map(club => `<div class="row">${logoImg(club.league, club.team)}<span>${esc(club.league)} / ${esc(club.team)}</span>${isOperator?'':`<button class="act" data-team="${esc(club.team_key)}">감독 부임</button>`}<a href="/app/team/${encodeURIComponent(club.league)}/${encodeURIComponent(club.team)}">정보</a></div>`).join('')
  document.getElementById('view').insertAdjacentHTML('beforeend', `${isOperator?'':`<div class="panel"><h2>내 구단</h2>${open}</div>`}<div class="panel"><h2>리그 구단</h2>${take}</div>`)
  document.querySelectorAll('[data-open]').forEach(button => button.onclick = () => { localStorage.setItem('rift-career', button.dataset.open); careerCache = null; go('/app/home') })
  document.querySelectorAll('[data-team]').forEach(button => button.onclick = async () => {
    try {
      const result = await api('/careers', {mode:isOperator?'enter':'takeover', team_key:button.dataset.team})
      localStorage.setItem('rift-career', result.id); careerCache = null; go('/app/home')
    } catch (error) { alert(error.message) }
  })
  document.querySelectorAll('#view a[href^="/app"]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); go(link.getAttribute('href')) }))
  if(!isOperator && !mine.careers.length){document.getElementById('view').insertAdjacentHTML('afterbegin',`<form class="panel" id="new-club"><h2>새 구단 창단</h2><label>구단 이름 <input name="clubName" required maxlength="40"/></label><label>참가 리그 <select name="league">${board.leagues.map(l=>`<option ${l==='LCK CL'?'selected':''}>${esc(l)}</option>`).join('')}</select></label><button class="act">창단하고 시작</button><p class="err"></p></form>`);document.getElementById('new-club').onsubmit=async e=>{e.preventDefault();const form=e.currentTarget;try{const r=await api('/careers',{mode:'create',name:form.elements.clubName.value.trim(),league:form.elements.league.value});localStorage.setItem('rift-career',r.id);careerCache=null;go('/app/squad')}catch(err){form.querySelector('.err').textContent=err.message}}}
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
function nickname(person) {return person.nickname_ko || person.nickname || person.display_name || person.name || '이름 확인 중'}
function personLink(person) {
  return `<a href="/app/player/${esc(person.id)}">${face(person.id,Boolean(person.photo))}<span>${esc(nickname(person))}<small>${esc(person.real_name_ko || person.display_name_ko || person.real_name || '')}</small></span></a>`
}
function rosterTable(people, records={}, development={}, contracts={}) {
  if(!people.length)return '<p class="empty">등록된 선수가 없습니다.</p>'
  return `<div class="table-scroll"><table class="roster-table"><thead><tr>${['선수 얼굴 · 닉네임 / 이름','구분','소속 팀','레이팅','OVR','포지션','계약금액 (연봉)','계약년도','만료'].map(t=>`<th>${t}</th>`).join('')}</tr></thead><tbody>${people.map(p=>{
    const c=contracts[p.id],d=development[p.id],r=records[p.id];const ratings=p.game_evaluation?.ratings||p.stats;const values=ratings?Object.values(ratings).filter(Number.isFinite):[];const ovr=d?.ovr??(values.length?Math.round(values.reduce((a,b)=>a+b,0)/values.length):null)
    const start=c?.start_turn?`${2026+Math.floor((c.start_turn-1)/104)}년 · ${Math.floor((c.start_turn-1)/104)+1}시즌`:'미기록'
    const expiry=c?`${2026+Math.floor((c.end_turn-1)/104)}년 · ${Math.floor((c.end_turn-1)/104)+1}시즌 ${((c.end_turn-1)%104)+1}주`:p.contract_end||'확인 중'
    const group=p.real_person?'실존 선수':'생성 선수';const assignment={first:'주전',reserve:'교체',academy:'2군',candidate:'영입 후보',unclassified:'분류 확인 중'}[p.assignment]||''
    return `<tr><td>${personLink(p)}</td><td><span class="identity-tag ${p.real_person?'real':'generated'}">${group}</span><small>${esc(assignment)}</small></td><td>${logoImg(p.league,p.team)}${esc(p.team||'무소속')}</td><td>${r?.rating!=null?`<b class="rating">${Number(r.rating).toFixed(1)}</b><small>${r.games}경기</small>`:'기록 없음'}</td><td><b>${ovr??'미평가'}</b></td><td>${esc(ROLE[p.role]||'확인 중')}</td><td>${money(c?.annual_salary??p.salary)}${c||p.salary_estimated?'<small>게임 계약</small>':''}</td><td>${start}</td><td>${esc(expiry)}${!c&&p.contract_estimated?'<small>예상</small>':''}</td></tr>`
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
async function player(id, tab) {
  const current = await requireCareer(); if (!current) return
  const [detail, train, manage] = await Promise.all([
    api('/person?id=' + current.id + '&person=' + encodeURIComponent(id)),
    isOperator?Promise.resolve({players:[]}):api('/training?id=' + current.id).catch(() => ({players:[]})),
    isOperator?Promise.resolve({}):api('/management?id=' + current.id).catch(() => ({}))
  ])
  const person = detail.person
  const dev = (train.players || []).find(row => row.person.id === id)
  const contract = (manage.contracts || []).find(item => item.person.id === id)
  const tabs = [['overview','개요'],['personal','개인'],['contract','계약'],['history','이력'],['report','보고'],['career','커리어'],['compare','비교']]
  const links = `<div class="tabs">${tabs.map(([key, label]) => `<a class="${tab === key ? 'on' : ''}" href="/app/player/${esc(id)}/${key}">${label}</a>`).join('')}</div>`
  const ratings = person.game_evaluation?.ratings || {}
  const bars = Object.entries(ratings).map(([name, value]) => `<div class="row">${esc(name)} <span class="bars"><span style="width:${value}px"></span></span> ${value}</div>`).join('') || '<p>운영자 평가가 없습니다.</p>'
  const pool = dev ? dev.pool.map(name => `<b>${esc(name)} 수준급</b>`).join('') : ''
  let main = ''
  if (tab === 'overview') main = `<div class="hero">${face(person.id,Boolean(person.photo)).replace('class="face"', 'class="portrait"')}<div><h1>${esc(nickname(person))}</h1><p>${esc(person.real_name || '')} · ${esc(ROLE[person.role] || person.role || person.raw_role || '')}</p><p>${logoImg(person.league, person.team)} ${esc(person.league || '')} ${esc(person.team || '')}</p><p>OVR ${dev ? dev.ovr : '기록 없음'}</p><div class="pool">${pool}</div><p>폭 밖 챔피언은 그럭저럭 다룹니다.</p>${bars}</div></div>`
  if (tab === 'personal') main = `<p>본명 ${esc(person.real_name || '기록 없음')}</p><p>닉네임 ${esc(person.nickname || '')}</p><p>리그 ${esc(person.league || '')}</p><p>지역 ${esc(person.region || '기록 없음')}</p><p>솔로 ${esc(person.solo?.label || '기록 없음')} ${esc(person.solo?.path_name || '')}</p>`
  if (tab === 'contract') main = `<p>계약 종료 ${esc(person.contract_end || '기록 없음')}</p><p>게임 연봉 ${contract ? money(contract.annual_salary) : money(person.salary)}</p><p>남은 턴 ${contract ? contract.remaining_turns : '우리 구단 계약 아님'}</p>`
  if (tab === 'history') main = `<p>원 소속 ${esc(person.registered_team || person.team || '')}</p><p>출처 ${esc(person.source || '')}</p>`
  if (tab === 'report') main = bars + `<p>${esc(person.game_evaluation?.note || '평가 근거 없음')}</p>`
  if (tab === 'career') main = `<p>배정 ${esc(person.assignment || '명단 밖')}</p><p>경로 ${esc(person.solo?.path_name || person.kind || '')}</p>`
  if (tab === 'compare') main = `<p>같은 역할 비교는 선수 DB에서 ${esc(ROLE[person.role] || '')} 검색으로 엽니다.</p><a href="/app/players">선수 DB</a>`
  shell(`<div class="panel">${links}${main}<p><a href="/app/team/${encodeURIComponent(person.league || '')}/${encodeURIComponent(person.team || '')}">구단 정보</a></p></div>`, '/app/player/' + id)
  document.querySelectorAll('a[href^="/app"]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); go(link.getAttribute('href')) }))
  await topbar()
}
async function team(league, name, tab) {
  const data = await api('/club-dossier?league=' + encodeURIComponent(league) + '&team=' + encodeURIComponent(name))
  const idn = data.identity
  const tabs = [['overview','개요'],['roster','로스터'],['staff','코치'],['finance','재정'],['matches','경기']]
  const links = `<div class="tabs">${tabs.map(([key, label]) => `<a class="${tab === key ? 'on' : ''}" href="/app/team/${encodeURIComponent(league)}/${encodeURIComponent(name)}/${key}">${label}</a>`).join('')}</div>`
  const list = rows => rosterTable(rows)
  let main = ''
  if (tab === 'overview') main = `<p>1군 ${data.players.length}명 · 2군 ${data.academy.length}명 · 스태프 ${data.staff.length}명</p><h2>최근 5경기</h2>${(data.recent||[]).map(g=>`<div class="row"><b class="${g.won?'win':'loss'}">${g.won?'승':'패'}</b><span>${esc(g.opponent)} · ${(g.score||[]).join(':')}</span><small>${g.season}시즌 ${g.week}주</small></div>`).join('')||'<p class="empty">기록된 경기가 없습니다.</p>'}<h2>현재 리그 순위</h2>` + (data.standings.length ? widget('standings', {standings:data.standings, club:name, league}) : '')
  if (tab === 'roster') main = `<h2>1군</h2>${list(data.players)}<h2>2군</h2>${list(data.academy)}`
  if (tab === 'staff') main = list(data.staff) + (data.finances?.staff_limits || []).map(item => `<div class="row">${esc(item.name)} ${item.count}/${item.limit}</div>`).join('')
  if (tab === 'finance') main = data.finances?.initialized ? `<p>보유 ${money(data.finances.cash)}</p><p>이적 ${money(data.finances.transfer_budget)}</p><p>급여 예산 ${money(data.finances.wage_budget)}</p><p>연봉 ${money(data.finances.annual_payroll)}</p><p>구단주 ${data.finances.board} / 팬 ${data.finances.fans}</p>` : '<p>이 구단의 리그 장부는 아직 없습니다. 로스터와 계약 종료일은 등록 정보입니다.</p>'
  if (tab === 'matches') main = (data.recent || []).map(game => `<div class="row">${game.won ? '승' : '패'} ${esc(game.opponent)} ${(game.score || []).join(':')}</div>`).join('') || '<p>끝난 경기가 없습니다.</p>'
  shell(`<div class="panel"><h1>${logoImg(idn.league, idn.team)} ${esc(idn.team)}</h1><p>${esc(idn.league)}</p>${links}${main}</div>`, '/app/team/' + encodeURIComponent(league) + '/' + encodeURIComponent(name))
  document.documentElement.style.setProperty('--team', idn.color || '#17324d')
  document.querySelectorAll('a[href^="/app"]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); go(link.getAttribute('href')) }))
  if (token() && careerId()) await topbar()
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
  shell(`<div class="page-heading"><div><p class="eyebrow">COMPETITIONS & QUALIFICATION</p><h1>대회 · 국제대회 진출권</h1><p>${current.season}시즌 · 2026 규정 적용</p></div></div><section class="panel"><h2>리그별 현황</h2><select id="league-picker">${data.leagues.map(l=>`<option ${l===data.league?'selected':''}>${esc(l)}</option>`).join('')}</select>${widget('standings',{standings:data.standings,club:current.name,league:data.league})}</section><section class="panel"><h2>지역별 출전권</h2><div class="table-scroll"><table><thead><tr><th>리그</th><th>First Stand</th><th>MSI 출전권</th><th>MSI 본선 직행</th><th>월즈 기본</th><th>월즈 현재 확정</th><th>추가 시드 상태</th></tr></thead><tbody>${q.allocations.map(r=>`<tr><td>${esc(r.league)}</td><td>${r.first_stand_slots}</td><td>${r.msi_slots}</td><td>${r.msi_bracket_slots}${r.msi_second_seed_pending?' · 2시드 대기':''}</td><td>${r.worlds_base}</td><td>${r.worlds_confirmed_slots}</td><td>${r.worlds_champion_pending?'MSI 우승팀의 자국 플레이오프 진출 확인 대기':r.worlds_extra_seed?'추가 지역 시드 확보':r.worlds_champion_slot?'MSI 우승팀 출전권 확보':'국제대회 결과 대기'}</td></tr>`).join('')}</tbody></table></div><p>First Stand: MSI 2번 시드 본선 직행 혜택. MSI: 우승팀 월즈 조건부 진출, 차순위 지역 추가 시드.</p><a class="text-link" href="${q.source}" target="_blank" rel="noopener">공식 규정 보기 ↗</a></section><section class="panel"><h2>국제대회 일정</h2>${q.events.map(e=>`<div class="event-card"><b>${esc(e.name)} · ${e.entrants}팀</b><p>${esc(e.start)} ~ ${esc(e.end)}</p><small>${esc(e.format)}</small></div>`).join('')}</section><section class="panel"><h2>등록된 경기 규정</h2>${data.rules.map(r=>`<div class="row"><b>${esc(r.competition)}</b><span>${esc(r.stage)} · BO${r.best_of}</span></div>`).join('')}</section>`,'/app/competition')
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
    media = {colors, logos}
  }
  try {
    worldState=await api('/world');isOperator=worldState.operator===true
    if(isOperator){careerCache=null;localStorage.removeItem('rift-career');if(path==='/app/manager')return go('/app/home');if(path==='/app/home'||path==='/'||path==='/app/schedule')return await operatorDesk(path==='/app/schedule'?path:'/app/home');if(!['/app/clubs','/app/competition','/app/players'].includes(path)&&!/^\/app\/(player|team|entity)\//.test(path))return go('/app/home')}
    if(!managerProfile)managerProfile=await api('/manager-profile')
    if(!isOperator && !managerProfile.complete && path!=='/app/manager')return go('/app/manager')
    if(path==='/app/manager')return await managerSetup()
    if (path === '/' || path === '/app' || path === '/app/') return await continueCareer()
    const entityPath=path.match(/^\/app\/entity\/(manager|owner)\/(\d+)$/)
    if(entityPath){const item=await api('/entity?kind='+entityPath[1]+'&entity='+entityPath[2]);shell(`<div class="page-heading"><div><p class="eyebrow">${entityPath[1]==='owner'?'CLUB OWNER':'MANAGER'}</p><h1>${esc(item.name)}</h1></div></div><section class="panel"><h2>${esc(item.club||item.company||'인물 정보')}</h2>${Object.entries(item.stats||{}).map(([key,value])=>`<div class="metric-pair"><span>${esc(key)}</span><b>${value} / 20</b></div>`).join('')}</section>`,path);await topbar();return}
    if (path === '/app/clubs') return await clubs()
    if (path === '/app/home') return await home()
    if (path === '/app/inbox') return await inbox()
    if (path === '/app/news') return await news()
    if (path === '/app/squad') return await squad('first')
    if (path === '/app/academy') return await squad('academy')
    if (path === '/app/tactics') return await tactics()
    if (path === '/app/training') return await training()
    if (path === '/app/staff') return await managementPage('staff')
    if (path === '/app/medical') return await managementPage('medical')
    if (path === '/app/relations') return await managementPage('relations')
    if (path === '/app/finance') return await managementPage('finance')
    if (path === '/app/vision') return await managementPage('vision')
    if (path === '/app/schedule') return await schedule()
    if (path === '/app/players') return await players()
    if (path === '/app/solo') return await solo()
    if (path === '/app/transfers') return await transfers()
    if (path === '/app/shortlist') return await shortlist()
    if (path === '/app/competition') return await competition()
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
