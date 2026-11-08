"""Collision and routing derive from the same PNG that the spectator sees."""
from PIL import Image
from pathlib import Path
import sys,heapq,math
ROOT=Path(getattr(sys,'_MEIPASS',Path(__file__).parent))
def distance(a,b):return math.hypot(a[0]-b[0],a[1]-b[1])
class Terrain:
    cellsize=4
    def __init__(self,path=None):
        image=Image.open(path or ROOT/'assets/map.png').convert('RGBA');self.image=image
        self.mask=image.getchannel('A');self.walk=set();self.cache={};self.sightcache={}
        # Body clearance prevents centers sitting on the very edge of transparent walls.
        for x in range(128):
            for y in range(128):
                px,py=x*4+2,y*4+2
                if all(0<=px+dx<512 and 0<=py+dy<512 and self.mask.getpixel((px+dx,py+dy))>220 for dx,dy in ((0,0),(2,0),(-2,0),(0,2),(0,-2))):self.walk.add((x,y))
        # Keep only the main connected component; decorative isolated islands are not paths.
        groups=[];unseen=set(self.walk)
        while unseen:
            start=min(unseen);group={start};stack=[start];unseen.remove(start)
            while stack:
                x,y=stack.pop()
                for n in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
                    if n in unseen:unseen.remove(n);group.add(n);stack.append(n)
            groups.append(group)
        self.walk=max(groups,key=len)
    def cell(self,p):return (int(p[0]//4),int(p[1]//4))
    def center(self,c):return(c[0]*4+2.,c[1]*4+2.)
    def legal(self,p):return self.cell(p) in self.walk
    def snap(self,p):
        if self.legal(p):return tuple(p)
        return self.center(min(self.walk,key=lambda c:(distance(self.center(c),p),c)))
    def clear(self,a,b):
        steps=max(1,math.ceil(distance(a,b)/1.5))
        return all(self.legal((a[0]+(b[0]-a[0])*i/steps,a[1]+(b[1]-a[1])*i/steps)) for i in range(steps+1))
    def sight(self,a,b):
        ca,cb=self.cell(a),self.cell(b);key=tuple(sorted((ca,cb)))
        if key not in self.sightcache:
            self.sightcache[key]=self.clear(self.center(ca),self.center(cb))
        return self.sightcache[key]
    def route(self,a,b):
        a,b=self.cell(a),self.cell(self.snap(b))
        if a not in self.walk:return []
        if (a,b) in self.cache:return self.cache[(a,b)]
        queue=[(0,a)];cost={a:0};parent={}
        while queue:
            _,p=heapq.heappop(queue)
            if p==b:
                path=[]
                while p!=a:path.append(self.center(p));p=parent[p]
                path.reverse()
                if len(self.cache)>20000:self.cache.clear()
                self.cache[(a,b)]=path;return path
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)):
                n=(p[0]+dx,p[1]+dy);new=cost[p]+math.hypot(dx,dy)
                if n not in self.walk or (dx and dy and ((p[0]+dx,p[1]) not in self.walk or (p[0],p[1]+dy) not in self.walk)):continue
                if new<cost.get(n,1e9):
                    cost[n]=new;parent[n]=p;heapq.heappush(queue,(new+distance(n,b),n))
        return []
    def move(self,u,goal,dt):
        if not self.legal(u.pos):u.pos=self.snap(u.pos);u.path=[]
        goal=self.snap(goal);key=self.cell(goal)
        if u.pathgoal!=key or not u.path:
            # Replanning from a fractional point must first reach its own cell
            # center. Otherwise a legal diagonal edge can cut a corner from the
            # off-center position and repeatedly fail swept collision.
            u.path=[self.center(self.cell(u.pos))]+list(self.route(u.pos,goal));u.pathgoal=key
        if len(u.path)<=2 and self.clear(u.pos,goal):
            u.path=[goal]
        budget=u.speed*dt
        while u.path and budget>0:
            p=u.path[0];d=distance(u.pos,p)
            if not self.clear(u.pos,p):u.path=[];break
            if d<=budget:u.pos=p;u.path.pop(0);budget-=d
            else:u.pos=(u.pos[0]+(p[0]-u.pos[0])*budget/d,u.pos[1]+(p[1]-u.pos[1])*budget/d);break
