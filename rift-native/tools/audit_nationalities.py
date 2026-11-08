#!/usr/bin/env python3
"""Audit and apply VERIFIED LFM nationality mappings, never infer from region/team."""
import argparse
import collections
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "assets" / "people.json"
NAMES = {
    "KR": "대한민국", "CN": "중국", "TW": "대만", "HK": "홍콩", "MO": "마카오",
    "JP": "일본", "VN": "베트남", "TH": "태국", "PH": "필리핀",
    "ID": "인도네시아", "MY": "말레이시아", "SG": "싱가포르",
    "US": "미국", "CA": "캐나다", "BR": "브라질", "AR": "아르헨티나",
    "MX": "멕시코", "PE": "페루", "CL": "칠레", "CO": "콜롬비아",
    "FR": "프랑스", "DE": "독일", "ES": "스페인", "PT": "포르투갈",
    "IT": "이탈리아", "GB": "영국", "PL": "폴란드", "TR": "튀르키예",
    "SE": "스웨덴", "DK": "덴마크", "NO": "노르웨이", "FI": "핀란드",
    "NL": "네덜란드", "BE": "벨기에", "CH": "스위스", "AT": "오스트리아",
    "CZ": "체코", "SK": "슬로바키아", "HU": "헝가리", "RO": "루마니아",
    "BG": "불가리아", "GR": "그리스", "UA": "우크라이나", "RU": "러시아",
    "RS": "세르비아", "HR": "크로아티아", "SI": "슬로베니아",
    "BA": "보스니아 헤르체고비나", "LT": "리투아니아",
    "LV": "라트비아", "EE": "에스토니아", "BY": "벨라루스",
    "AU": "호주", "NZ": "뉴질랜드", "IN": "인도", "PK": "파키스탄",
    "IL": "이스라엘", "EG": "이집트", "ZA": "남아프리카 공화국",
}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapping", type=Path, help="UTF-8 CSV: id,nickname,real_name,code,source")
    ap.add_argument("--apply", action="store_true", help="Actually update people.json after validation")
    ap.add_argument("--report", type=Path, default=ROOT / "nationality-audit.json")
    ap.add_argument("--queue", type=Path, default=ROOT / "nationality-review.csv")
    args = ap.parse_args()
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    people = data["people"]
    ids = [p["id"] for p in people]
    if len(set(ids)) != len(ids):
        raise SystemExit("Duplicate person IDs; refusing to update")
    index = {p["id"]: p for p in people}
    approved = {}
    if args.mapping:
        with args.mapping.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                pid = row.get("id", "").strip()
                p = index.get(pid)
                if p is None or pid in approved:
                    raise SystemExit(f"Unknown/duplicate ID: {pid}")
                if row.get("nickname", "").strip().casefold() != (p.get("nickname") or "").strip().casefold():
                    raise SystemExit(f"Nickname mismatch: {pid}")
                if row.get("real_name", "").strip().casefold() != (p.get("real_name") or "").strip().casefold():
                    raise SystemExit(f"Real-name mismatch: {pid}")
                code = row.get("code", "").strip().upper()
                source = row.get("source", "").strip()
                if code not in NAMES:
                    raise SystemExit(f"Unsupported nationality code {code} for {pid}")
                if not source.startswith("https://"):
                    raise SystemExit(f"Missing HTTPS verification source for {pid}")
                if p.get("nationality_code") and p["nationality_code"] != code:
                    raise SystemExit(f"Existing nationality conflict for {pid}")
                if p.get("nationality_name_ko") and p["nationality_name_ko"] not in (NAMES[code], "이탈리아계 한국인"):
                    raise SystemExit(f"Existing nationality label conflict for {pid}")
                approved[pid] = (code, source)
    if args.apply and not args.mapping:
        raise SystemExit("--apply requires --mapping")
    if args.apply:
        for pid, (code, source) in approved.items():
            index[pid]["nationality_code"] = code
            index[pid]["nationality_name_ko"] = NAMES[code]
            index[pid]["nationality_source"] = source
            index[pid]["nationality_review_status"] = "verified"
        CATALOG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    missing = [p for p in people if not p.get("nationality_code")]
    count_by_kind = dict(collections.Counter(p.get("kind", "unknown") for p in people))
    report = {
        "total": len(people), "by_kind": count_by_kind,
        "with_code": len(people) - len(missing), "without_code": len(missing),
        "approved_rows": len(approved), "applied": bool(args.apply),
        "note": "Entries with Korean display labels but no ISO nationality code remain unverified.",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.queue.parent.mkdir(parents=True, exist_ok=True)
    with args.queue.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id","kind","nickname","real_name","team","league","region","existing_label","code","source"])
        w.writeheader()
        for p in missing:
            w.writerow({k: p.get({"existing_label":"nationality_name_ko"}.get(k,k),"") for k in w.fieldnames})
    print(json.dumps(report, ensure_ascii=False))
if __name__ == "__main__":
    main()
