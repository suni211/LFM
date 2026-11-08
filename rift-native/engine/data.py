from dataclasses import dataclass

# Data Dragon 16.21.1 attackrange values, projected onto the 512px map.
def map_range(units):
    return units * 512 / 14850

TOWER_RANGE = map_range(750)
FOUNTAIN_RANGE = map_range(1050)

SUMMONERS = {
    'Flash': ('점멸', 300), 'Teleport': ('순간이동', 360),
    'Dot': ('점화', 180), 'Exhaust': ('탈진', 240), 'Heal': ('회복', 240),
    'Haste': ('유체화', 240), 'Barrier': ('방어막', 180), 'Boost': ('정화', 240),
    'Smite': ('강타', 75),
}
# Role presets sampled from OP.GG 16.20–16.22. Keyed by champion.
KEYSTONES = {
    'Jax': 'tempo', 'Nunu': 'stormraider', 'Annie': 'electrocute',
    'Ashe': 'tempo', 'Alistar': 'aftershock', 'Sion': 'grasp',
    'Warwick': 'tempo', 'Ryze': 'deathfire', 'Sivir': 'tempo', 'Soraka': 'aery',
    'Fiddlesticks': 'electrocute', 'Kayle': 'pta', 'MasterYi': 'hail',
    'Morgana': 'comet', 'Teemo': 'pta', 'Tristana': 'tempo', 'TwistedFate': 'comet',
}
RUNE_NAMES = {
    'tempo': '치명적 속도', 'stormraider': '폭풍전사의 포효', 'electrocute': '감전',
    'aftershock': '여진', 'grasp': '착취의 손아귀', 'deathfire': '죽음불꽃 손길',
    'aery': '콩콩이 소환', 'pta': '집중 공격', 'hail': '칼날비', 'comet': '신비로운 유성',
}

@dataclass(frozen=True)
class Kit:
    ko:str; roles:tuple; style:str; hp:int; attack:int; reach:float; spells:tuple; build:tuple
# spell = (name, family, power, range in map pixels, cooldown, cc duration)
def q(n,k,p,r,c,cc=0):return(n,k,p,r * .2,c,cc)
KITS={
'Alistar':Kit('알리스타',('SUPPORT','TOP'),'tank',820,60,125,(q('분쇄','aoe',100,40,13,1),q('박치기','dash',90,65,14,.6),q('짓밟기','aoe',60,35,10),q('꺾을 수 없는 의지','guard',.65,0,90)),(3117,3190,3107,3083)),
'Annie':Kit('애니',('MID','SUPPORT'),'ap',620,50,625,(q('붕괴','target',100,90,4),q('소각','aoe',100,65,8),q('용암 방패','shield',150,90,12),q('티버','pet',220,95,100)),(3020,6655,3089,3157)),
'Ashe':Kit('애쉬',('ADC',),'ad',640,62,600,(q('궁사의 집중','haste',.6,0,14),q('일제 사격','line',100,130,9,.5),q('매 날리기','vision',0,250,40),q('마법의 수정화살','line',220,400,100,2)),(3006,3153,3031,3035)),
'Fiddlesticks':Kit('피들스틱',('JUNGLE','SUPPORT'),'ap',690,52,480,(q('공포','target',80,80,14,1.3),q('풍작','drain',160,60,9),q('수확','line',100,110,9,.7),q('까마귀 폭풍','storm',300,100,100)),(3020,3152,3157,3089)),
'Jax':Kit('잭스',('TOP','JUNGLE'),'fighter',780,68,125,(q('도약 공격','dash',100,100,9),q('무기 강화','target',90,24,5),q('반격','counter',120,38,13,1),q('무기의 달인','guard',.35,0,80)),(3047,3078,3153,3053)),
'Kayle':Kit('케일',('TOP','MID'),'ap',650,58,175,(q('광휘의 일격','line',100,110,10,.7),q('천상의 축복','heal',120,95,14),q('화염주문검','target',100,90,7),q('신성한 심판','immune',2.5,95,120)),(3006,3115,3089,3157)),
'MasterYi':Kit('마스터 이',('JUNGLE',),'ad',740,68,175,(q('일격 필살','blink',130,90,14),q('명상','meditate',180,0,25),q('우주류 검술','truebuff',55,0,14),q('최후의 전사','haste',1,0,85)),(3006,3153,3031,3053)),
'Morgana':Kit('모르가나',('MID','SUPPORT','JUNGLE'),'ap',700,52,450,(q('어둠의 속박','line',110,140,10,1.7),q('고통의 그림자','zone',170,100,11),q('칠흑의 방패','shield',180,95,18),q('영혼의 족쇄','tether',250,65,100,1.5)),(3020,3116,3157,3089)),
'Nunu':Kit('누누',('JUNGLE',),'tank',800,60,125,(q('잡아먹기','consume',160,25,8),q('눈덩이','dash',110,100,14,1),q('눈덩이 팡팡팡','line',100,85,10,.7),q('절대 영도','channel',350,65,100,1)),(3111,3118,3083,3075)),
'Ryze':Kit('라이즈',('MID','TOP'),'ap',680,55,550,(q('과부하','line',100,115,5),q('룬 감옥','target',85,90,12,1),q('주문 전이','target',80,90,4),q('공간 왜곡','portal',0,180,100)),(3020,6655,3089,3157)),
'Sion':Kit('사이온',('TOP',),'tank',900,65,175,(q('대량 학살 강타','channel',180,55,10,1.2),q('영혼의 용광로','shield',200,0,14),q('학살자의 포효','line',90,110,10,.6),q('멈출 수 없는 맹공','dash',230,180,100,1.5)),(3047,3118,3083,3075)),
'Sivir':Kit('시비르',('ADC',),'ad',650,63,500,(q('부메랑 검','pierce',130,130,9),q('튕기는 부메랑','ricochet',.5,0,10),q('주문 방어막','spellshield',1,0,20),q('사냥 개시','teamhaste',.5,0,90)),(3006,3031,3033,3035)),
'Soraka':Kit('소라카',('SUPPORT',),'support',630,48,550,(q('별부름','zone',100,100,7,.4),q('은하의 마력','heal',160,95,5),q('별의 균형','zone',100,100,17,1),q('기원','globalheal',200,1000,120)),(3117,4005,3504,3107)),
'Teemo':Kit('티모',('TOP',),'ap',640,58,500,(q('실명 다트','blind',100,100,9,1.5),q('신속한 이동','haste',.5,0,16),q('맹독 다트','poisonbuff',50,0,12),q('유독성 함정','trap',180,100,25,.6)),(3020,3115,3116,3089)),
'Tristana':Kit('트리스타나',('ADC','MID'),'ad',670,65,550,(q('속사','haste',.8,0,16),q('로켓 점프','blink',110,110,18,.5),q('폭발 화약','bomb',160,100,14),q('대구경 탄환','knockback',220,100,90)),(3006,3031,3033,3035)),
'TwistedFate':Kit('트위스티드 페이트',('MID',),'ap',640,53,525,(q('와일드 카드','pierce',110,130,6),q('골드 카드','target',90,90,9,1.5),q('속임수 덱','target',90,90,8),q('운명','gate',0,250,110)),(3020,6655,3089,3157)),
'Warwick':Kit('워윅',('JUNGLE','TOP'),'fighter',780,66,125,(q('야수의 송곳니','drain',120,25,6),q('피의 사냥','haste',.65,0,20),q('원시의 포효','guard',.4,0,15),q('무한의 구속','dash',230,130,100,1.8)),(3047,3153,3078,3053))}
ITEMS={1001:('장화',300,'speed',1.3),3006:('광전사의 군화',1100,'as',.25),3020:('마법사의 신발',1100,'pen',12),3047:('판금 장화',1100,'armor',25),3111:('헤르메스의 발걸음',1100,'mr',25),3117:('기동력의 장화',1000,'speed',3),
3153:('몰락한 왕의 검',3000,'ad',35),3078:('삼위일체',3300,'ad',40),3053:('스테락의 도전',3000,'hp',400),3118:('케이닉 루컨',2900,'hp',400),3083:('워모그의 갑옷',3100,'hp',650),3075:('가시 갑옷',2700,'armor',65),
6655:('루덴의 동반자',2900,'ap',90),3152:('마법공학 로켓 벨트',2650,'ap',70),3089:('라바돈의 죽음모자',3600,'ap',120),3157:('존야의 모래시계',3250,'ap',90),3116:('라일라이의 수정홀',2600,'ap',65),3115:('내셔의 이빨',3000,'ap',80),
3031:('무한의 대검',3400,'ad',70),3033:('필멸자의 운명',3100,'ad',35),3035:('최후의 속삭임',1450,'ad',20),3190:('강철의 솔라리 펜던트',2200,'armor',30),3107:('구원',2300,'hp',250),4005:('제국의 명령',2250,'ap',60),3504:('불타는 향로',2300,'ap',50)}
from champion_catalog import extend
extend(KITS,Kit,KEYSTONES)
from item_catalog import ITEM_DETAILS,build_for,register
register(KITS,ITEMS)
ROLES=('TOP','JUNGLE','MID','ADC','SUPPORT')
ROSTER=(('Jax','Nunu','Annie','Ashe','Alistar'),('Sion','Warwick','Ryze','Sivir','Soraka'))
def project(x,z):return (x/14850*512,(1-z/14850)*512)
SPAWNS=(project(410,422),project(14298,14384))
NEXUS=(project(1136,1370),project(13202,13165))
TOWERS=({'TOP':[(981,10441),(1512,6699),(1169,4287)],'MID':[(5846,6396),(5048,4812),(3651,3696)],'BOT':[(10504,1029),(6919,1483),(4281,1253)]},
        {'TOP':[(4318,13875),(7943,13411),(10481,13650)],'MID':[(8955,8510),(9767,10113),(11134,11207)],'BOT':[(13866,4505),(13324,8226),(13624,10572)]})
INHIB=({'TOP':(1171,3571),'MID':(3203,3208),'BOT':(3452,1236)},{'TOP':(11261,13676),'MID':(11598,11667),'BOT':(13604,11316)})
BASE_TOWERS=([(1748,2270),(2177,1807)],[(13052,12612),(12611,13084)])
CAMP=({'Blue':(3821,7901),'Gromp':(2111,8451),'Wolves':(3781,6444),'Raptors':(6707,5521),'Red':(7765,4020),'Krugs':(8482,2706)},
      {'Blue':(11032,6991),'Gromp':(12704,6444),'Wolves':(11008,8387),'Raptors':(7987,9471),'Red':(7102,10901),'Krugs':(6317,12146)})
PITS={'Dragon':project(9866,4414),'Baron':project(5007,10471),'Grub':project(4930,10371)}
