"""Real HTTP smoke test using a temporary DB and loopback-only server.

Validates registration -> manager nationality -> five offers -> club founding
-> training -> club roster -> user logo -> immutable name -> sponsorship.
Never touches user's GCP server or production database.
"""
import base64
import json
import os
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
SERVER=ROOT/'server'/'server.py'

class HttpCareerSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(prefix='rift-smoke-')
        cls.db=Path(cls.temp.name)/'game.db'
        cls.log=open(Path(cls.temp.name)/'server.log','w+',encoding='utf-8')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0))
            cls.port=sock.getsockname()[1]
        cls.url='http://127.0.0.1:'+str(cls.port)
        env=os.environ.copy()
        env.update({'RIFT_DB':str(cls.db),'RIFT_PORT':str(cls.port),
                    'PYTHONUNBUFFERED':'1'})
        cls.proc=subprocess.Popen([sys.executable,str(SERVER)],cwd=str(SERVER.parent),
                                  env=env,stdout=cls.log,stderr=subprocess.STDOUT)
        deadline=time.monotonic()+45
        while time.monotonic()<deadline:
            if cls.proc.poll() is not None:
                cls.log.flush();cls.log.seek(0)
                raise RuntimeError('RIFT API crashed on startup:\n'+cls.log.read()[-7000:])
            try:
                with urlopen(cls.url+'/health',timeout=1) as response:
                    if response.status==200:break
            except (URLError,OSError):
                time.sleep(.2)
        else:
            cls.proc.terminate()
            cls.log.flush();cls.log.seek(0)
            raise RuntimeError('RIFT API startup timed out:\n'+cls.log.read()[-7000:])

    @classmethod
    def tearDownClass(cls):
        if getattr(cls,'proc',None):
            cls.proc.terminate()
            try:cls.proc.wait(timeout=3)
            except subprocess.TimeoutExpired:cls.proc.kill();cls.proc.wait(timeout=3)
        if getattr(cls,'log',None):cls.log.close()
        if getattr(cls,'temp',None):cls.temp.cleanup()

    def call(self,path,body=None,token=None):
        data=json.dumps(body,ensure_ascii=False).encode('utf-8') if body is not None else None
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Bearer '+token
        req=Request(self.url+path,data=data,headers=headers,
                    method='POST' if data is not None else 'GET')
        try:
            with urlopen(req,timeout=30) as response:
                return response.status,json.load(response)
        except HTTPError as error:
            return error.code,json.loads(error.read().decode('utf-8'))

    def test_full_career_journey(self):
        status,data=self.call('/register',{'name':'smoke-qa','password':'abCD!12345678'})
        self.assertEqual(200,status,data)
        token=data['token']
        skills={name:10 for name in ('전술','훈련','협상','동기부여','선수관리','스카우팅')}
        status,data=self.call('/manager-profile',dict(
            name='Smoke Coach',nickname='SmokeManager',nationality_code='KR',
            stats=skills),token)
        self.assertEqual(200,status,data)
        self.assertEqual('대한민국',data['nationality_name_ko'])
        status,data=self.call('/rookie-offers',token=token)
        self.assertEqual(200,status,data)
        self.assertEqual(5,len(data['offers']))
        image='data:image/png;base64,'+base64.b64encode(
            bytes.fromhex('89504e470d0a1a0a')+b'test-small').decode()
        status,data=self.call('/careers',dict(mode='create',
            name='Smoke Phoenix',short='SMP',league='LCK CL',
            color='#254a7a',emblem='shield',logo_data=image),token)
        self.assertEqual(201,status,data)
        career=data['id']
        status,data=self.call('/careers',token=token)
        self.assertEqual(200,status,data)
        self.assertEqual('Smoke Phoenix',data['careers'][0]['name'])
        status,data=self.call('/club-identity?league=LCK%20CL&team=Smoke%20Phoenix',token=token)
        self.assertEqual(200,status,data)
        self.assertEqual('Smoke Phoenix',data['display_name'])
        status,data=self.call('/club-dossier?league=LCK%20CL&team=Smoke%20Phoenix',token=token)
        if status!=200:
            self.log.flush()
            with open(self.log.name,encoding='utf-8') as stream:
                raise AssertionError('Dossier '+str(status)+': '+str(data)+'\nServer trace:\n'+stream.read()[-7000:])
        # A real imported player without numerical source stats still has a
        # fully labeled game-only FM report; completed game stats stay separate.
        status,profile=self.call('/person?id='+str(career)+
            '&person=ddd8c7fdc2c4dbb5e87d',token=token)
        self.assertEqual(200,status,profile)
        self.assertEqual('FenRir',profile['person']['nickname'])
        traits=profile['player_analysis']['attributes']
        self.assertEqual(30,traits['count'])
        self.assertEqual('game-estimated',traits['source'])
        self.assertFalse(profile['player_analysis']['season']['available'])
        status,data=self.call('/league-overview?league=LCK%20CL',token=token)
        self.assertEqual(200,status,data)
        status,data=self.call('/training?id='+str(career),token=token)
        if status!=200:
            self.log.flush()
            with open(self.log.name,encoding='utf-8') as stream:
                raise AssertionError('Training '+str(status)+': '+str(data)+'\nServer trace:\n'+stream.read()[-7000:])
        self.assertIn('players',data)
        # Real HTTP permission and persistence check: a normal manager can
        # view all 30 stats but cannot edit any person's profile.
        status,players=self.call('/people?id='+str(career)+'&kind=player&page=0',token=token)
        self.assertEqual(200,status,players)
        person_id=players['people'][0]['id']
        status,profile=self.call('/person?id='+str(career)+'&person='+person_id,token=token)
        self.assertEqual(200,status,profile)
        self.assertFalse(profile['can_edit_attributes'])
        self.assertEqual(30,len(profile['attributes']['ratings']))
        self.assertEqual(30,profile['player_analysis']['attributes']['count'])
        new_attributes={key:14 for key in profile['attributes']['ratings']}
        new_attributes['라인전']=18
        status,data=self.call('/operator/person-attributes',
            dict(person=person_id,ratings=new_attributes),token)
        self.assertEqual(403,status,data)
        status,admin=self.call('/register',
            dict(name='smoke-operator',password='ValidPassword!983'))
        self.assertEqual(200,status,admin)
        admin_token=admin['token']
        with sqlite3.connect(self.db) as db:
            admin_id=db.execute("SELECT id FROM users WHERE name='smoke-operator'").fetchone()[0]
            db.execute("INSERT INTO league_operators(user_id) VALUES(?)",(admin_id,))
        status,data=self.call('/person?id=0&person='+person_id,token=admin_token)
        self.assertEqual(200,status,data)
        self.assertTrue(data['can_edit_attributes'])
        status,bad=self.call('/operator/person-attributes',
            dict(person=person_id,ratings={'라인전':18}),admin_token)
        self.assertEqual(400,status,bad)
        status,updated=self.call('/operator/person-attributes',
            dict(person=person_id,ratings=new_attributes),admin_token)
        self.assertEqual(200,status,updated)
        self.assertEqual('operator-edited',updated['attributes']['source'])
        status,reloaded=self.call('/person?id='+str(career)+'&person='+person_id,token=token)
        self.assertEqual(200,status,reloaded)
        self.assertEqual(new_attributes,reloaded['attributes']['ratings'])
        self.assertEqual(18,reloaded['player_analysis']['attributes']['sections'][0]['attributes'][0]['value'])
        self.assertEqual(90,reloaded['person']['game_evaluation']['ratings']['라인전'])
        status,data=self.call('/club-logo',dict(id=career,logo_data=image),token)
        self.assertEqual(403,status,data)
        status,data=self.call('/club-brandings',token=token)
        self.assertEqual(200,status,data)
        self.assertEqual(image,data['brandings']['LCK CL\nSmoke Phoenix']['logo_data'])
        self.assertEqual('LCK\nT1',data['academy_parents']['LCK CL\nT1 Esports Academy'])
        status,data=self.call('/solo-ladder?id='+str(career)+'&region=KR',token=token)
        self.assertEqual(200,status,data)
        self.assertEqual(500,len(data['rows']))
        self.assertEqual('KR',data['region'])
        self.assertTrue(all(row.get('region')=='KR' for row in data['rows']))
        status,data=self.call('/solo-ladder?id='+str(career)+'&region=NA',token=token)
        self.assertEqual(200,status,data)
        self.assertEqual(500,len(data['rows']))
        # Existing prospects and pros may never fall below Master.
        with sqlite3.connect(self.db) as db:
            below=db.execute("""SELECT COUNT(*) FROM solo_ranks
                WHERE path IN ('pro','prospect') AND mmr<2800""").fetchone()[0]
            self.assertEqual(0,below)
            pool=db.execute("""SELECT r.person_id,r.nickname,p.payload
                FROM solo_ranks r JOIN solo_people p ON p.person_id=r.person_id""").fetchall()
            names=[]
            for pid,nick,raw in pool:
                person=json.loads(raw)
                if person.get('origin')=='solo-queue-only':
                    self.assertTrue(nick.isascii() and nick.isalpha() and 4<=len(nick)<=8,nick)
                    self.assertEqual(nick,person['nickname'])
                    names.append(nick.casefold())
            self.assertEqual(4160,len(names))
            self.assertEqual(len(names),len(set(names)))
        status,data=self.call('/solo-ladder?id='+str(career)+'&region=KR&scope=mine',token=token)
        self.assertEqual(200,status,data)
        self.assertTrue(all(row.get('career_id')==career or row.get('club')=='Smoke Phoenix' for row in data['rows']))
        status,data=self.call('/sponsor-offers?id='+str(career),token=token)
        self.assertEqual(200,status,data)
        secondary=[o for o in data['offers'] if o['tier']=='support' and o['status']=='offered']
        self.assertGreaterEqual(len(secondary),2)
        for o in secondary[:2]:
            status,accepted=self.call('/sponsor-accept',dict(id=career,offer=o['id']),token)
            self.assertEqual(200,status,accepted)
            self.assertEqual('support',accepted['tier'])
        status,logos=self.call('/media/league-logos.json',token=token)
        self.assertEqual(200,status,logos)
        self.assertIn('LCK',logos)
        self.assertIn('LEC',logos)
        status,data=self.call('/operator/club-identity',dict(
            league='LCK CL',team='Smoke Phoenix',name='Unauthorized Name'),token)
        self.assertEqual(403,status,data)
        status,data=self.call('/careers',token=token)
        self.assertEqual('Smoke Phoenix',data['careers'][0]['name'])
        # Use a seeded fictional offer; no real company received contact.
        with sqlite3.connect(self.db) as db:
            db.execute("""INSERT INTO sponsor_offers
                (career_id,season,company,region,amount)
                VALUES(?,1,'삼성전자','KR',50000000)""",(career,))
            offer=db.execute("SELECT id FROM sponsor_offers WHERE career_id=? AND company='삼성전자' AND tier='main'",(career,)).fetchone()[0]
            initial=db.execute('SELECT cash FROM club_finances WHERE career_id=?',(career,)).fetchone()[0]
        status,data=self.call('/sponsor-accept',dict(id=career,offer=offer),token)
        self.assertEqual(200,status,data)
        self.assertEqual('fictional-game-contract',data['source'])
        with sqlite3.connect(self.db) as db:
            after=db.execute('SELECT cash FROM club_finances WHERE career_id=?',(career,)).fetchone()[0]
        self.assertEqual(50000000,after-initial)
        status,data=self.call('/club-identity?league=LCK%20CL&team=Smoke%20Phoenix',token=token)
        self.assertEqual(200,status,data)
        self.assertIn('sponsor-change',{x['event'] for x in data['history']})
        self.assertIn('club-founded',{x['event'] for x in data['history']})

if __name__=='__main__':
    unittest.main()
