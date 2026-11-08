"""Fan-post diversity and repeatable event-based social reactions."""
import sqlite3
import unittest

import fan_community
import fan_variety


class FanVarietyTest(unittest.TestCase):
    def test_more_than_one_thousand_distinct_styles_in_each_sentiment(self):
        self.assertGreater(fan_variety.STYLES_PER_SENTIMENT,1000)
        self.assertGreaterEqual(fan_variety.TOTAL_STYLES,4000)
        for sentiment in (-1,0,1):
            variants={
                fan_variety.voice(i,sentiment,'Recorded game event','The result is official.')
                for i in range(fan_variety.STYLES_PER_SENTIMENT)
            }
            self.assertEqual(len(variants),fan_variety.STYLES_PER_SENTIMENT)

    def test_game_event_spawns_praise_criticism_meme_without_fabrication(self):
        db=sqlite3.connect(':memory:')
        fan_community.init(db)
        try:
            event='Match event: Falcons defeated Lions 2-1.'
            post=fan_community.publish(
                db,'LCK','match:test:1','team','Falcons 2:1 Lions',
                event,1,11,[{'kind':'team','entity':'Falcons'}],sentiment=1)
            self.assertGreater(post,0)
            rows=db.execute("SELECT category,title,body FROM fan_posts WHERE league='LCK' ORDER BY id").fetchall()
            self.assertEqual(len(rows),5)
            self.assertIn('praise',{r[0] for r in rows})
            self.assertIn('rant',{r[0] for r in rows})
            self.assertTrue(all(event in row[2] for row in rows))
            self.assertGreater(db.execute('SELECT COUNT(*) FROM fan_comments').fetchone()[0],10)
            # Idempotent when backend retries posting a result.
            repeated=fan_community.publish(
                db,'LCK','match:test:1','team','Falcons 2:1 Lions',
                event,1,11,[],sentiment=1)
            self.assertEqual(post,repeated)
            self.assertEqual(db.execute('SELECT COUNT(*) FROM fan_posts').fetchone()[0],5)
        finally:
            db.close()


if __name__=='__main__':
    unittest.main()
