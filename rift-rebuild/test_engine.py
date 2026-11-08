import unittest,math,json
from engine import Match,DT
from terrain import Terrain,distance
from data import KITS,ITEMS
from replay import clips

class TerrainTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.terrain=Terrain()
    def test_no_transparent_pixel_in_walk_grid(self):
        t=self.terrain
        for cell in t.walk:
            p=t.center(cell)
            self.assertGreater(t.mask.getpixel(tuple(map(int,p))),220)
    def test_routes_never_cross_walls(self):
        t=self.terrain;points=[t.snap(p) for p in ((20,490),(490,20),(64,170),(350,350),(180,100))]
        for a in points:
            for b in points:
                path=t.route(a,b);previous=t.center(t.cell(a))
                for p in path:self.assertTrue(t.clear(previous,p),(previous,p));previous=p
                self.assertTrue(path or t.cell(a)==t.cell(b))
    def test_outside_goals_are_clamped(self):
        t=self.terrain
        for p in ((-100,0),(900,900),(256,-100)):
            self.assertTrue(t.legal(t.snap(p)))

class EngineTests(unittest.TestCase):
    def setUp(self):self.m=Match(13);self.a=self.m.players()[0];self.b=self.m.players()[5]
    def open_positions(self):
        t=self.m.terrain
        for c in sorted(t.walk):
            p=t.center(c)
            if all(t.legal((p[0]+dx,p[1])) for dx in range(0,90,2)):return p,(p[0]+80,p[1])
        self.fail('No open lane')
    def test_attack_requires_range(self):
        a,b=self.a,self.b;a.pos,b.pos=self.open_positions();hp=b.hp
        self.assertFalse(self.m.attack(a,b));self.assertEqual(hp,b.hp)
        b.pos=(a.pos[0]+3,a.pos[1]);self.assertTrue(self.m.attack(a,b));self.assertLess(b.hp,hp)
    def test_attack_requires_line_of_sight(self):
        t=self.m.terrain;a,b=self.a,self.b;a.reach=2000
        points=list(sorted(t.walk))[::97]
        pair=next(( (t.center(x),t.center(y)) for x in points for y in points if not t.clear(t.center(x),t.center(y))),None)
        self.assertIsNotNone(pair);a.pos,b.pos=pair
        self.assertFalse(self.m.attack(a,b))
    def test_monster_has_short_reach(self):
        m=self.m;monster=next(u for u in m.units if u.kind=='camp');monster.hp=monster.maxhp
        monster.pos,self.a.pos=self.open_positions();monster.nextattack=0
        self.assertLessEqual(monster.reach,16);self.assertFalse(m.attack(monster,self.a))
    def test_no_wall_crossing_during_walk(self):
        m=self.m;u=self.a;goal=m.players()[5].home
        for _ in range(700):
            old=u.pos;m.move(u,goal)
            self.assertTrue(m.terrain.legal(u.pos));self.assertTrue(m.terrain.clear(old,u.pos));self.assertLessEqual(distance(old,u.pos),u.speed*DT+.001)
    def test_replan_from_fractional_position_reaches_target(self):
        m=self.m;u=self.a;t=m.terrain
        u.pos=t.snap((78.4,315.8));goal=t.snap((300,180));start=distance(u.pos,goal)
        for _ in range(1200):m.move(u,goal)
        self.assertLess(distance(u.pos,goal),6)
        self.assertGreater(start,100)
    def test_recover_fully_before_leaving(self):
        m=self.m;u=self.a;u.hp=10;u.mana=0;old=u.pos
        for _ in range(5):m.step();self.assertEqual(old,u.pos)
        for _ in range(100):
            m.step()
            if distance(old,u.pos)>1:
                self.assertEqual(u.hp,u.maxhp);self.assertEqual(u.mana,u.maxmana);break
        else:self.fail('Never left fountain')
    def test_champion_specific_builds(self):
        m=self.m;u=m.players()[1];self.assertEqual(u.name,'Nunu');u.gold=20000;m.buy(u)
        self.assertEqual(u.items,list(KITS['Nunu'].build));self.assertNotIn(3153,u.items);self.assertNotIn(3031,u.items)
        for u in m.players():
            u.gold=20000;m.buy(u);self.assertEqual(u.items,list(KITS[u.name].build))
    def test_pack_respawn_after_last_monster(self):
        m=self.m;m.t=100;cfg=next(c for c in m.camps if m.units[c['id']].name=='Wolves')
        for uid in cfg['members']:m.units[uid].hp=m.units[uid].maxhp
        m.damage(self.a,m.units[cfg['id']],1e6,true=True)
        self.assertEqual(m.units[cfg['id']].dead_until,0)
        for uid in cfg['members'][1:]:m.damage(self.a,m.units[uid],1e6,true=True)
        self.assertTrue(all(m.units[i].dead_until==250 for i in cfg['members']))
    def test_grub_plan_persists_for_remaining_two(self):
        m=self.m;m.t=400;ci=next(i for i,c in enumerate(m.camps) if m.units[c['id']].name=='Grub');cfg=m.camps[ci]
        for uid in cfg['members']:m.units[uid].hp=m.units[uid].maxhp
        for u in m.players(0):u.pos=m.units[cfg['id']].home
        m.plans[0]=dict(kind='오브젝트',camp=ci,p=m.units[cfg['id']].home,since=390)
        m.damage(self.a,m.units[cfg['id']],1e6,true=True)
        plan=m.macro(0);self.assertEqual(plan['camp'],ci);self.assertEqual(plan['kind'],'오브젝트')
    def test_grub_split_credits_actual_killer(self):
        m=self.m;m.t=400;cfg=next(c for c in m.camps if m.units[c['id']].name=='Grub')
        for i,uid in enumerate(cfg['members']):
            u=m.units[uid];u.hp=u.maxhp;m.damage(self.a if i<2 else self.b,u,1e6,true=True)
        self.assertEqual(m.grubs,[2,1])
    def test_structure_sequence(self):
        m=self.m;towers=sorted((u for u in m.units if u.team==1 and u.kind=='tower' and u.lane=='TOP'),key=lambda u:u.depth)
        self.assertTrue(m.open_structure(towers[0]));self.assertFalse(m.open_structure(towers[1]));towers[0].hp=0;self.assertTrue(m.open_structure(towers[1]))
    def test_combat_visuals_identify_attacker_and_victim(self):
        a,b=self.a,self.b;a.pos,b.pos=self.open_positions();b.pos=(a.pos[0]+3,a.pos[1]);self.m.attack(a,b)
        self.assertTrue(any(e['kind']=='melee' and e['a']==a.id and e['b']==b.id for e in self.m.visuals))
        self.assertTrue(any(e['kind']=='impact' and e['value']>0 for e in self.m.visuals))
    def test_every_champion_spell_family_executes(self):
        for name,kit in KITS.items():
            for slot in range(4):
                with self.subTest(champion=name,slot=slot):
                    m=Match();a=m.players()[0];b=m.players()[5]
                    a.name=name;a.level=6;a.hp=100;a.pos=m.terrain.snap((256,256));b.pos=m.terrain.snap((a.pos[0]+3,a.pos[1]));a.cool=[99999]*4;a.cool[slot]=0
                    friend=m.players()[1];friend.pos=a.pos;friend.hp=10
                    if name=='Soraka' and slot==1:a.hp=a.maxhp*.7
                    m.reindex()
                    self.assertTrue(m.cast(a,b,slot));self.assertLess(a.mana,a.maxmana)
                    for _ in range(20):m.t+=.2;m.effects();m.resolve()

class HighlightTests(unittest.TestCase):
    def test_no_escape_or_arbitrary_fight_clips(self):
        events=[dict(type='flash',t=50,p=(20,20)),dict(type='fight',t=60,ids=[0,1],p=(20,20))]
        self.assertEqual(clips(events,100),[])
    def test_kill_pre_roll(self):
        c=clips([dict(type='kill',t=50,p=(20,20),killer=0,victim=1,assists=[])],100)
        self.assertEqual(c[0]['start'],40);self.assertEqual(c[0]['label'],'솔로 킬')
    def test_continuous_fight_to_nexus(self):
        es=[dict(type='kill',t=100,p=(30,30),killer=0,victim=1,assists=[2]),dict(type='victory',t=150,p=(40,40),unit=5)]
        c=clips(es,150);self.assertEqual(len(c),1);self.assertEqual(c[0]['start'],90);self.assertEqual(c[0]['end'],150)
    def test_nexus_thirty_seconds_pre_roll(self):
        c=clips([dict(type='victory',t=200,p=(30,30),unit=5)],200);self.assertEqual(c[0]['start'],170)

if __name__=='__main__':unittest.main()
