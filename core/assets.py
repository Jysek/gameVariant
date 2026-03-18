"""
Caricamento centralizzato degli asset grafici.

Tutti gli sprite (navi, nemici, laser, asteroidi, boss, esplosioni, power-up)
vengono caricati e pre-scalati una sola volta in ``Assets.load()``.
Questo evita costose chiamate a ``transform.scale()`` ad ogni frame.

La GIF del boss e delle esplosioni viene decomposta in frame individuali
tramite Pillow (PIL).
"""

import os
import pygame
from PIL import Image

from core.constants import (
    ENEMY_W, ENEMY_H, ASTEROID_SIZE, CARRIER_SIZE,
    POWERUP_ITEM_SIZE, EXPLOSION_SIZE, POWERUP_TYPES,
)

# ---------------------------------------------------------------------------
# Dimensioni laser pre-scalati
# ---------------------------------------------------------------------------
_LASER_W = 20
_LASER_H = 40

# ---------------------------------------------------------------------------
# Parametri spritesheet scia asteroide (strip orizzontale 12 frame)
# ---------------------------------------------------------------------------
_TRAIL_FW = 32
_TRAIL_FH = 32
_TRAIL_N  = 12


def _base() -> str:
    """Restituisce il percorso della directory radice del progetto."""
    return os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))


def _gif_frames(path: str) -> list[pygame.Surface]:
    """Decompone una GIF animata nei suoi frame individuali.

    Usa Pillow per leggere ogni frame della GIF, lo converte in RGBA
    e lo trasforma in una Surface Pygame.

    Args:
        path: Percorso assoluto del file GIF.

    Returns:
        Lista di ``pygame.Surface`` (un frame per elemento).
    """
    frames: list[pygame.Surface] = []
    gif = Image.open(path)
    for i in range(gif.n_frames):
        gif.seek(i)
        rgba = gif.convert("RGBA")
        frames.append(pygame.image.fromstring(rgba.tobytes(), rgba.size, "RGBA"))
    return frames


class Assets:
    """Contenitore statico per tutti gli asset grafici del gioco.

    Tutti gli attributi sono attributi di *classe*: vengono caricati una
    sola volta da ``load()`` e condivisi da tutte le entita'.
    """

    _loaded: bool = False

    # -- Navi del giocatore (3 tipi) ---
    player_ships: list[pygame.Surface] = []

    # -- Laser (sprite pre-scalati per ciascun tipo di nave) --
    laser_sprites:       list[pygame.Surface] = []
    laser_left_angular:  list[pygame.Surface] = []
    laser_right_angular: list[pygame.Surface] = []
    enemy_laser_sprite_scaled: pygame.Surface | None = None

    # -- Nemici --
    alien_sprite:         pygame.Surface | None = None  # sprite base (alien.png)
    enemy_scout_sprite:   pygame.Surface | None = None
    enemy_fighter_sprite: pygame.Surface | None = None
    enemy_bomber_sprite:  pygame.Surface | None = None
    enemy_elite_sprite:   pygame.Surface | None = None

    # -- Asteroide e scia --
    asteroid_sprite: pygame.Surface | None = None
    trail_frames:    list[pygame.Surface] = []

    # -- Carrier e power-up --
    carrier_sprites: dict[str, pygame.Surface] = {}
    powerup_sprites: dict[str, pygame.Surface] = {}

    # -- Boss e esplosioni (frame da GIF) --
    boss_frames:          list[pygame.Surface] = []
    explosion_frames:     list[pygame.Surface] = []
    explosion_frames_raw: list[pygame.Surface] = []

    @classmethod
    def load(cls) -> None:
        """Carica tutti gli asset grafici dal disco.

        Deve essere chiamato **dopo** ``pygame.display.set_mode()`` perche'
        ``convert_alpha()`` richiede un display attivo.

        Il metodo e' idempotente: chiamate successive non ricaricano nulla.
        """
        if cls._loaded:
            return

        base = _base()
        assets_dir = os.path.join(base, "Assets")
        laser_dir  = os.path.join(base, "LaserSprites")

        # -- Helper interni ----------------------------------------------------

        def img(name: str, size: tuple[int, int] | None = None) -> pygame.Surface:
            """Carica e opzionalmente scala un'immagine dalla cartella Assets."""
            surf = pygame.image.load(os.path.join(assets_dir, name)).convert_alpha()
            return pygame.transform.scale(surf, size) if size else surf

        def lz(name: str) -> pygame.Surface:
            """Carica e scala un laser dalla cartella LaserSprites."""
            return pygame.transform.scale(
                pygame.image.load(os.path.join(laser_dir, name)).convert_alpha(),
                (_LASER_W, _LASER_H),
            )

        # -- Navi del giocatore ------------------------------------------------
        cls.player_ships = [
            img("ship.png"),
            img("ship2.png"),
            img("ship3.png"),
        ]

        # -- Laser -------------------------------------------------------------
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

        # -- Nemici ------------------------------------------------------------
        # Lo sprite base (alien.png, il disco volante) viene usato come
        # nemico di default.  Dimensione: ENEMY_W x ENEMY_H (60x44) per
        # rispettare le proporzioni dell'immagine originale 350x350 (il
        # contenuto utile e' un UFO piu' largo che alto).
        cls.alien_sprite         = img("alien.png",         (ENEMY_W, ENEMY_H))
        cls.enemy_scout_sprite   = img("alien.png",         (ENEMY_W, ENEMY_H))
        cls.enemy_fighter_sprite = img("alien.png",         (ENEMY_W, ENEMY_H))
        cls.enemy_bomber_sprite  = img("alien.png",         (ENEMY_W, ENEMY_H))
        cls.enemy_elite_sprite   = img("alien.png",         (ENEMY_W, ENEMY_H))

        # -- Asteroide e scia --------------------------------------------------
        cls.asteroid_sprite = img(
            "asteroid_1_rotondo.png", (ASTEROID_SIZE, ASTEROID_SIZE))

        sheet = pygame.image.load(
            os.path.join(assets_dir, "asteroid_trail.png")).convert_alpha()
        cls.trail_frames = []
        for i in range(_TRAIL_N):
            frame = sheet.subsurface(
                pygame.Rect(i * _TRAIL_FW, 0, _TRAIL_FW, _TRAIL_FH)).copy()
            cls.trail_frames.append(frame)

        # -- Carrier e power-up ------------------------------------------------
        for pt in POWERUP_TYPES:
            cls.carrier_sprites[pt] = img(
                f"carrier_{pt}.png", (CARRIER_SIZE, CARRIER_SIZE))
            cls.powerup_sprites[pt] = img(
                f"powerup_{pt}.png", (POWERUP_ITEM_SIZE, POWERUP_ITEM_SIZE))

        # -- Boss (GIF animata) ------------------------------------------------
        cls.boss_frames = _gif_frames(os.path.join(assets_dir, "boss.gif"))

        # -- Esplosioni (GIF animata) ------------------------------------------
        cls.explosion_frames_raw = _gif_frames(
            os.path.join(assets_dir, "explosionGif.gif"))
        cls.explosion_frames = [
            pygame.transform.scale(f, (EXPLOSION_SIZE, EXPLOSION_SIZE))
            for f in cls.explosion_frames_raw
        ]

        cls._loaded = True
