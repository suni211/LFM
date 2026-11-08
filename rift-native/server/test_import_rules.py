"""Small fast tests for import quotas and 3rd-year game residency."""
import sqlite3
import unittest
import import_rules as rules


def player(uid, code, role="TOP", assignment="first", **extra):
    return {"id": uid, "kind": "player", "role": role,
            "assignment": assignment, "nationality_code": code,
            "nickname": uid, "real_person": True, **extra}


class ImportRulesTest(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        rules.init(self.db)

    def tearDown(self):
        self.db.close()

    def test_lck_lpl_one_foreigner(self):
        for league, local in (("LCK", "KR"), ("LPL", "CN"),
                              ("LCK CL", "KR"), ("LDL", "CN")):
            roster=[player("one",local,"TOP"),player("two",local,"JUNGLE"),
                    player("three",local,"MID"),player("foreign","US","ADC"),
                    player("local",local,"SUPPORT")]
            self.assertTrue(rules.validate(self.db,league,2026,roster)["valid"])
            roster[-1]["nationality_code"]="JP"
            with self.assertRaises(rules.ForeignQuotaError):
                rules.validate(self.db,league,2026,roster)

    def test_lcp_asia_excluding_china_korea(self):
        roster=[player("jp","JP","TOP"),player("vn","VN","JUNGLE"),
                player("tw","TW","MID"),player("kr","KR","ADC"),
                player("cn","CN","SUPPORT")]
        status=rules.validate(self.db,"LCP",2026,roster)
        self.assertEqual(status["used"],2)
        roster[2]["nationality_code"]="US"
        with self.assertRaises(rules.ForeignQuotaError):
            rules.validate(self.db,"LCP",2026,roster)

    def test_other_leagues_two_foreigners(self):
        roster=[player("br","BR","TOP"),player("br2","BR","JUNGLE"),
                player("us","US","MID"),player("kr","KR","ADC"),
                player("br3","BR","SUPPORT")]
        self.assertEqual(rules.validate(self.db,"CBLOL",2026,roster)["used"],2)
        roster[-1]["nationality_code"]="JP"
        with self.assertRaises(rules.ForeignQuotaError):
            rules.validate(self.db,"CBLOL",2026,roster)

    def test_3rd_consecutive_year_is_domestic_for_quota_only(self):
        p=player("resident","KR")
        for year in (2026,2027):
            rules.register(self.db,p["id"],"LPL",year)
            self.assertEqual(rules.status(self.db,p,"LPL",year),"foreign")
        rules.register(self.db,p["id"],"LPL",2028)
        self.assertEqual(rules.status(self.db,p,"LPL",2028),"resident")
        self.assertEqual(p["nationality_code"],"KR")

    def test_return_after_gap_resets(self):
        p=player("return","CN")
        rules.register(self.db,"return","LCK",2026)
        rules.register(self.db,"return","LCK",2027)
        rules.register(self.db,"return","LCK",2029)
        self.assertEqual(rules.status(self.db,p,"LCK",2029),"foreign")

    def test_residency_is_league_specific(self):
        p=player("changed","CN")
        for year in (2026,2027,2028):
            rules.register(self.db,"changed","LCK",year)
        self.assertEqual(rules.status(self.db,p,"LCK",2028),"resident")
        rules.register(self.db,"changed","LCS",2028)
        self.assertEqual(rules.status(self.db,p,"LCS",2028),"foreign")

    def test_unknown_country_never_becomes_domestic_without_residency(self):
        roster=[player(str(i),"",r) for i,r in enumerate(("TOP","JUNGLE","MID","ADC","SUPPORT"))]
        self.assertEqual(rules.summary(self.db,"LCK",2026,roster)["used"],5)
        with self.assertRaises(rules.ForeignQuotaError):
            rules.validate(self.db,"LCK",2026,roster)

    def test_staff_and_bench_do_not_take_lineup_slots(self):
        roster=[player("foreign1","KR","TOP"),player("foreign2","CN","JUNGLE"),
                player("bench","US","ADC","reserve"),
                {"id":"coach","kind":"coach","role":"COACH","assignment":"staff","nationality_code":"KR"}]
        self.assertEqual(rules.summary(self.db,"LPL",2026,roster)["used"],1)

    def test_generated_korean_person_with_label(self):
        p={"id":"gen-1","kind":"player","role":"MID","assignment":"first",
           "real_person":False,"nationality_name_ko":"대한민국"}
        self.assertEqual(rules.status(self.db,p,"LCK",2026),"domestic")

    def test_duplicate_year_does_not_accelerate_residency(self):
        p=player("repeat","CN")
        for _ in range(5):
            rules.register(self.db,p["id"],"LCK",2026)
        self.assertEqual(rules.status(self.db,p,"LCK",2026),"foreign")


if __name__=="__main__":
    unittest.main()
