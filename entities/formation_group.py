"""
FormationGroup v3 — movimento, sparo, anti-overlap assoluto.

Anti-overlap inter-gruppo:
- Ogni gruppo registra la propria "fascia Y di ingresso" in un registro globale.
- Un nuovo gruppo non spawna se c'è già un gruppo nella stessa fascia Y
  (cioè se il gruppo precedente non è ancora sceso abbastanza).
- Questa logica è gestita da game.py tramite can_spawn().
"""
import random
import pygame
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from entities.enemy import Enemy
from entities.formations import Slot

DROP_AMOUNT   = 24
DROP_INTERVAL = 70

_TYPE_MAP={"GRID_3x3":"scout","GRID_4x2":"scout","H_LINE":"scout",
           "V_SHAPE":"fighter","Z_LINE":"fighter",
           "DIAMOND":"elite","PINCER":"bomber","ARROW":"bomber"}
_SCORE={"scout":1,"fighter":2,"bomber":3,"elite":5}
_HP   ={"scout":1,"fighter":2,"bomber":3,"elite":2}

def _type(name,lv):
    base=_TYPE_MAP.get(name,"scout")
    if lv==0 and base in("bomber","elite"): return "scout"
    if lv<=1 and base=="elite": return "fighter"
    return base

class FormationGroup:
    def __init__(self,spawn_data,speed_mult=1.0,formation_name="",difficulty=0):
        self.formation_name=formation_name
        et=_type(formation_name,difficulty)
        hp=_HP.get(et,1)
        self.score_per_kill=_SCORE.get(et,1)
        self.enemies=[Enemy(d["x"],d["y"],enemy_type=et,hp=hp) for d in spawn_data]
        for e,d in zip(self.enemies,spawn_data):
            e.slot=d["slot"]
        base=random.choice([-1.0,-0.7,0.7,1.0])*speed_mult
        self.dx=base
        self._drop_timer=0
        self.pending_lasers=[]

    @property
    def alive_enemies(self): return[e for e in self.enemies if e.alive]
    @property
    def is_empty(self): return all(not e.alive for e in self.enemies)
    @property
    def left_edge(self):
        a=self.alive_enemies; return min(e.x for e in a)if a else 0.0
    @property
    def right_edge(self):
        a=self.alive_enemies; return max(e.x+e.width for e in a)if a else 0.0
    @property
    def bottom_edge(self):
        a=self.alive_enemies; return max(e.y+e.height for e in a)if a else 0.0
    @property
    def top_edge(self):
        a=self.alive_enemies; return min(e.y for e in a)if a else 0.0

    def update(self)->bool:
        self.pending_lasers.clear()
        if self.is_empty: return False
        # bordi
        if self.dx<0 and self.left_edge+self.dx<10: self.dx=abs(self.dx)
        elif self.dx>0 and self.right_edge+self.dx>SCREEN_WIDTH-10: self.dx=-abs(self.dx)
        for e in self.alive_enemies: e.x+=self.dx
        # discesa
        self._drop_timer+=1
        if self._drop_timer>=DROP_INTERVAL:
            self._drop_timer=0
            for e in self.alive_enemies: e.y+=DROP_AMOUNT
        # sparo con pattern per tipo
        for e in self.alive_enemies:
            e.shoot_timer+=1
            if e.shoot_timer>=e.shoot_interval:
                e.shoot_timer=0
                lo,hi={"scout":(70,160),"fighter":(100,200),
                        "bomber":(160,320),"elite":(80,180)}.get(e.enemy_type,(100,200))
                e.shoot_interval=random.randint(lo,hi)
                self.pending_lasers.extend(e.build_lasers())
        return self.bottom_edge>=SCREEN_HEIGHT

    def draw(self,surf):
        for e in self.alive_enemies: e.draw(surf)

    def get_alive_rects(self):
        return[(e.get_rect(),e) for e in self.alive_enemies]
