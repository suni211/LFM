'use strict';
const el = id => document.getElementById(id);
let token = '';
let busy = false;

async function request(path, data) {
    const headers = {};
    if (token) headers.Authorization = 'Bearer ' + token;
    if (data !== undefined) headers['Content-Type'] = 'application/json';
    const response = await fetch('api/' + path, {
        method: data === undefined ? 'GET' : 'POST',
        headers, body: data === undefined ? undefined : JSON.stringify(data),
        signal: AbortSignal.timeout(10000)
    });
    if (response.status === 409) throw new Error('이미 처리됐거나 이름이 사용 중입니다. 목록을 새로고침하세요.');
    if (response.status === 401) throw new Error('계정과 비밀번호를 확인하거나 다시 로그인하세요.');
    if (!response.ok) throw new Error('요청을 처리하지 못했습니다.');
    return response.json();
}

async function run(action) {
    if (busy) return;
    busy = true;
    try { await action(); }
    catch (error) { el('status').textContent = error.message; }
    finally { busy = false; }
}

async function refresh() {
    const { careers } = await request('careers');
    el('list').replaceChildren();
    for (const career of careers) {
        const row = document.createElement('p');
        row.textContent = career.name + ' · 시즌 ' + career.season + ' / ' + career.week + '주차 ';
        const advance = document.createElement('button');
        advance.textContent = career.role === 'admin' ? '다음 주' : '진행 투표';
        advance.onclick = () => run(async () => {
            const result = await request('advance', {id: career.id, version: career.version});
            await refresh();
            el('status').textContent = result.advanced ? '다음 주로 진행했습니다.' : '투표를 저장했습니다.';
        });
        row.append(advance);
        el('list').append(row);
    }
    if (!careers.length) el('list').textContent = '등록된 커리어가 없습니다.';
}
el('account').onsubmit = event => {
    event.preventDefault();
    const mode = event.submitter?.value || 'login';
    const password = el('password').value;
    el('password').value = '';
    run(async () => {
        token = (await request(mode, {name: el('name').value.trim(), password})).token;
        await refresh();
        el('login').hidden = true;
        el('careers').hidden = false;
        el('status').textContent = '서버에 연결됐습니다.';
    });
};
el('create').onsubmit = event => {
    event.preventDefault();
    run(async () => { await request('careers', {name: el('club').value.trim()}); el('club').value = ''; await refresh(); });
};
el('refresh').onclick = () => run(refresh);
el('logout').onclick = () => { if (!busy) location.reload(); };
