from pathlib import Path
p=Path('rift-native/web/app.js');s=p.read_text(encoding='utf-8');s=s.replace('let careerCache = null','let careerCache = null\nlet managerProfile = null\nlet isOperator = false',1)
s=s.replace("  if (!item || !item.logo) return ''", "  if (!item || !item.logo) return `<span class=\"club-monogram\" aria-label=\"${esc(team)}\">${esc((team||'RM').slice(0,2))}</span>`")
s=s.replace('src="${BASE}/media/${esc(item.logo)}"','style="background:${esc(item.background || \'#dce3ed\')}" src="${BASE}/media/${esc(item.logo)}"',1)
s=s.replace("function face(id) { return `<img class=\"face\" alt=\"\" src=\"${BASE}/media/portraits/${esc(id)}.png\" onerror=\"this.remove()\"/>` }", "function face(id) { return `<span class=\"face-frame\"><img class=\"face\" alt=\"선수 얼굴\" src=\"${BASE}/media/portraits/${esc(id)}.png\" onerror=\"this.style.display='none';this.nextElementSibling.hidden=false\"/><span class=\"face-placeholder\" hidden title=\"등록된 얼굴 없음\">●</span></span>` }")
s=s.replace("['대회·경기',['schedule','competition','data']],['운영',['clubs']]", "['대회·경기',['schedule','competition','data']],...(isOperator?[['운영',['clubs']]]:[])")
s=s.replace('<header id="top"></header><nav id="navigation">','<header id="masthead"><div id="top"></div><nav id="navigation">')
s=s.replace('${menu}<a class="account-link" href="/app/clubs">구단 전환</a>', '${menu}<a class="account-link" href="/app/manager">감독 프로필</a>')
s=s.replace('로그아웃</button></nav><main','로그아웃</button></nav></header><main')
s=s.replace("      go('/app/clubs')", "      careerCache=null;managerProfile=null;localStorage.removeItem('rift-career');go('/app/manager')",1)
s=s.replace("  const [mine, board] = await Promise.all([api('/careers'), api('/clubs')])", "  const [mine, board] = await Promise.all([api('/careers'), api('/clubs')])\n  if(mine.careers.length && !isOperator)return go('/app/home')")
s=s.replace('board.clubs.map(club =>', 'board.clubs.filter(club=>isOperator || !club.claimed).map(club =>',1)
s=s.replace("      let result\n      try { result = await api('/careers', {mode:'enter', team_key:button.dataset.team}) }\n      catch { result = await api('/careers', {mode:'takeover', team_key:button.dataset.team}) }", "      const result = await api('/careers', {mode:isOperator?'enter':'takeover', team_key:button.dataset.team})")
s=s.replace("  await topbar()\n}\nasync function requireCareer", "  if(!isOperator && !mine.careers.length){document.getElementById('view').insertAdjacentHTML('afterbegin','<form class=\"panel\" id=\"new-club\"><h2>새 구단 창단</h2><label>구단 이름 <input name=\"clubName\" required maxlength=\"40\"/></label><button class=\"act\">창단하고 시작</button><p class=\"err\"></p></form>');document.getElementById('new-club').onsubmit=async e=>{e.preventDefault();const form=e.currentTarget;try{const r=await api('/careers',{mode:'create',name:form.elements.clubName.value.trim()});localStorage.setItem('rift-career',r.id);careerCache=null;go('/app/home')}catch(err){form.querySelector('.err').textContent=err.message}}}\n  await topbar()\n}\nasync function requireCareer",1)
s=s.replace("  if (!careerId()) { go('/app/clubs'); return null }\n  return career()", "  const current=await career();if(!current){go('/app/clubs');return null}return current",1)
a=s.index('function personLink(');b=s.index('async function tactics()',a)
s=s[:a]+'''function nickname(person) {return person.nickname_ko || person.nickname || person.name || '이름 확인 중'}
function personLink(person) {
  return `<a href="/app/player/${esc(person.id)}">${face(person.id)}<span>${esc(nickname(person))}<small>${esc(person.real_name_ko || person.display_name_ko || person.real_name || '')}</small></span></a>`
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
  await topbar()
}
''' +s[b:]
a=s.index('async function players(');b=s.index('async function player(',a)
s=s[:a]+'''async function players(query='',page=0,origin='all') {
  const current=await requireCareer();if(!current)return
  const data=await api('/people?id='+current.id+'&kind=player&page='+page+'&query='+encodeURIComponent(query))
  const rows=data.people.filter(p=>origin==='all'||(origin==='real'?p.real_person:!p.real_person))
  shell(`<div class="panel"><h1>선수 데이터베이스</h1><p>전체 ${data.total}명 · ${page+1} / ${Math.max(1,Math.ceil(data.total/data.page_size))}페이지</p><form id="player-search" class="roster-controls"><input id="q" aria-label="선수 검색" placeholder="한국어 이름 · 닉네임 · 구단" value="${esc(query)}"/><button class="act">검색</button><select id="origin"><option value="all">실존·생성 전체</option><option value="real">실존 선수</option><option value="generated">생성 선수</option></select></form>${rosterTable(rows)}<div class="roster-controls"><button class="act" id="prev-page" ${page===0?'disabled':''}>이전</button><span>${page+1}페이지</span><button class="act" id="next-page" ${(page+1)*data.page_size>=data.total?'disabled':''}>다음</button></div></div>`,'/app/players')
  document.getElementById('origin').value=origin
  document.getElementById('player-search').onsubmit=e=>{e.preventDefault();players(document.getElementById('q').value,0,document.getElementById('origin').value)}
  document.getElementById('origin').onchange=e=>players(query,page,e.target.value)
  document.getElementById('prev-page').onclick=()=>players(query,page-1,origin)
  document.getElementById('next-page').onclick=()=>players(query,page+1,origin)
  await topbar()
}
''' +s[b:]
# Require account manager creation before any club route, including deep links.
s=s.replace("  try {\n    if (path === '/'", "  try {\n    if(!managerProfile)managerProfile=await api('/manager-profile')\n    isOperator=(await api('/world')).operator===true\n    if(!managerProfile.complete && path!=='/app/manager')return go('/app/manager')\n    if(path==='/app/manager')return await managerSetup()\n    if (path === '/'",1)
s=s.replace("const name = person.display_name || person.nickname", "const name = person.nickname_ko || person.display_name || person.nickname")
s=s.replace("${esc(person.display_name || person.nickname)}", "${esc(nickname(person))}")
p.write_text(s,encoding='utf-8')
