/* Spectates actual Python engine chunks; never simulates outcomes in the browser. */
let engineViewer=null
function stopEngineViewer(){if(engineViewer){engineViewer.closed=true;cancelAnimationFrame(engineViewer.raf);clearTimeout(engineViewer.timer);engineViewer=null}}
async function mountEngineViewer(fixture,setIndex=0){
  stopEngineViewer()
  const host=document.getElementById('engine-spectator');if(!host)return
  const state={closed:false,frames:[],loaded:0,time:0,speed:8,playing:true,complete:false,units:new Map(),images:new Map(),raf:0,timer:0,lastWall:0,frame:0,focus:null,showScore:false,started:false}
  engineViewer=state
  host.innerHTML=`<div class="spectator-toolbar"><b>${setIndex+1}세트 관전</b><button class="act" id="spectator-play">일시 정지</button><label>재생 속도 <select id="spectator-speed">${[1,2,4,8,16,32].map(n=>`<option value="${n}" ${n===8?'selected':''}>${n}배</option>`).join('')}</select></label><button class="act" id="spectator-reset">처음부터</button><label><input id="spectator-camera" type="checkbox" checked/> 교전 카메라</label><span id="spectator-status">경기 연결 중</span></div><div class="spectator-score"><b class="blue" id="spectator-blue">BLUE</b><strong id="spectator-clock">00:00</strong><b class="red" id="spectator-red">RED</b></div><div class="spectator-layout"><div class="spectator-map-wrap"><canvas id="spectator-map" width="1024" height="1024" aria-label="기존 매치엔진 실제 경기 관전 화면"></canvas><div id="spectator-events" class="spectator-events" aria-live="polite"></div></div><aside id="spectator-players" class="spectator-players"></aside></div><input id="spectator-seek" class="spectator-seek" type="range" min="0" max="0" value="0" step="0.2" aria-label="기록된 경기 시각"/><small>선수·전투·오브젝트는 서버 엔진의 실제 기록입니다. 결과는 재생 종료 후 표시됩니다.</small>`
  const canvas=document.getElementById('spectator-map'),ctx=canvas.getContext('2d');if(!ctx){host.innerHTML='<p class="err">브라우저의 Canvas 지원이 필요합니다.</p>';return}
  const map=new Image();map.src=BASE+'/media/replay-map.png'
  const camera=document.getElementById('spectator-camera'),seek=document.getElementById('spectator-seek')
  document.getElementById('spectator-speed').onchange=e=>{state.speed=Number(e.target.value)}
  document.getElementById('spectator-play').onclick=e=>{state.playing=!state.playing;e.target.textContent=state.playing?'일시 정지':'계속 재생'}
  document.getElementById('spectator-reset').onclick=()=>{state.time=state.frames[0]?.[0]||0;state.frame=0;state.playing=true;state.showScore=false;document.getElementById('spectator-play').textContent='일시 정지'}
  seek.oninput=e=>{state.time=Number(e.target.value);state.showScore=false}
  const icon=unit=>{if(!state.images.has(unit.name)){const img=new Image();img.src='https://ddragon.leagueoflegends.com/cdn/'+CHAMP_PATCH+'/img/champion/'+encodeURIComponent(championMeta[unit.name]?.image?.full||unit.name+'.png');state.images.set(unit.name,img)}return state.images.get(unit.name)}
  const clock=t=>String(Math.floor(t/60)).padStart(2,'0')+':'+String(Math.floor(t%60)).padStart(2,'0')
  let lastStats=-1,lastEvents=''
  function draw(frame,next,blend){
    const positions=new Map(frame[1].map(p=>[p[0],p]));const following=new Map((next?.[1]||[]).map(p=>[p[0],p]));const players=frame[2]||[]
    const events=state.frames.slice(Math.max(0,state.frame-35),state.frame+1).flatMap(f=>f[3]||[]).filter(e=>e.t<=state.time&&e.t>=state.time-10)
    const action=events.filter(e=>e.type==='kill'||e.type==='objective').at(-1)
    let center=[256,256],zoom=1
    if(camera.checked&&action?.p&&state.time-action.t<7){center=action.p;zoom=1.65}
    const view=512/zoom;center=[Math.max(view/2,Math.min(512-view/2,center[0])),Math.max(view/2,Math.min(512-view/2,center[1]))]
    ctx.clearRect(0,0,1024,1024);ctx.fillStyle='#08131c';ctx.fillRect(0,0,1024,1024);ctx.save();ctx.scale(2*zoom,2*zoom);ctx.translate(view/2-center[0],view/2-center[1]);
    if(map.complete&&map.naturalWidth)ctx.drawImage(map,0,0,512,512)
    for(const area of frame[5]||[]){if(!area.p)continue;ctx.beginPath();ctx.arc(area.p[0],area.p[1],area.r||6,0,Math.PI*2);ctx.fillStyle='#ac76fa33';ctx.fill();ctx.strokeStyle='#be95ff88';ctx.lineWidth=.8;ctx.stroke()}
    for(const w of frame[6]||[]){if(!w.p)continue;ctx.fillStyle=w.team===0?'#52e8e3':'#ff7698';ctx.fillRect(w.p[0]-1,w.p[1]-1,2,2)}
    for(const p of frame[1]){
      const meta=state.units.get(p[0]);if(!meta)continue
      let [,x,y,hp]=p;const n=following.get(p[0]);if(n&&Math.hypot(n[1]-x,n[2]-y)<45){x+=(n[1]-x)*blend;y+=(n[2]-y)*blend}
      const team=meta.team===0?'#48bdff':meta.team===1?'#ff626f':'#d7c292';ctx.fillStyle=team;ctx.strokeStyle='#09131d';ctx.lineWidth=1
      if(meta.kind==='champion'){
        const image=icon(meta);ctx.save();ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.clip();ctx.fillRect(x-8,y-8,16,16);if(image.complete&&image.naturalWidth)ctx.drawImage(image,x-8,y-8,16,16);ctx.restore();ctx.strokeStyle=team;ctx.lineWidth=1.5;ctx.beginPath();ctx.arc(x,y,8,0,Math.PI*2);ctx.stroke()
        ctx.fillStyle='#070d12';ctx.fillRect(x-10,y-14,20,3);ctx.fillStyle=team;ctx.fillRect(x-10,y-14,20*Math.max(0,Math.min(1,hp/100)),3)
        ctx.font='bold 5px sans-serif';ctx.textAlign='center';ctx.strokeStyle='#000';ctx.lineWidth=1.7;const label=meta.player_name||championKo(meta.name);ctx.strokeText(label,x,y-17);ctx.fillStyle='#fff';ctx.fillText(label,x,y-17)
      }else if(['tower','nexus','inhibitor'].includes(meta.kind)){
        const radius=meta.kind==='nexus'?9:meta.kind==='tower'?5:4;ctx.fillRect(x-radius,y-radius,radius*2,radius*2);ctx.strokeRect(x-radius,y-radius,radius*2,radius*2);ctx.fillStyle='#0b1822';ctx.fillRect(x-7,y-radius-4,14,2);ctx.fillStyle=team;ctx.fillRect(x-7,y-radius-4,14*hp/100,2)
      }else if(meta.kind==='minion'){ctx.beginPath();ctx.arc(x,y,1.5,0,Math.PI*2);ctx.fill()}
      else{ctx.beginPath();ctx.arc(x,y,meta.name==='Baron'||meta.name==='Dragon'?5:2.8,0,Math.PI*2);ctx.fill();ctx.stroke()}
    }
    for(const effect of frame[4]||[]){
      const a=positions.get(effect.a),b=positions.get(effect.b),from=effect.start||(a?[a[1],a[2]]:null),to=effect.p||(b?[b[1],b[2]]:null)
      if(!to)continue;ctx.strokeStyle=effect.magic?'#c596ff':'#ffd68a';ctx.lineWidth=1.1
      if(from&&effect.kind!=='impact'){ctx.beginPath();ctx.moveTo(...from);ctx.lineTo(...to);ctx.stroke()}
      if(effect.kind==='impact'){ctx.beginPath();ctx.arc(to[0],to[1],3,0,Math.PI*2);ctx.stroke()}
    }
    ctx.restore();document.getElementById('spectator-clock').textContent=clock(state.time);seek.value=state.time
    const kills=[0,0],gold=[0,0];for(const p of players){const u=state.units.get(p.id);if(u&&u.team>=0){kills[u.team]+=p.kda[0];gold[u.team]+=p.gold}}
    document.getElementById('spectator-blue').textContent='BLUE · '+kills[0]+' K · '+(gold[0]/1000).toFixed(1)+'k G'
    document.getElementById('spectator-red').textContent='RED · '+kills[1]+' K · '+(gold[1]/1000).toFixed(1)+'k G'
    if(Math.floor(state.time)!==lastStats){lastStats=Math.floor(state.time);document.getElementById('spectator-players').innerHTML=[0,1].map(team=>'<section><h3 class="'+(team===0?'blue':'red')+'">'+(team===0?'BLUE':'RED')+'</h3>'+players.filter(p=>state.units.get(p.id)?.team===team).map(p=>{const u=state.units.get(p.id);return '<div class="spectator-player '+(p.alive?'':'is-dead')+'">'+championIcon(u.name)+'<div><b>'+esc(u.player_name||championKo(u.name))+'</b><small>'+esc(championKo(u.name))+' · Lv '+p.level+' · '+esc(u.role)+'</small><strong>'+p.kda.join(' / ')+' · CS '+p.cs+'</strong><small>'+Math.round(p.hp)+' / '+p.maxhp+' HP · '+p.gold.toLocaleString('ko-KR')+' G'+(!p.alive?' · 부활 '+p.respawn+'초':'')+'</small><small>'+esc(p.items.join(' · '))+'</small><small>룬 '+esc(p.rune||'—')+' · '+esc(p.summoners.join(' / '))+'</small></div></div>'}).join('')+'</section>').join('')}
    const killEvents=events.filter(e=>e.type==='kill'||e.type==='objective'||e.type==='structure').slice(-4);const signature=JSON.stringify(killEvents)
    if(signature!==lastEvents){lastEvents=signature;document.getElementById('spectator-events').innerHTML=killEvents.map(e=>{const actor=state.units.get(e.killer??e.unit),victim=state.units.get(e.victim);return '<div><b>'+clock(e.t)+'</b> '+esc(e.type==='kill'?(actor?.player_name||championKo(actor?.name||''))+' → '+(victim?.player_name||championKo(victim?.name||'')):e.type==='objective'?(e.name||'오브젝트')+' 처치':'구조물 파괴')+'</div>'}).join('')}
  }
  async function refresh(){
    if(state.closed||!host.isConnected)return
    try{
      const manifest=await api('/spectator?id='+fixture+'&set='+setIndex);if(state.closed)return
      for(const unit of manifest.units||[])state.units.set(unit.id,unit)
      state.complete=manifest.complete;state.manifestChunks=manifest.chunk_count;let fetched=0
      while(state.loaded<manifest.chunk_count&&fetched<12&&!state.closed){
        const data=await api('/spectator-chunk?id='+fixture+'&set='+setIndex+'&chunk='+state.loaded);if(state.closed)return
        for(const f of data.frames||[]){if(!state.frames.length||f[0]>state.frames.at(-1)[0])state.frames.push(f)}state.loaded++;fetched++
      }
      if(state.frames.length){if(!state.started){state.started=true;state.time=state.frames[0][0]};seek.max=state.frames.at(-1)[0]}
      document.getElementById('spectator-status').textContent=state.frames.length?'경기 화면 연결됨':manifest.available===false?'관전 기록 대기':'경기 연결 중'
      if(manifest.available===false&&document.getElementById('engine-spectator')===host&&document.getElementById('match-results')){document.getElementById('spectator-status').textContent='이전 경기에는 전체 관전 기록이 없습니다. 아래 하이라이트를 이용하세요.'}
    }catch(error){if(!state.closed)document.getElementById('spectator-status').textContent='연결 재시도 · '+error.message}
    if(!state.closed&&!(state.complete&&state.loaded===state.manifestChunks))state.timer=setTimeout(refresh,state.loaded?1800:1000)
  }
  function animate(now){
    if(state.closed||!host.isConnected){stopEngineViewer();return}
    const dt=state.lastWall?Math.min(.2,(now-state.lastWall)/1000):0;state.lastWall=now
    if(state.frames.length){
      const end=state.frames.at(-1)[0];if(state.playing)state.time=Math.min(end,state.time+dt*state.speed)
      while(state.frame>0&&state.frames[state.frame][0]>state.time)state.frame--
      while(state.frame+1<state.frames.length&&state.frames[state.frame+1][0]<=state.time)state.frame++
      const frame=state.frames[state.frame],next=state.frames[state.frame+1];draw(frame,next,next?Math.max(0,Math.min(1,(state.time-frame[0])/(next[0]-frame[0]))):0)
      if(state.complete&&state.loaded>0&&state.time>=end&&!state.showScore){state.showScore=true;document.getElementById('spectator-status').textContent='세트 관전 종료';document.dispatchEvent(new CustomEvent('engine-set-viewed',{detail:{fixture,set:setIndex}}))}
    }
    state.raf=requestAnimationFrame(animate)
  }
  refresh();state.raf=requestAnimationFrame(animate)
}

document.addEventListener('engine-set-viewed',event=>{
  const {fixture,set}=event.detail
  const toolbar=document.querySelector('#engine-spectator .spectator-toolbar');if(!toolbar||toolbar.querySelector('[data-next-engine-set]'))return
  const button=document.createElement('button');button.className='act';button.dataset.nextEngineSet='true';button.textContent='다음 세트 · 경기 진행'
  button.onclick=async()=>{
    button.disabled=true
    try{
      const current=await requireCareer();if(!current)return
      const response=await api('/fixtures?id='+current.id);const game=response.fixtures.find(g=>g.id===fixture)
      if(!game)return
      const sets=game.series?.sets||game.result?.sets||[]
      if(sets.length>set+1||game.series?.phase==='ready'&&sets.length===set+1){await mountEngineViewer(fixture,set+1);return}
      if(game.state==='finished'){document.getElementById('match-results').open=true;button.textContent='경기 종료 · 기록 펼침';return}
      if(['choice','draft','draft_pending','swap'].includes(game.series?.phase)){go('/app/draft/'+fixture);return}
      if(game.series?.phase==='feedback'){const note=document.querySelector('#match-feedback-input');if(note)note.focus();button.textContent='세트 피드백 대기';return}
      button.textContent='다음 세트 준비 중'
    }catch(error){button.textContent=error.message}finally{button.disabled=false}
  }
  toolbar.append(button)
})
