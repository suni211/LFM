#!/usr/bin/env python3
"""Conservative, reproducible nationality reconciliation for the R/M people catalog.

Only a Leaguepedia Player + real-name identity match may assign a nationality.
A region, league, team, nickname alone, or a person's romanized name alone is
never sufficient evidence of nationality. Existing edits are not overwritten.
"""
import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "assets" / "people.json"
API = "https://lol.fandom.com/api.php"
COLUMNS = "Player,OverviewPage,Name,NameFull,NationalityPrimary,Nationality"
COUNTRIES = {
    "south korea": ("KR", "대한민국"), "korea": ("KR", "대한민국"),
    "north korea": ("KP", "북한"), "china": ("CN", "중국"),
    "taiwan": ("TW", "대만"), "hong kong": ("HK", "홍콩"),
    "macau": ("MO", "마카오"), "japan": ("JP", "일본"),
    "vietnam": ("VN", "베트남"), "thailand": ("TH", "태국"),
    "philippines": ("PH", "필리핀"), "indonesia": ("ID", "인도네시아"),
    "malaysia": ("MY", "말레이시아"), "singapore": ("SG", "싱가포르"),
    "australia": ("AU", "호주"), "new zealand": ("NZ", "뉴질랜드"),
    "united states": ("US", "미국"), "united states of america": ("US", "미국"),
    "usa": ("US", "미국"), "canada": ("CA", "캐나다"),
    "mexico": ("MX", "멕시코"), "brazil": ("BR", "브라질"),
    "argentina": ("AR", "아르헨티나"), "chile": ("CL", "칠레"),
    "colombia": ("CO", "콜롬비아"), "peru": ("PE", "페루"),
    "uruguay": ("UY", "우루과이"), "venezuela": ("VE", "베네수엘라"),
    "united kingdom": ("GB", "영국"), "uk": ("GB", "영국"),
    "france": ("FR", "프랑스"), "germany": ("DE", "독일"),
    "spain": ("ES", "스페인"), "portugal": ("PT", "포르투갈"),
    "italy": ("IT", "이탈리아"), "poland": ("PL", "폴란드"),
    "sweden": ("SE", "스웨덴"), "denmark": ("DK", "덴마크"),
    "norway": ("NO", "노르웨이"), "finland": ("FI", "핀란드"),
    "netherlands": ("NL", "네덜란드"), "belgium": ("BE", "벨기에"),
    "switzerland": ("CH", "스위스"), "austria": ("AT", "오스트리아"),
    "turkey": ("TR", "튀르키예"), "türkiye": ("TR", "튀르키예"),
    "greece": ("GR", "그리스"), "czech republic": ("CZ", "체코"),
    "czechia": ("CZ", "체코"), "slovakia": ("SK", "슬로바키아"),
    "hungary": ("HU", "헝가리"), "romania": ("RO", "루마니아"),
    "bulgaria": ("BG", "불가리아"), "croatia": ("HR", "크로아티아"),
    "serbia": ("RS", "세르비아"), "slovenia": ("SI", "슬로베니아"),
    "ukraine": ("UA", "우크라이나"), "russia": ("RU", "러시아"),
    "belarus": ("BY", "벨라루스"), "lithuania": ("LT", "리투아니아"),
    "latvia": ("LV", "라트비아"), "estonia": ("EE", "에스토니아"),
    "israel": ("IL", "이스라엘"), "egypt": ("EG", "이집트"),
    "morocco": ("MA", "모로코"), "south africa": ("ZA", "남아프리카공화국"),
    "india": ("IN", "인도"), "pakistan": ("PK", "파키스탄"),
    "saudi arabia": ("SA", "사우디아라비아"), "united arab emirates": ("AE", "아랍에미리트"),
}

def simple(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    return "".join(ch for ch in value if ch.isalnum() and not unicodedata.combining(ch))

def name_signature(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    words = re.findall(r"[^\W_]+", value, flags=re.UNICODE)
    return tuple(sorted("".join(ch for ch in word if not unicodedata.combining(ch)) for word in words))

def identity_matches(person, entry):
    original = name_signature(person.get("real_name"))
    if not original:
        return False
    for key in ("Name", "NameFull"):
        value = entry.get(key, "")
        if value and original == name_signature(value):
            return True
    return False

def country_from(entry):
    value = str(entry.get("NationalityPrimary") or "").strip()
    # Do not silently infer nationality from the birthplace, team, or region.
    if not value or "," in value or ";" in value:
        return None
    return COUNTRIES.get(value.casefold())

def source_url(entry):
    name = str(entry.get("OverviewPage") or entry.get("Player") or "")
    return "https://lol.fandom.com/wiki/" + urllib.parse.quote(name.replace(" ", "_"), safe="/()")

def groups(items, amount=20):
    for index in range(0, len(items), amount):
        yield items[index:index+amount]

def fetch_entries(people):
    names = sorted({p.get("nickname", "").strip() for p in people
                    if p.get("real_person") and p.get("nickname")}, key=str.casefold)
    result, failures = [], []
    for group in groups(names):
        quoted = ",".join("'" + name.replace("'", "''") + "'" for name in group)
        params = {
            "action": "cargoquery", "format": "json", "tables": "Players",
            "fields": COLUMNS, "where": "Players.Player IN (" + quoted + ")",
            "limit": "500",
        }
        url = API + "?" + urllib.parse.urlencode(params)
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "LFM-Nationality-Audit/1.0 (Leaguepedia Cargo; source attribution)"
            })
            with urllib.request.urlopen(request, timeout=25) as response:
                data = json.load(response)
            if "error" in data:
                raise ValueError(str(data["error"]))
            result.extend(item.get("title", item) for item in data.get("cargoquery", []))
        except (urllib.error.URLError, ValueError, TimeoutError, OSError) as exc:
            failures.append({"nicknames": group, "error": str(exc)})
        time.sleep(0.65)
    return result, failures

def reconcile(people, records):
    index = defaultdict(list)
    for item in records:
        entry = item.get("title", item)
        nick = simple(entry.get("Player"))
        if nick:
            index[nick].append(entry)
    report = []
    for person in people:
        id_, nick = person["id"], person.get("nickname") or person.get("name", "")
        note = {"id": id_, "nickname": nick, "real_name": person.get("real_name"),
                "team": person.get("team"), "kind": person.get("kind")}
        if not person.get("real_person"):
            note["status"] = "generated"
            report.append(note)
            continue
        same_nick = index.get(simple(nick), [])
        same_person = [entry for entry in same_nick if identity_matches(person, entry)]
        supported = [(entry, country_from(entry)) for entry in same_person]
        supported = [(entry, country) for entry, country in supported if country]
        distinct = {country[0] for _, country in supported}
        existing_code = person.get("nationality_code")
        existing_label = person.get("nationality_name_ko")
        if len(distinct) > 1:
            note["status"] = "conflict"
            note["reason"] = "matching identity has conflicting nationality records"
        elif len(distinct) == 1:
            entry, country = supported[0]
            if existing_code and existing_code != country[0]:
                note["status"] = "conflict"
                note["reason"] = "preexisting country code disagrees with Leaguepedia"
            elif existing_label and existing_label != country[1] and not existing_code:
                note["status"] = "needs_review"
                note["reason"] = "preexisting nationality label is different or non-standard"
            else:
                person["nationality_code"] = country[0]
                person["nationality_name_ko"] = country[1]
                person["nationality_source"] = source_url(entry)
                person["nationality_verification"] = "nickname_and_real_name"
                note["status"] = "matched"
                note["nationality_code"] = country[0]
                note["nationality_source"] = person["nationality_source"]
        elif existing_code or existing_label:
            note["status"] = "preexisting_unverified"
            note["reason"] = "catalog value retained; no source-matched verification"
        else:
            note["status"] = "unresolved"
            note["reason"] = ("same nickname, different or missing real name"
                              if same_nick else "profile not found")
        report.append(note)
    return report

def run():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--source-json", type=Path, help="saved Leaguepedia cargoquery JSON or list of rows")
    parser.add_argument("--report", type=Path, default=ROOT / "nationality-audit.json")
    parser.add_argument("--apply", action="store_true", help="write ONLY source-matched changes")
    parser.add_argument("--require-complete", action="store_true",
                        help="fail if any real registered person remains unverified")
    args = parser.parse_args()
    data = json.loads(args.catalog.read_text(encoding="utf-8"))
    people = data["people"]
    if len(people) != len({person["id"] for person in people}):
        raise ValueError("duplicate person IDs")
    if args.source_json:
        raw = json.loads(args.source_json.read_text(encoding="utf-8"))
        records = raw if isinstance(raw, list) else raw.get("cargoquery", raw.get("records", []))
        failures = []
    else:
        records, failures = fetch_entries(people)
    report = reconcile(people, records)
    counts = dict(Counter(item["status"] for item in report))
    outcome = {
        "audited_at": datetime.now(timezone.utc).isoformat(),
        "total": len(people),
        "by_kind": dict(Counter(person.get("kind") for person in people)),
        "status_counts": counts,
        "source": API,
        "fetch_failures": failures,
        "people": report,
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(outcome, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.apply:
        if failures:
            print("WARNING: some source requests failed; existing values retained.", file=sys.stderr)
        args.catalog.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"total": len(people), "status_counts": counts,
                      "fetch_failures": len(failures), "applied": args.apply,
                      "report": str(args.report)}, ensure_ascii=False))
    if args.require_complete and any(x["status"] != "matched" for x in report if x["status"] != "generated"):
        return 2
    return 0

if __name__ == "__main__":
    sys.exit(run())
