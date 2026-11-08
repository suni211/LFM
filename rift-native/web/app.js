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
    if (path === '/app/onboarding') return await onboarding()
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
    if (path === '/app/leagues') return await leagueIndex()
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
function seasonStanding(row) {
  if(!row)return {rank:'미집계',played:0,wins:0,losses:0,sets_won:0,sets_lost:0,diff:0}
  return {...row,diff:(row.sets_won||0)-(row.sets_lost||0),rank:row.rank==null?'미집계':row.rank+'위'}
}
function leagueStandingsTable(rows,league,currentTeam='') {
  return `<div class="table-scroll"><table class="league-table"><thead><tr><th>순위</th><th>구단</th><th>경기</th><th>승</th><th>패</th><th>세트 득실</th><th>득실차</th></tr></thead><tbody>${(rows||[]).map((r,i)=>`<tr class="${r.team===currentTeam?'mine':''}"><td>${r.rank==null?'—':r.rank}</td><td>${logoImg(league,r.team)}<a href="/app/team/${encodeURIComponent(league)}/${encodeURIComponent(r.team)}">${esc(r.team)}</a></td><td>${r.played||0}</td><td>${r.wins||0}</td><td>${r.losses||0}</td><td>${r.sets_won||0}:${r.sets_lost||0}</td><td>${(r.sets_won||0)-(r.sets_lost||0)>0?'+':''}${(r.sets_won||0)-(r.sets_lost||0)}</td></tr>`).join('')}</tbody></table></div>${(rows||[]).every(r=>!r.played)?'<p class="muted-note">아직 완료된 경기가 없습니다. 첫 경기 이후 순위가 확정됩니다.</p>':''}`
}
function frontOfficeCard(p) {
  return `<div class="front-person"><div class="front-role">${esc(p.role||'직책 미확인')}</div><strong>${esc(p.name||'정보 미등록')}</strong><small>${p.source==='real'?'등록된 실제 인물':p.source==='generated'?'게임 생성 인물':'게임 내 직책'}</small></div>`
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
  const tabs=[['overview','구단 개요'],['roster','1군·2군'],['front','프런트'],['finance','재정'],['matches','경기'],['news','뉴스']]
  const links=`<div class="tabs team-tabs">${tabs.map(([k,l])=>`<a class="${active===k?'on':''}" href="/app/team/${encodeURIComponent(league)}/${encodeURIComponent(name)}/${k}">${l}</a>`).join('')}</div>`
  const table=leagueStandingsTable(data.standings||[],league,name)
  const rowNotes=`<div class="fm-metrics"><div><small>리그 순위</small><strong>${esc(s.rank)}</strong></div><div><small>경기</small><strong>${s.played}</strong></div><div><small>승 / 패</small><strong>${s.wins}승 ${s.losses}패</strong></div><div><small>세트 득실</small><strong>${s.sets_won}:${s.sets_lost} (${s.diff>0?'+':''}${s.diff})</strong></div><div><small>담당 감독</small><strong>${esc(data.manager||'정보 미등록')}</strong></div></div>`
  const teamPlayers=(data.players||[]).filter(p=>p.kind==='player')
  const rosterCards=teamPlayers.filter(p=>p.assignment!=='reserve').slice(0,5).map(p=>`<a class="fm-player-line" href="/app/player/${encodeURIComponent(p.id)}">${face(p.id,Boolean(p.photo))}<span><small>${esc(ROLE[p.role]||p.role||'선수')}</small><b>${esc(nickname(p))}</b></span></a>`).join('')||'<p class="empty">1군 주전 선수단이 등록되지 않았습니다.</p>'
  const finance=data.finances?.initialized?`<div class="fm-finance-totals"><div><small>보유 현금</small><strong>${money(data.finances.cash)}</strong></div><div><small>이적 예산</small><strong>${money(data.finances.transfer_budget)}</strong></div><div><small>연봉 총액</small><strong>${money(data.finances.annual_payroll)}</strong></div></div>${cashGraph(data.cash_history||[])}`:'<p class="empty">이 구단의 재정 내역은 공개되지 않았거나 아직 기록이 없습니다.</p>'
  let main=''
  if(active==='overview')main=`<div class="fm-club-dashboard"><section class="panel fm-dashboard-standing"><h2>리그 순위 <a href="/app/league/${encodeURIComponent(league)}">리그 상세</a></h2>${table}</section><section class="panel fm-dashboard-squad"><h2>이번 시즌 1군 · ${teamPlayers.length}명</h2>${rosterCards}<a class="panel-link" href="/app/team/${encodeURIComponent(league)}/${encodeURIComponent(name)}/roster">전체 명단 보기</a></section><section class="panel fm-dashboard-front"><h2>프런트·코칭스태프</h2>${frontOfficePanel(data)}</section><section class="panel fm-dashboard-news"><h2>구단 뉴스</h2>${latestTeamNews(data)}</section><section class="panel fm-dashboard-finance"><h2>재정 흐름</h2>${finance}</section><section class="panel fm-dashboard-form"><h2>최근 공식 경기</h2>${resultStrip(data.recent||[])}</section></div>`
  else if(active==='roster')main=`<section class="panel"><h2>1군 선수 · ${teamPlayers.length}명</h2>${rosterTable(teamPlayers)}</section><section class="panel"><h2>2군 육성 선수 · ${(data.academy||[]).length}명</h2>${rosterTable((data.academy||[]).filter(p=>p.kind==='player'))}</section>`
  else if(active==='front')main=`<section class="panel"><h2>프런트 및 코칭스태프</h2><p class="muted-note">선수와 구분하여 구단주, 감독, 수석코치, 코치, 단장 및 실무진을 직책별로 표시합니다.</p>${frontOfficePanel(data)}</section><section class="panel"><h2>구단 운영 정보</h2><p>담당 감독 · ${esc(data.manager||'미등록')}</p><p>구단주 · ${esc(data.owner||'미등록')}</p></section>`
  else if(active==='finance')main=`<div class="fm-club-finance"><section class="panel"><h2>재정 요약</h2>${finance}</section><section class="panel"><h2>거래 원장</h2>${(data.finances?.ledger||[]).map(n=>`<div class="row"><span>${n.season}시즌 ${n.week}주 · ${esc(n.description)}</span><b>${money(n.amount)}</b></div>`).join('')||'<p class="empty">표시할 거래 원장이 없습니다.</p>'}</section></div>`
  else if(active==='matches')main=`<section class="panel"><h2>${data.season||''}시즌 공식 경기 결과</h2>${resultStrip(data.recent||[])}</section><section class="panel"><h2>시즌 성적</h2>${rowNotes}</section>`
  else if(active==='news')main=`<section class="panel"><h2>구단 소식</h2>${latestTeamNews(data)}</section>`
  else return go('/app/team/'+encodeURIComponent(league)+'/'+encodeURIComponent(name)+'/overview')
  shell(`<div class="fm-team-page"><header class="fm-team-header">${logoImg(idn.league,idn.team)}<div><p class="eyebrow">CLUB INFORMATION · ${esc(idn.league)}</p><h1>${esc(idn.team)}</h1><p>${esc(data.season||'현재')}시즌 · 1군 ${teamPlayers.length}명 · 2군 ${(data.academy||[]).length}명 · 프런트 ${(data.front_office||[]).length}명</p></div><a href="/app/league/${encodeURIComponent(league)}" class="act">${esc(league)} 리그 보기</a></header>${rowNotes}${links}${main}</div>`,'/app/team/'+encodeURIComponent(league)+'/'+encodeURIComponent(name))
  document.documentElement.style.setProperty('--team',idn.color||'#17324d')
  if(token()&&careerId())await topbar()
}
async function leagueIndex() {
  const board=await api('/clubs')
  const leagues=[...new Set((board.clubs||[]).map(c=>c.league).filter(Boolean))].sort()
  shell(`<div class="page-heading"><div><p class="eyebrow">DOMESTIC COMPETITIONS</p><h1>리그 정보</h1><p>모든 리그의 구단 및 순위를 독립적으로 확인할 수 있습니다.</p></div></div><div class="fm-league-index">${leagues.map(l=>`<a class="panel" href="/app/league/${encodeURIComponent(l)}"><p class="eyebrow">LEAGUE DIRECTORY</p><h2>${esc(l)}</h2><p>${board.clubs.filter(c=>c.league===l).length}개 구단</p></a>`).join('')}</div>`,'/app/leagues')
  await topbar()
}
async function leagueOverview(league) {
  const data=await api('/league-overview?league='+encodeURIComponent(league))
  const standings=data.standings||[],completed=(data.fixtures||[]).filter(g=>g.state==='finished'),upcoming=(data.fixtures||[]).filter(g=>g.state!=='finished')
  const games=(fixtures)=>fixtures.map(g=>`<div class="fm-match-item"><small>${g.season}시즌 ${g.week}주 · ${esc(g.stage||'정규 시즌')}</small><div><b>${esc(g.home)}</b><strong>${g.score?g.score.join(' : '):'VS'}</strong><b>${esc(g.away)}</b></div></div>`).join('')||'<p class="empty">아직 등록된 경기가 없습니다.</p>'
  const teams=(data.clubs||[]).map(c=>`<a class="fm-league-club" href="/app/team/${encodeURIComponent(league)}/${encodeURIComponent(c.team)}">${logoImg(league,c.team)}<span>${esc(c.team)}</span><small>${c.kind==='user'?'유저 감독':'AI 구단'}</small></a>`).join('')
  shell(`<div class="fm-league-page"><header class="fm-team-header"><div><p class="eyebrow">LEAGUE & COMPETITION</p><h1>${esc(league)}</h1><p>${data.season}시즌 ${data.week}주차 · 등록 구단 ${(data.clubs||[]).length}팀</p></div><a class="act" href="/app/leagues">전체 리그</a></header><div class="fm-league-metrics"><div><small>등록 구단</small><strong>${(data.clubs||[]).length}</strong></div><div><small>종료된 경기</small><strong>${completed.length}</strong></div><div><small>진행 예정 경기</small><strong>${upcoming.length}</strong></div></div><div class="fm-league-dashboard"><section class="panel fm-league-ranking"><h2>${esc(league)} 순위표</h2>${leagueStandingsTable(standings,league)}</section><section class="panel fm-league-games"><h2>최근 경기 결과</h2>${games(completed.slice(-8).reverse())}<h2>다음 일정</h2>${games(upcoming.slice(0,8))}</section><section class="panel fm-league-clubs"><h2>참가 구단</h2><div class="fm-league-club-list">${teams||'<p class="empty">등록된 구단이 없습니다.</p>'}</div></section></div></div>`,'/app/leagues')
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
    if (path === '/app/onboarding') return await onboarding()
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
