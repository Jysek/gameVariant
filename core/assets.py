"""
Caricamento centralizzato degli asset grafici.

Tutti gli sprite (navi, nemici, laser, asteroidi, boss, esplosioni, power-up)
vengono caricati e pre-scalati una sola volta in Assets.load().
Questo evita costose chiamate a transform.scale() ad ogni frame.

La GIF del boss e delle esplosioni viene decomposta in frame individuali
tramite Pillow (PIL).
"""

import os
import pygame
from PIL import Image

from core.constants import (
    ENEMY_SIZE, ASTEROID_SIZE, CARRIER_SIZE,
    POWERUP_ITEM_SIZE, EXPLOSION_SIZE, POWERUP_TYPES,
)

# Dimensioni laser pre-scalati
_LASER_W = 20
_LASER_H = 40

# Dimensioni frame scia asteroide (spritesheet orizzontale)
_TRAIL_FW = 32
_TRAIL_FH = 32
_TRAIL_N  = 12   # numero di frame nella spritesheet


def _base():
    """Restituisce il percorso della directory radice del progetto."""
    return os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))


def _gif_frames(path):
    """Decompone una GIF animata nei suoi frame individuali.

    Usa Pillow per leggere ogni frame della GIF, lo converte in RGBA
    e lo trasforma in una Surface Pygame.

    Args:
        path: Percorso del file GIF.

    Returns:
        Lista di pygame.Surface (un frame per elemento).
    """
    frames = []
    gif = Image.open(path)
    for i in range(gif.n_frames):
        gif.seek(i)
        f = gif.convert("RGBA")
        frames.append(pygame.image.fromstring(f.tobytes(), f.size, "RGBA"))
    return frames


class Assets:
    """Contenitore statico per tutti gli asset grafici del gioco.

    Tutti gli attributi sono attributi di classe: vengono caricati una
    sola volta da load() e condivisi da tutte le entita'.
    """

    _loaded = False

    # Navi del giocatore (3 tipi)
    player_ships = []

    # Laser (sprite pre-scalati per ciascun tipo di nave)
    laser_sprites       = []
    laser_left_angular  = []
    laser_right_angular = []
    enemy_laser_sprite_scaled = None

    # Nemici
    enemy_scout_sprite  = None
    enemy_fighter_sprite = None
    enemy_bomber_sprite = None
    enemy_elite_sprite  = None
    alien_sprite        = None   # fallback per tipi sconosciuti

    # Asteroide e scia
    asteroid_sprite = None
    trail_frames    = []

    # Carrier e power-up
    carrier_sprites = {}
    powerup_sprites = {}

    # Boss e esplosioni (frame da GIF)
    boss_frames          = []
    explosion_frames     = []
    explosion_frames_raw = []

    @classmethod
    def load(cls):
        """Carica tutti gli asset grafici dal disco.

        Deve essere chiamato dopo pygame.display.set_mode() perche'
        convert_alpha() richiede un display attivo.

        Il metodo e' idempotente: chiamate successive non ricaricano nulla.
        """
        if cls._loaded:
            return

        base = _base()
        assets_dir = os.path.join(base, "Assets")
        laser_dir  = os.path.join(base, "LaserSprites")

        def img(name, size=None):
            """Carica e opzionalmente scala un'immagine dalla cartella Assets."""
            s = pygame.image.load(os.path.join(assets_dir, name)).convert_alpha()
            return pygame.transform.scale(s, size) if size else s

        def lz(name):
            """Carica e scala un laser dalla cartella LaserSprites."""
            return pygame.transform.scale(
                pygame.image.load(os.path.join(laser_dir, name)).convert_alpha(),
                (_LASER_W, _LASER_H),
            )

        # ---- Navi del giocatore ----
        cls.player_ships = [
            img("ship.png"),
            img("ship2.png"),
            img("ship3.png"),
        ]

        # ---- Laser ----
        cls.laser_sprites = [lz("11.png"), lz("16.png"), lz("12.png")]
        cls.laser_left_angular = [
            lz("11LeftAngular.png"),
            lz("16LeftAngular.png"),
            lz("12LeftAngular.png"),
        ]
        cls.laser_right_angular = [
            lz("11RightAngular.png"),
            lz("16RightAngular.png"),
            lz("12RightAngular.png"),
        ]
        cls.enemy_laser_sprite_scaled = lz("14.png")

        # ---- Nemici ----
        cls.alien_sprite        = img("alien.png",          (ENEMY_SIZE, ENEMY_SIZE))
        cls.enemy_scout_sprite  = img("enemy_scout.png",    (ENEMY_SIZE, ENEMY_SIZE))
        cls.enemy_fighter_sprite = img("enemy_fighter.png",  (ENEMY_SIZE, ENEMY_SIZE))
        cls.enemy_bomber_sprite = img("enemy_bomber.png",   (ENEMY_SIZE, ENEMY_SIZE))
        cls.enemy_elite_sprite  = img("enemy_elite.png",    (ENEMY_SIZE, ENEMY_SIZE))

        # ---- Asteroide e scia ----
        cls.asteroid_sprite = img(
            "asteroid_1_rotondo.png", (ASTEROID_SIZE, ASTEROID_SIZE))

        sheet = pygame.image.load(
            os.path.join(assets_dir, "asteroid_trail.png")).convert_alpha()
        cls.trail_frames = []
        for i in range(_TRAIL_N):
            f = sheet.subsurface(
                pygame.Rect(i * _TRAIL_FW, 0, _TRAIL_FW, _TRAIL_FH)).copy()
            cls.trail_frames.append(f)

        # ---- Carrier e power-up ----
        for pt in POWERUP_TYPES:
            cls.carrier_sprites[pt] = img(
                f"carrier_{pt}.png", (CARRIER_SIZE, CARRIER_SIZE))
            cls.powerup_sprites[pt] = img(
                f"powerup_{pt}.png", (POWERUP_ITEM_SIZE, POWERUP_ITEM_SIZE))

        # ---- Boss (GIF animata) ----
        cls.boss_frames = _gif_frames(os.path.join(assets_dir, "boss.gif"))

        # ---- Esplosioni (GIF animata) ----
        cls.explosion_frames_raw = _gif_frames(
            os.path.join(assets_dir, "explosionGif.gif"))
        cls.explosion_frames = [
            pygame.transform.scale(f, (EXPLOSION_SIZE, EXPLOSION_SIZE))
            for f in cls.explosion_frames_raw
        ]

        cls._loaded = True
