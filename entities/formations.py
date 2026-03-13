"""
Formazioni nemici — v3.
Ogni formazione occupa una fascia orizzontale DEDICATA per livello di riga,
così gruppi diversi non si sovrappongono MAI sullo schermo.
"""
import random
from typing import NamedTuple
from core.constants import SCREEN_WIDTH, ENEMY_SIZE

class Slot(NamedTuple):
    col: int
    row: int

CELL_W = ENEMY_SIZE + 18   # 68 px
CELL_H = ENEMY_SIZE + 14   # 64 px

FORMATIONS = {
    "GRID_3x3":[Slot(c,r) for r in range(3) for c in range(3)],
    "GRID_4x2":[Slot(c,r) for r in range(2) for c in range(4)],
    "H_LINE"  :[Slot(c,0) for c in range(5)],
    "V_SHAPE" :[Slot(1,0),Slot(2,0),
                Slot(0,1),Slot(1,1),Slot(2,1),Slot(3,1),
                Slot(0,2),Slot(1,2),Slot(2,2),Slot(3,2)],
    "DIAMOND" :[Slot(1,0),
                Slot(0,1),Slot(1,1),Slot(2,1),
                Slot(0,2),Slot(1,2),Slot(2,2),
                Slot(1,3)],
    "PINCER"  :[Slot(0,0),Slot(3,0),
                Slot(0,1),Slot(3,1),
                Slot(0,2),Slot(3,2)],
    "ARROW"   :[Slot(0,1),
                Slot(1,0),Slot(1,1),Slot(1,2),
                Slot(2,0),          Slot(2,2)],
    "Z_LINE"  :[Slot(0,0),Slot(1,0),Slot(2,0),
                            Slot(1,1),Slot(2,1),Slot(3,1),
                                      Slot(2,2),Slot(3,2),Slot(4,2)],
}

_POOLS=[
    ["GRID_4x2","H_LINE","GRID_3x3"],
    ["GRID_4x2","H_LINE","GRID_3x3","V_SHAPE"],
    ["GRID_3x3","V_SHAPE","DIAMOND","Z_LINE"],
    ["V_SHAPE","DIAMOND","Z_LINE","PINCER","ARROW","GRID_3x3"],
]

def pick_formation(difficulty_level:int)->tuple[str,list[Slot]]:
    pool=_POOLS[min(difficulty_level,len(_POOLS)-1)]
    name=random.choice(pool)
    return name,list(FORMATIONS[name])

def build_spawn_positions(slots:list[Slot])->list[dict]:
    if not slots: return []
    max_col=max(s.col for s in slots)
    max_row=max(s.row for s in slots)
    fw=(max_col+1)*CELL_W
    fh=(max_row+1)*CELL_H
    # Centra orizzontalmente con un offset casuale per varietà visiva
    margin=max(0,(SCREEN_WIDTH-fw)//2)
    ox=random.randint(max(10,margin-60),min(SCREEN_WIDTH-fw-10,margin+60))
    oy=-fh-30
    return [{"x":float(ox+s.col*CELL_W),"y":float(oy+s.row*CELL_H),"slot":s}
            for s in slots]
