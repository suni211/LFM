"""AI transfer history must be a real roster move, never a rumor-only story."""
import json
import sqlite3
import unittest
from unittest.mock import patch

import catalog
import clubs
import transfers
import world_transfers
import rumors


def person(uid,team,role):
    return dict(id=uid,kind="player",real_person=True,nickname=uid,
                real_name=uid,team=team,league="LCK",region="KR",role=role)


def fixture():
    roles=("TOP","JUNGLE","MID","ADC","SUPPORT")
    people=[person("A"+str(i),"Alpha",role) for i,role in enumerate(roles)]
    people.append(person("extra-top","Alpha","TOP"))
    people.extend(person("B"+str(i),"Beta",role) for i,role in enumerate(roles))
    return people


class WorldTransferTest(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.execute("CREATE TABLE careers(id INTEGER PRIMARY KEY, name TEXT)")
        clubs.init(self.db)
        transfers.init(self.db)
        world_transfers.init(self.db)
        rumors.init(self.db)
        self.patcher=patch.object(catalog,"load",return_value={"people":fixture()})
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.db.close()

    def make_deal(self):
        for season in range(1,10):
            for week in range(1,11):
                if world_transfers.weekly(self.db,season,week):
                    return season,week
        self.fail("No AI transfer was generated in deterministic test interval")

    def test_ai_signing_updates_roster_and_appears_in_official_feed(self):
        season,week=self.make_deal()
        deals=world_transfers.official(self.db)
        self.assertEqual(len(deals),1)
        deal=deals[0]
        self.assertEqual(deal["from_team"],"Alpha")
        self.assertEqual(deal["to_team"],"Beta")
        self.assertEqual(deal["league"],"LCK")
        self.assertGreater(deal["fee"],0)
        self.assertEqual(deal["status"],"official")
        # Either of the two TOPs can move; at least one TOP remains at Alpha.
        self.assertIn(deal["person_id"],("A0","extra-top"))
        changes=catalog.game_clubs(self.db)
        moved=next(p for p in fixture() if p["id"]==deal["person_id"])
        self.assertEqual(catalog.apply_game_club(moved,changes)["team"],"Beta")
        self.assertEqual(world_transfers.weekly(self.db,season,week),0)
        self.assertEqual(len(world_transfers.official(self.db)),1)
        merged=transfers.activity(self.db,league="LCK")
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]["origin"],"ai")
        self.assertEqual(merged[0]["player_name"],"extra-top")
        self.assertEqual(transfers.activity(self.db,league="LPL"),[])

    def test_managed_source_cannot_be_modified(self):
        self.db.execute("INSERT INTO careers VALUES(1,'Alpha')")
        self.db.execute("INSERT INTO club_profiles VALUES(?,?,?,?,?)",
                        (1,"takeover","LCK",clubs.key("LCK","Alpha"),"source"))
        for season in range(1,6):
            for week in range(1,11):
                world_transfers.weekly(self.db,season,week)
        self.assertEqual(world_transfers.official(self.db),[])

    def test_rumors_do_not_create_official_signings(self):
        self.db.execute("""INSERT INTO league_rumors
            (league,event_key,season,week,headline,body,subjects)
            VALUES(?,?,?,?,?,?,?)""",
            ("LCK","ai:1:1:test",1,1,"접촉설","미확정",
             json.dumps([{"kind":"team","entity":"Alpha"}])))
        feed=rumors.feed(self.db,"LCK")
        self.assertEqual(len(feed),1)
        self.assertEqual(feed[0]["status"],"rumor")
        self.assertFalse(feed[0]["confirmed"])
        self.assertEqual(world_transfers.official(self.db),[])
        self.assertEqual(transfers.activity(self.db),[])


if __name__=="__main__":
    unittest.main()
