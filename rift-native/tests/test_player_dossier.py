"""FM player report regressions: 28 in-game skill traits, real recorded match facts."""
import json
import sqlite3
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'server'))
import player_analysis
import player_attributes
import scouting


class PlayerDossierTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        player_attributes.init(self.db)
        self.db.executescript("""CREATE TABLE careers(id INTEGER PRIMARY KEY,season INTEGER NOT NULL);
            INSERT INTO careers VALUES(1,3);
            CREATE TABLE fixtures(id INTEGER PRIMARY KEY,career_id INTEGER,
                season INTEGER,week INTEGER,opponent TEXT,state TEXT,result TEXT);""")
        self.player={'id':'player-a','nickname':'Kiro','kind':'player','role':'MID',
                     'real_person':True,'stats':None,'game_evaluation':None}
        self.other={'id':'player-b','nickname':'Vexo','kind':'player','role':'MID',
                    'real_person':True,'stats':None,'game_evaluation':None}

    def tearDown(self):
        self.db.close()

    def test_real_world_people_without_source_stats_receive_labeled_simulation_only(self):
        a=player_analysis.attribute_profile(self.player)
        again=player_analysis.attribute_profile(self.player)
        b=player_analysis.attribute_profile(self.other)
        self.assertEqual(a,again)
        self.assertEqual('simulation-estimate',a['source'])
        self.assertIn('검증된 능력치가 아닙니다',a['note'])
        self.assertEqual(28,a['count'])
        self.assertEqual(4,len(a['sections']))
        self.assertEqual(28,len({entry['name'] for section in a['sections']
                                 for entry in section['attributes']}))
        self.assertTrue(all(1<=v['value']<=20 for section in a['sections']
                            for v in section['attributes']))
        self.assertNotEqual(a['sections'],b['sections'])
        self.assertEqual('미드',a['role']['primary_label'])
        self.assertEqual([],a['role']['secondary'])

    def test_explicit_base_scores_are_derived_not_discarded(self):
        self.player['game_evaluation']={'ratings':{
            '라인전':90,'교전':84,'운영':70,'시야':40,'협동':71,'멘탈':64}}
        result=player_analysis.attribute_profile(self.player)
        self.assertEqual('game-rating',result['source'])
        self.assertEqual(90,result['core']['라인전'])
        self.assertEqual(28,result['count'])

    def test_match_stats_only_from_completed_fixtures(self):
        missing=player_analysis.season_performance(self.db,1,self.player)
        self.assertFalse(missing['available'])
        self.assertEqual([],missing['recent'])
        match={'winner':0,'sets':[{'winner':0,'players':[{
            'player_id':'player-a','player_name':'Kiro','role':'MID','name':'Ahri',
            'team':0,'kda':[3,1,5],'cs':201,'gold':11700,'damage':23000}],'draft':[]}]}
        self.db.execute("""INSERT INTO fixtures(id,career_id,season,week,opponent,state,result)
            VALUES(1,1,3,8,'Gen.G','finished',?)""",(json.dumps(match),))
        self.db.execute("""INSERT INTO fixtures(id,career_id,season,week,opponent,state,result)
            VALUES(2,1,3,9,'T1','scheduled',?)""",(json.dumps(match),))
        result=player_analysis.season_performance(self.db,1,self.player)
        self.assertTrue(result['available'])
        self.assertEqual('played-game-results',result['source'])
        self.assertEqual(1,result['games'])
        self.assertEqual(1,result['wins'])
        self.assertEqual(0,result['losses'])
        self.assertEqual(8.0,result['kda'])
        self.assertEqual(201.0,result['avg_cs'])
        self.assertEqual(23000,result['avg_damage'])
        self.assertEqual(1,len(result['recent']))
        self.assertEqual('Ahri',result['recent'][0]['champion'])
        self.assertFalse(player_analysis.season_performance(
            self.db,1,self.other)['available'])

    def test_compare_uses_same_visible_30_skills(self):
        with patch('catalog.load',return_value={'people':[self.player,self.other]}):
            compared=scouting.compare(self.db,1,self.player)
        self.assertEqual(1,len(compared))
        self.assertEqual('game-estimated',compared[0]['source'])
        self.assertEqual(20,compared[0]['scale'])
        self.assertEqual(30,len(compared[0]['differences']))
        report=player_analysis.report(self.db,1,self.player)
        self.assertEqual(30,report['attributes']['count'])
        self.assertEqual(5,len(report['attributes']['sections']))
        # Editor overrides must update comparisons as well as the player page.
        new={name:20 for name in player_attributes.KEYS}
        player_attributes.save(self.db,self.other,new,9)
        with patch('catalog.load',return_value={'people':[self.player,self.other]}):
            changed=scouting.compare(self.db,1,self.player)
        self.assertEqual('operator-edited',changed[0]['source'])
        self.assertEqual(30,len(changed[0]['differences']))

    def test_player_html_does_not_show_avatar_dot_or_raw_squad_enum(self):
        js=(ROOT/'web'/'app.js').read_text(encoding='utf-8')
        css=(ROOT/'web'/'app.css').read_text(encoding='utf-8')
        face=js[js.index('function face('):js.index('function logoImg(')]
        self.assertNotIn('>●<',face)
        self.assertIn('portrait-person-svg',face)
        self.assertIn('.face-placeholder[hidden]',css)
        self.assertIn('display:none!important',css)
        player=js[js.index('async function player(id, tab) {'):
                  js.index('function seasonStanding(',js.index('async function player(id, tab) {'))]
        self.assertIn('rosterStatus(person)',player)
        self.assertNotIn('esc(person.assignment||',player)
        self.assertIn('playerAttributePanel(analysis)',player)
        self.assertIn('playerSeasonPanel(performance)',player)


if __name__=='__main__':
    unittest.main()
