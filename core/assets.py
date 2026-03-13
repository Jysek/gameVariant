import os
import pygame
from PIL import Image
from core.constants import (
    ENEMY_SIZE, ASTEROID_SIZE, CARRIER_SIZE,
    POWERUP_ITEM_SIZE, EXPLOSION_SIZE, POWERUP_TYPES,
)

_LASER_W = 20
_LASER_H = 40
_TRAIL_FW = 32
_TRAIL_FH = 32
_TRAIL_N  = 12

def _base():
    return os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))

def _gif_frames(path):
    frames=[]
    gif=Image.open(path)
    for i in range(gif.n_frames):
        gif.seek(i)
        f=gif.convert("RGBA")
        frames.append(pygame.image.fromstring(f.tobytes(),f.size,"RGBA"))
    return frames

class Assets:
    _loaded=False
    player_ships=[]
    laser_sprites=[]; laser_left_angular=[]; laser_right_angular=[]
    enemy_laser_sprite_scaled=None
    enemy_scout_sprite=None; enemy_fighter_sprite=None
    enemy_bomber_sprite=None; enemy_elite_sprite=None
    alien_sprite=None
    asteroid_sprite=None
    trail_frames=[]
    carrier_sprites={}; powerup_sprites={}
    boss_frames=[]; explosion_frames=[]; explosion_frames_raw=[]

    @classmethod
    def load(cls):
        if cls._loaded: return
        base=_base()
        A=os.path.join(base,"Assets")
        L=os.path.join(base,"LaserSprites")

        def img(name, size=None):
            s=pygame.image.load(os.path.join(A,name)).convert_alpha()
            return pygame.transform.scale(s,size) if size else s

        def lz(name):
            return pygame.transform.scale(
                pygame.image.load(os.path.join(L,name)).convert_alpha(),
                (_LASER_W,_LASER_H))

        cls.player_ships=[img("ship.png"),img("ship2.png"),img("ship3.png")]
        cls.laser_sprites=[lz("11.png"),lz("16.png"),lz("12.png")]
        cls.laser_left_angular=[lz("11LeftAngular.png"),lz("16LeftAngular.png"),lz("12LeftAngular.png")]
        cls.laser_right_angular=[lz("11RightAngular.png"),lz("16RightAngular.png"),lz("12RightAngular.png")]
        cls.enemy_laser_sprite_scaled=lz("14.png")

        cls.alien_sprite=img("alien.png",(ENEMY_SIZE,ENEMY_SIZE))
        cls.enemy_scout_sprite  =img("enemy_scout.png",  (ENEMY_SIZE,ENEMY_SIZE))
        cls.enemy_fighter_sprite=img("enemy_fighter.png",(ENEMY_SIZE,ENEMY_SIZE))
        cls.enemy_bomber_sprite =img("enemy_bomber.png", (ENEMY_SIZE,ENEMY_SIZE))
        cls.enemy_elite_sprite  =img("enemy_elite.png",  (ENEMY_SIZE,ENEMY_SIZE))

        cls.asteroid_sprite=img("asteroid_1_rotondo.png",(ASTEROID_SIZE,ASTEROID_SIZE))

        sheet=pygame.image.load(os.path.join(A,"asteroid_trail.png")).convert_alpha()
        cls.trail_frames=[]
        for i in range(_TRAIL_N):
            f=sheet.subsurface(pygame.Rect(i*_TRAIL_FW,0,_TRAIL_FW,_TRAIL_FH)).copy()
            cls.trail_frames.append(f)

        for pt in POWERUP_TYPES:
            cls.carrier_sprites[pt]=img(f"carrier_{pt}.png",(CARRIER_SIZE,CARRIER_SIZE))
            cls.powerup_sprites[pt]=img(f"powerup_{pt}.png",(POWERUP_ITEM_SIZE,POWERUP_ITEM_SIZE))

        cls.boss_frames=_gif_frames(os.path.join(A,"boss.gif"))
        cls.explosion_frames_raw=_gif_frames(os.path.join(A,"explosionGif.gif"))
        cls.explosion_frames=[pygame.transform.scale(f,(EXPLOSION_SIZE,EXPLOSION_SIZE))
                               for f in cls.explosion_frames_raw]
        cls._loaded=True
