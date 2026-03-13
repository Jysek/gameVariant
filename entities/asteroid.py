"""
Asteroid — scia pixel art sprite-based.
Particelle usano BLEND_ADD per effetto fuoco luminoso.
Frame avanzano da 0 (bianco caldo) verso N-1 (brace morta).
"""
import random, math
import pygame
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ASTEROID_SIZE
from core.assets import Assets

_active_x: list = []
_MIN_GAP = 90

def _safe_x(w):
    for _ in range(30):
        x = random.randint(20, SCREEN_WIDTH-w-20)
        if all(abs(x-ox)>=_MIN_GAP for ox in _active_x):
            return float(x)
    cols=6; cw=(SCREEN_WIDTH-40)//cols
    counts=[0]*cols
    for ox in _active_x:
        c=int((ox-20)/cw)
        if 0<=c<cols: counts[c]+=1
    best=counts.index(min(counts))
    return float(20+best*cw+random.randint(0,max(0,cw-w)))

def clear_registry():
    _active_x.clear()

_N_FRAMES=12
_FW=32

class _Particle:
    __slots__=('x','y','vx','vy','frame','alpha','sz','alive')
    def __init__(self,cx,cy):
        self.x  =cx+random.uniform(-10,10)
        self.y  =cy+random.uniform(-6,6)
        self.vx =random.uniform(-0.3,0.3)
        self.vy =random.uniform(-1.0,-0.15)   # risale — fumo caldo
        self.frame=float(random.randint(0,2))  # parte da frame giovane
        self.alpha=random.randint(200,255)
        self.sz =random.uniform(0.5,1.2)
        self.alive=True
    def update(self):
        self.x+=self.vx; self.y+=self.vy
        self.frame+=0.4
        self.alpha-=16
        self.sz=max(0,self.sz-0.02)
        if self.alpha<=0 or self.sz<0.05 or self.frame>=_N_FRAMES:
            self.alive=False
    def draw(self,surf,frames):
        fi=min(int(self.frame),_N_FRAMES-1)
        src=frames[fi]
        sz=max(2,int(_FW*self.sz))
        scaled=pygame.transform.scale(src,(sz,sz))
        scaled.set_alpha(max(0,min(255,int(self.alpha))))
        surf.blit(scaled,(int(self.x-sz//2),int(self.y-sz//2)),
                  special_flags=pygame.BLEND_ADD)

class Asteroid:
    MIN_SPEED=1.8; MAX_SPEED=3.2

    def __init__(self):
        self.width=ASTEROID_SIZE; self.height=ASTEROID_SIZE
        self.x=_safe_x(self.width); self.y=float(-self.height-random.randint(0,40))
        self.active=True
        _active_x.append(self.x)
        self.fall_speed=random.uniform(self.MIN_SPEED,self.MAX_SPEED)
        self.angle=0.0
        self.rot_speed=random.choice([-3,-2,-1,1,2,3])
        self.trail:list[_Particle]=[]

    def update(self):
        if not self.active: return
        self.y+=self.fall_speed
        self.angle=(self.angle+self.rot_speed)%360
        cx=self.x+self.width//2; cy=self.y+self.height//2
        for _ in range(random.randint(4,6)):
            self.trail.append(_Particle(cx,cy))
        for p in self.trail: p.update()
        self.trail=[p for p in self.trail if p.alive]
        if self.y>SCREEN_HEIGHT+60:
            self.active=False; self._dereg()

    def _dereg(self):
        try: _active_x.remove(self.x)
        except ValueError: pass

    def deactivate(self):
        if self.active: self.active=False; self._dereg()

    def draw(self,surf):
        if not self.active: return
        if Assets.trail_frames:
            for p in self.trail: p.draw(surf,Assets.trail_frames)
        rot=pygame.transform.rotate(Assets.asteroid_sprite,self.angle)
        r=rot.get_rect(center=(int(self.x+self.width//2),int(self.y+self.height//2)))
        surf.blit(rot,r)

    def get_rect(self):
        return pygame.Rect(self.x+10,self.y+10,self.width-20,self.height-20)
