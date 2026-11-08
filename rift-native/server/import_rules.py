"""League import quotas and earned third-year local residency (game rule).

A foreigner becomes a local-status player in their *third consecutive registered
season in the same league*. This does not alter nationality/citizenship.
Only active first-team five count against game lineup quotas. Staff are excluded.
Unverified nationalities are counted as foreign, never inferred from team/region.
"""
import sqlite3

ROLES = frozenset(("TOP", "JUNGLE", "MID", "ADC", "SUPPORT"))
ASIA = frozenset(("JP", "TW", "HK", "MO", "VN", "TH", "PH", "ID", "MY", "SG",
                  "IN", "PK", "BD", "NP", "KH", "LA", "MM", "MN", "KZ", "UZ",
                  "KG", "TJ", "TM", "LK", "BN", "TL", "BT", "MV", "AF", "IR",
                  "IQ", "SY", "JO", "IL", "PS", "SA", "AE", "QA", "KW", "BH",
                  "OM", "YE", "AZ", "AM", "GE", "TR", "CY"))
EMEA = frozenset(("GB", "FR", "DE", "ES", "PT", "IT", "PL", "TR", "SE", "DK",
                  "NO", "FI", "NL", "BE", "CH", "AT", "CZ", "SK", "HU", "RO",
                  "BG", "GR", "UA", "RU", "RS", "HR", "SI", "BA", "LT", "LV",
                  "EE", "BY", "IE", "IS", "LU", "MT", "CY", "AL", "ME", "MK",
                  "GE", "AM", "AZ", "IL", "EG", "MA", "TN", "DZ", "ZA",
                  "SA", "AE", "QA", "KW", "BH", "OM", "JO", "LB"))
AMERICAS_NORTH = frozenset(("US", "CA", "MX"))
DOMESTIC = {
    "LCK": frozenset(("KR",)), "LCK CL": frozenset(("KR",)),
    "LPL": frozenset(("CN",)), "LDL": frozenset(("CN",)),
    "LCP": ASIA,
    "FLS": ASIA, "WildCard": ASIA,
    "LJL": frozenset(("JP",)),
    "PCS": frozenset(("TW", "HK", "MO")),
    "VCS": frozenset(("VN",)),
    "LCS": AMERICAS_NORTH, "NACL": AMERICAS_NORTH,
    "CBLOL": frozenset(("BR",)), "Circuito Desafiante": frozenset(("BR",)),
    "LEC": EMEA, "LFL": EMEA, "PRM": EMEA, "LES": EMEA, "TCL": EMEA,
}
ALIASES = {"LCKCL": "LCK CL", "LCK CL": "LCK CL"}
QUOTA_ONE = frozenset(("LCK", "LCK CL", "LPL", "LDL"))
# All other leagues default to two, including new leagues not listed above.
DEFAULT_QUOTA = 2


class ForeignQuotaError(ValueError):
    pass


def init(db):
    db.execute("""CREATE TABLE IF NOT EXISTS league_residency (
        person_id TEXT NOT NULL,
        league TEXT NOT NULL,
        first_year INTEGER NOT NULL,
        last_year INTEGER NOT NULL,
        PRIMARY KEY (person_id, league)
    )""")


def code(person):
    value = str(person.get("nationality_code") or "").upper().strip()
    if value:
        return value
    # Explicitly fictional/generated Korean candidates have authored Korean identity.
    if person.get("real_person") is False and person.get("nationality_name_ko") == "대한민국":
        return "KR"
    return ""


def quota(league):
    return 1 if league in QUOTA_ONE else DEFAULT_QUOTA


def origin_countries(league, region=""):
    if league in DOMESTIC:
        return DOMESTIC[league]
    # New leagues may use an explicitly recognized geographic competition region.
    if region == "EMEA":
        return EMEA
    if region == "LCP":
        return ASIA
    return frozenset()  # no invented domestic category for unknown competitions


def register(db, person_id, league, year):
    """Record a season in which a signed player is on the club roster.

    Consecutive seasons count; a gap resets the qualifying first season.
    A year can only be recorded once, and future/old years cannot backfill history.
    """
    if not person_id or not league or type(year) is not int or year < 2020:
        raise ValueError("invalid residency record")
    row = db.execute("SELECT first_year,last_year FROM league_residency WHERE person_id=? AND league=?",
                     (person_id, league)).fetchone()
    if row is None:
        db.execute("INSERT INTO league_residency VALUES(?,?,?,?)",
                   (person_id, league, year, year))
    elif year > row[1]:
        first = row[0] if year == row[1] + 1 else year
        db.execute("UPDATE league_residency SET first_year=?,last_year=? WHERE person_id=? AND league=?",
                   (first, year, person_id, league))


def third_year(db, person_id, league, year):
    row = db.execute("SELECT first_year,last_year FROM league_residency WHERE person_id=? AND league=?",
                     (person_id, league)).fetchone()
    return bool(row and row[1] == year and year - row[0] >= 2)


def status(db, person, league, year, region=""):
    country = code(person)
    if country and country in origin_countries(league, region):
        return "domestic"
    if country and third_year(db, person["id"], league, year):
        return "resident"
    return "foreign" if country else "unknown"


def summary(db, league, year, people, region=""):
    starting = [p for p in people if p.get("assignment") == "first" and
                p.get("kind") == "player" and p.get("role") in ROLES]
    rows = []
    for p in starting:
        state = status(db, p, league, year, region)
        rows.append({"id": p["id"], "nickname": p.get("nickname") or p.get("name"),
                     "nationality_code": code(p) or None, "status": state})
    used = sum(p["status"] in ("foreign", "unknown") for p in rows)
    limit = quota(league)
    return {"league": league, "year": year, "limit": limit, "used": used,
            "remaining": max(0, limit - used), "valid": used <= limit,
            "players": rows,
            "note": "국적 미확인 선수는 외국인으로 계산; 3년차 연속 등록부터 현지 선수 취급"}


def validate(db, league, year, people, region=""):
    value = summary(db, league, year, people, region)
    if not value["valid"]:
        raise ForeignQuotaError(
            f"{league} 용병 제한 초과: {value['used']}명 / 최대 {value['limit']}명 "
            f"(국적 미확인도 용병으로 계산)")
    return value


def for_career(db, career, people=None, *, record=True):
    import clubs
    import recruitment
    profile = clubs.profile(db, career)
    year = 2025 + db.execute("SELECT season FROM careers WHERE id=?", (career,)).fetchone()[0]
    if people is None:
        people = recruitment.view(db, career)["people"]
    # Count roster/academy seasons, not coach/staff history. Do not assume prior
    # seasons for imported real players, because source data has no proof of it.
    if record:
        for p in people:
            if p.get("kind") == "player" and p.get("assignment") in ("first", "reserve", "academy"):
                register(db, p["id"], profile["league"], year)
    return validate(db, profile["league"], year, people)
