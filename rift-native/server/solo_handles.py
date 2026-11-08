"""Short, distinct English solo-queue handles for fictional players only.

Single pronounceable names (4-8 Latin letters), not word concatenations.
Nicknames remain stable after assignment and never rename real players.
"""
import hashlib
import re

CURATED=("""
Aven Kiro Nox Raze Kaze Tavi Riven Zeph Varo Luma Kade
Vex Neru Yuki Rook Arix Lune Jett Juno Axo Faye
Daro Riku Yaro Torin Vail Ryn Drax Zeon Tyro
Haru Aro Taro Kora Vale Reni Yori Venn
Zeno Sora Ryko Nari Elio Nevi Kian Roan
Ivo Teya Zeri Lior Mira Aero Rivo Sevi
Sael Kero Dovi Savi Arlo Dren Zila Vira
Zion Theo Roza Fenn Talon Rian Kiva Enzo
Maro Kito Nyro Javi Kora Reno Keno Ilya
Pavo Oryn Silo Kylin Lumi Vero Lani
""").split()
ONSET=('', 'b','c','d','f','g','h','j','k','l','m','n','p','r','s','t','v','w','y','z',
       'br','cr','dr','gr','tr','sh','sk','fl')
VOWEL=('a','e','i','o','u','ae','ai','io')
END=('','n','r','s','x','l','m','k','v','z')

def valid(nickname):
    return bool(re.fullmatch('[A-Za-z]{4,8}', str(nickname)))

def _fingerprint(nickname):
    low=nickname.casefold()
    return {low[:i]+low[i+1:] for i in range(len(low))}

def signatures_for(used):
    """Avoid near-identical solo handles without expensive edit-distance loops."""
    output=set()
    for item in used:
        if valid(item):output.update(_fingerprint(item))
    return output

def choose(seed, used, signatures):
    """Seed-stable handle; used and signatures are updated on success."""
    def free(name):
        low=name.casefold()
        if not valid(name) or low in used:return False
        if _fingerprint(name) & signatures:return False
        return True
    digest=hashlib.sha256(str(seed).encode()).digest()
    start=int.from_bytes(digest[:4],'big')%len(CURATED)
    for k in range(len(CURATED)):
        name=CURATED[(start+k)%len(CURATED)]
        if free(name):
            used.add(name.casefold())
            signatures.update(_fingerprint(name))
            return name
    for attempt in range(30000):
        raw=hashlib.sha256(f'{seed}:short-v3:{attempt}'.encode()).digest()
        name=''.join(ONSET[raw[2*i]%len(ONSET)]+VOWEL[raw[2*i+1]%len(VOWEL)]
                     for i in range(2))
        name+=END[raw[5]%len(END)]
        name=name.capitalize()
        if free(name):
            used.add(name.casefold())
            signatures.update(_fingerprint(name))
            return name
    raise ValueError('exhausted available short esports nicknames')
