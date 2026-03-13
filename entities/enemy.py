"""
Enemy — sprite e pattern laser per tipo.

Tipi e pattern:
- scout:   laser singolo veloce, intervallo breve
- fighter: laser doppio (±offset), intermedio
- bomber:  laser lento ma grande, lungo intervallo
- elite:   burst da 3 laser ravvicinati, intervallo medio
"""
import random
import pygame
from core.constants import ENEMY_SIZE, RED, ORANGE, YELLOW, CYAN
from core.assets import Assets
from entities.formations import Slot

_FLASH_DUR=5

# Colore laser per tipo
_LASER_COLOR={
    "scout":  RED,
    "fighter":ORANGE,
    "bomber": (180,0,220,255) if False else (180,0,220),  # viola
    "elite":  CYAN,
    "default":RED,
}
# Velocità laser per tipo
_LASER_SPEED={"scout":6,"fighter":5,"bomber":3,"elite":5,"default":5}
# Intervallo sparo (min,max) frames
_SHOOT_INTERVAL={"scout":(70,160),"fighter":(100,200),"bomber":(160,320),"elite":(80,180),"default":(100,200)}

class Enemy:
    def __init__(self,x,y,enemy_type="scout",hp=1):
        self.width=ENEMY_SIZE; self.height=ENEMY_SIZE
        self.x=x; self.y=y; self.alive=True
        self.enemy_type=enemy_type; self.hp=hp; self.max_hp=hp
        self.h_speed=0.0
        lo,hi=_SHOOT_INTERVAL.get(enemy_type,(100,200))
        self.shoot_timer=random.randint(0,hi)
        self.shoot_interval=random.randint(lo,hi)
        self.slot:Slot=Slot(0,0)
        self._flash=0
        self._flash_surf=None

    def take_damage(self,amount=1)->bool:
        self.hp-=amount; self._flash=_FLASH_DUR
        if self.hp<=0: self.hp=0; self.alive=False; return True
        return False

    def _sprite(self)->pygame.Surface:
        m={"scout":Assets.enemy_scout_sprite,
           "fighter":Assets.enemy_fighter_sprite,
           "bomber":Assets.enemy_bomber_sprite,
           "elite":Assets.enemy_elite_sprite}
        s=m.get(self.enemy_type)
        return s if s is not None else Assets.alien_sprite

    def build_lasers(self)->list:
        """Costruisce i laser secondo il pattern del tipo."""
        from entities.laser import Laser
        cx=self.x+self.width//2; by=self.y+self.height
        spd=_LASER_SPEED.get(self.enemy_type,5)
        col=_LASER_COLOR.get(self.enemy_type,RED)
        lasers=[]
        t=self.enemy_type
        if t=="scout":
            lasers.append(Laser(cx-2,by,spd,col,is_enemy=True))
        elif t=="fighter":
            lasers.append(Laser(cx-10,by,spd,col,is_enemy=True))
            lasers.append(Laser(cx+8, by,spd,col,is_enemy=True))
        elif t=="bomber":
            # laser largo e lento
            l=Laser(cx-3,by,spd,col,is_enemy=True)
            l.width=8; lasers.append(l)
        elif t=="elite":
            # burst 3 laser in rapida successione (simulato con offset y)
            for dy in [0,6,12]:
                lasers.append(Laser(cx-2,by+dy,spd,col,is_enemy=True))
        else:
            lasers.append(Laser(cx-2,by,spd,col,is_enemy=True))
        return lasers

    def draw(self,surf):
        if not self.alive: return
        sprite=self._sprite()
        surf.blit(sprite,(int(self.x),int(self.y)))
        # flash bianco all'hit — NO box, solo aumento alpha temporaneo
        if self._flash>0:
            self._flash-=1
            ratio=self._flash/_FLASH_DUR
            sz=(self.width,self.height)
            if self._flash_surf is None or self._flash_surf.get_size()!=sz:
                self._flash_surf=pygame.Surface(sz,pygame.SRCALPHA)
            self._flash_surf.fill((255,255,255,int(60*ratio)))
            surf.blit(self._flash_surf,(int(self.x),int(self.y)),
                      special_flags=pygame.BLEND_RGBA_ADD)

    def get_rect(self)->pygame.Rect:
        return pygame.Rect(self.x+4,self.y+4,self.width-8,self.height-8)
