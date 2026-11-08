#!/usr/bin/env python3
"""Evidence-only bulk nationality reconciliation from Leaguepedia Players Cargo.

No countries are inferred from nickname, role, employer, team, nationality-like
real names, competitive league, or region. Match both IGN and real-world name;
ambiguous or contradictory entries remain unset for human review.
"""
import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parents[1]
PEOPLE = ROOT / "assets" / "people.json"
OVERRIDES = ROOT / "assets" / "nationality-overrides.json"
REPORT = ROOT / "nationality-cargo-report.json"
ENDPOINT = "https://lol.fandom.com/api.php"
FIELDS = "ID,Name,NameFull,OverviewPage,NationalityPrimary,Role,Team"
COUNTRY_ALIASES = {
    "South Korea": "KR", "Korea": "KR", "Republic of Korea": "KR",
    "North Korea": "KP", "China": "CN", "People's Republic of China": "CN",
    "Taiwan": "TW", "Taiwan, Province of China": "TW", "Hong Kong": "HK",
    "Macau": "MO", "Macao": "MO", "Vietnam": "VN", "Viet Nam": "VN",
    "United States": "US", "USA": "US", "United Kingdom": "GB",
    "UK": "GB", "Russia": "RU", "Russian Federation": "RU",
    "Turkey": "TR", "Türkiye": "TR", "Czech Republic": "CZ",
    "Czechia": "CZ", "Kosovo": "XK", "Iran": "IR", "United Arab Emirates": "AE",
}
NAMES_KO = {
    "KR":"대한민국","CN":"중국","JP":"일본","TW":"대만","HK":"홍콩","MO":"마카오",
    "VN":"베트남","TH":"태국","PH":"필리핀","ID":"인도네시아","MY":"말레이시아",
    "SG":"싱가포르","US":"미국","CA":"캐나다","BR":"브라질","AR":"아르헨티나",
    "MX":"멕시코","CL":"칠레","GB":"영국","FR":"프랑스","DE":"독일",
    "ES":"스페인","PT":"포르투갈","IT":"이탈리아","NL":"네덜란드",
    "BE":"벨기에","DK":"덴마크","SE":"스웨덴","NO":"노르웨이",
    "FI":"핀란드","PL":"폴란드","CZ":"체코","TR":"튀르키예",
    "UA":"우크라이나","RU":"러시아","AU":"호주","NZ":"뉴질랜드",
    "ZA":"남아프리카공화국","GR":"그리스","RO":"루마니아",
    "HU":"헝가리","RS":"세르비아","HR":"크로아티아","CH":"스위스",
    "AT":"오스트리아","IE":"아일랜드","IL":"이스라엘",
    "SA":"사우디아라비아","AE":"아랍에미리트","IR":"이란",
    "IN":"인도","BD":"방글라데시","PK":"파키스탄","EG":"이집트",
    "MA":"모로코","DZ":"알제리","TN":"튀니지","PE":"페루",
    "CO":"콜롬비아","UY":"우루과이","VE":"베네수엘라",
    "EC":"에콰도르","BO":"볼리비아","PY":"파라과이",
}
try:
    import pycountry
except ImportError:
    pycountry = None

def norm(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c.casefold() for c in text if c.isalnum() and not unicodedata.combining(c))

def name_parts(text):
    text = unicodedata.normalize("NFKD", str(text or ""))
    # Handle both "Park Seung-gyu" and "Seung-gyu Park" with word order.
    return sorted(re.findall(r"[a-z0-9]+", "".join(
        c for c in text.casefold() if not unicodedata.combining(c))))

def same_real_name(a,b):
    if not a or not b:
        return False
    return norm(a) == norm(b) or name_parts(a) == name_parts(b)

def country_code(raw):
    raw = str(raw or "").strip()
    if not raw or "," in raw and raw not in COUNTRY_ALIASES and len(raw) > 50:
        return None
    if raw in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[raw]
    if len(raw)==2 and raw.isalpha():
        return raw.upper()
    if not pycountry:
        return None
    try:
        country = pycountry.countries.lookup(raw)
        return country.alpha_2
    except LookupError:
        return None

def from_api(limit,offset,delay):
    params = urllib.parse.urlencode(dict(
        action="cargoquery",tables="Players",fields=FIELDS,
        where="NationalityPrimary IS NOT NULL AND NationalityPrimary != ''",
        limit=limit,offset=offset,format="json"
    ))
    url = ENDPOINT+"?"+params
    last=None
    for attempt in range(4):
        try:
            req=urllib.request.Request(url,headers={
                "User-Agent":"RiftManagerNationalityAudit/1.0 (github.com/suni211/LFM; publicly sourced, noncommercial)",
                "Accept":"application/json","Accept-Encoding":"identity",
            })
            with urllib.request.urlopen(req,timeout=35) as resp:
                payload=json.load(resp)
            if "error" in payload:
                raise RuntimeError("Leaguepedia Cargo error: "+str(payload["error"])[:300])
            items=payload.get("cargoquery")
            if not isinstance(items,list):
                raise RuntimeError("Cargo response missing cargoquery: "+str(payload)[:300])
            time.sleep(delay)
            return [x.get("title",{}) for x in items]
        except (urllib.error.URLError,TimeoutError,ValueError,RuntimeError) as exc:
            last=exc
            time.sleep(min(30,2**attempt*3))
    raise RuntimeError("Leaguepedia nationality API unavailable: "+str(last))

def collect(max_pages,delay,sample_json=None):
    if sample_json:
        payload=json.loads(pathlib.Path(sample_json).read_text(encoding="utf-8"))
        items=payload.get("cargoquery",payload) if isinstance(payload,dict) else payload
        return [x.get("title",x) for x in items]
    rows=[]
    for page in range(max_pages):
        batch=from_api(500,page*500,delay)
        rows.extend(batch)
        print("Cargo pages",page+1,"nationality rows",len(rows),flush=True)
        if len(batch)<500:
            return rows
    raise RuntimeError("Page cap reached before finishing Cargo nationality records; refusing partial import")

def match(people,rows,existing):
    by_ign=defaultdict(list)
    for person in people:
        if person.get("real_person") and person.get("id") and person.get("nickname"):
            by_ign[norm(person["nickname"])].append(person)
    candidates=defaultdict(list)
    misses=defaultdict(int)
    for row in rows:
        ign=row.get("ID") or ""
        if not ign:
            continue
        matches=by_ign.get(norm(ign),[])
        if not matches:
            continue
        country=row.get("NationalityPrimary","")
        code=country_code(country)
        if not code:
            misses["unsupported-country"]+=1
            continue
        wiki_name=row.get("Name") or row.get("NameFull") or ""
        page=row.get("OverviewPage") or ""
        if not wiki_name or not page:
            misses["no-name-or-source"]+=1
            continue
        for p in matches:
            if not same_real_name(wiki_name,p.get("real_name")):
                misses["name-disagreement"]+=1
                continue
            url="https://lol.fandom.com/wiki/"+urllib.parse.quote(page.replace(" ","_"),safe="/()")
            candidates[p["id"]].append(dict(
                code=code,name=NAMES_KO.get(code,country.strip()),
                source=url,
                verified_on=dt.date.today().isoformat(),
                match="Leaguepedia Players: exact IGN + reordered-equivalent real name",
                source_field="NationalityPrimary",
                wiki_id=ign,wiki_name=wiki_name,
            ))
    assignments={};ambiguous=[];conflicts=[]
    for p in people:
        pid=p["id"]
        options=candidates.get(pid,[])
        unique={row["code"] for row in options}
        if len(unique)>1:
            ambiguous.append(dict(id=pid,nickname=p.get("nickname"),codes=sorted(unique)))
            continue
        if not options:
            continue
        row=options[0]
        original=p.get("nationality_code")
        prior=existing.get(pid,{})
        prior_code=original or prior.get("code")
        if prior_code and prior_code!=row["code"]:
            conflicts.append(dict(id=pid,nickname=p.get("nickname"),
                stored=prior_code,leaguepedia=row["code"],source=row["source"]))
            continue
        if prior_code:
            continue
        assignments[pid]=row
    return assignments,ambiguous,conflicts,dict(misses)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--max-pages",type=int,default=140)
    parser.add_argument("--delay",type=float,default=0.9)
    parser.add_argument("--source-json",help="offline fixture for unit/integration tests")
    parser.add_argument("--dry-run",action="store_true")
    args=parser.parse_args()
    source=json.loads(PEOPLE.read_text(encoding="utf-8"))
    p=source["people"]
    filedata=json.loads(OVERRIDES.read_text(encoding="utf-8")) if OVERRIDES.exists() else {"people":{}}
    existing=filedata["people"]
    rows=collect(args.max_pages,args.delay,args.source_json)
    additions,ambiguous,conflicts,misses=match(p,rows,existing)
    identified=set(x["id"] for x in p if x.get("nationality_code"))|set(existing)|set(additions)
    report=dict(total=len(p),cargo_rows=len(rows),previous_overrides=len(existing),
                added=len(additions),mapped_after=len(identified),missing=len(p)-len(identified),
                ambiguous=ambiguous,conflicts=conflicts,unmatched_breakdown=misses,
                policy="No inference from league/team/region; IGN and legal name must both match")
    print(json.dumps({k:v for k,v in report.items() if k not in
        ("ambiguous","conflicts")},ensure_ascii=False,indent=2),flush=True)
    if not args.dry_run:
        filedata["people"].update(additions)
        OVERRIDES.write_text(json.dumps(filedata,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
        REPORT.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    if not rows:
        sys.exit("No Leaguepedia player rows returned; refusing to claim verification")

if __name__=="__main__":
    main()
