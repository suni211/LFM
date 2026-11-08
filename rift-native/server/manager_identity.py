"""Account-level manager identity, completed before joining the online league."""
import json
import re
ATTRIBUTES=('전술','훈련','협상','동기부여','선수관리','스카우팅')
def init(db):
    db.execute('''CREATE TABLE IF NOT EXISTS account_managers(user_id INTEGER PRIMARY KEY REFERENCES users(id),
        nickname TEXT NOT NULL,name TEXT NOT NULL,stats TEXT NOT NULL)''')
def view(db,uid):
    row=db.execute('SELECT nickname,name,stats FROM account_managers WHERE user_id=?',(uid,)).fetchone()
    return dict(complete=bool(row),nickname=row[0] if row else '',name=row[1] if row else '',
                stats=json.loads(row[2]) if row else dict.fromkeys(ATTRIBUTES,10),attributes=ATTRIBUTES,total=60,minimum=1,maximum=20)
def save(db,uid,data):
    nick=data.get('nickname');name=data.get('name');stats=data.get('stats')
    for text in (nick,name):
        if not isinstance(text,str) or not 1<=len(text.strip())<=30 or any(ord(c)<32 or ord(c)==127 for c in text):
            raise ValueError('닉네임과 이름을 각각 1~30자로 입력하세요.')
    if not isinstance(nick,str) or not re.fullmatch(r'[A-Za-z]{2,20}', nick.strip()):
        raise ValueError('감독 닉네임은 영문 2~20자만 사용할 수 있습니다.')
    existing=db.execute('SELECT user_id FROM account_managers WHERE lower(nickname)=lower(?) AND user_id!=?',(nick.strip(),uid)).fetchone()
    if existing: raise ValueError('이미 사용 중인 감독 닉네임입니다.')
    if not isinstance(stats,dict) or set(stats)!=set(ATTRIBUTES) or any(type(v) is not int or not 1<=v<=20 for v in stats.values()) or sum(stats.values())!=60:
        raise ValueError('감독 능력치는 각각 1~20, 합계 60으로 설정하세요.')
    raw=json.dumps(stats,ensure_ascii=False)
    db.execute('INSERT INTO account_managers VALUES(?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET nickname=excluded.nickname,name=excluded.name,stats=excluded.stats',(uid,nick.strip(),name.strip(),raw))
    # Viewing another club as an operator never changes that club's manager.
    db.execute("UPDATE manager_profiles SET name=?,stats=? WHERE career_id IN (SELECT career_id FROM members WHERE user_id=? AND role='admin')",(name.strip(),raw,uid))
    return view(db,uid)
