"""
Caricamento centralizzato degli asset grafici.

Tutti gli sprite (navi, nemici, laser, asteroidi, boss, esplosioni, power-up)
vengono caricati e pre-scalati una sola volta in ``Assets.load()``.

Le GIF animate (boss, esplosioni, navi giocatore, nemici) vengono
decomposte in frame individuali tramite Pillow (PIL) e convertite
in Surface Pygame per il rendering in tempo reale.
"""

import os
import pygame
from PIL import Image

from core.constants import (
    ENEMY_W, ENEMY_H, ASTEROID_SIZE, CARRIER_SIZE,
    POWERUP_ITEM_SIZE, EXPLOSION_SIZE, POWERUP_TYPES,
    NUM_PLAYER_SHIPS, NUM_BOSS_VARIANTS, PLAYER_W, PLAYER_H,
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

# ---------------------------------------------------------------------------
# Bounding-box delle navicelle nel foglio navicelle.gif (3 righe x 4 colonne).
# Ricavate dall'analisi automatica dei pixel (bg = RGB(29,35,40)).
# ---------------------------------------------------------------------------
_NAV_ROWS = [(30, 284), (316, 571), (603, 857)]
_NAV_COLS = [(25, 217), (246, 439), (466, 658), (687, 881)]
_NAV_BG   = (29, 35, 40)

# ---------------------------------------------------------------------------
# Bounding-box delle 4 navicelle nemiche in enemy_ships.gif.
# bg = RGB(255,255,255)
# ---------------------------------------------------------------------------
_ENEMY_COLS = [(38, 162), (202, 290), (341, 425), (479, 559)]
_ENEMY_ROW  = (44, 160)
_ENEMY_BG   = (255, 255, 255)


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
        data = rgba.tobytes()
        surf = pygame.image.fromstring(data, rgba.size, "RGBA")
        frames.append(surf)
    return frames


def _gif_frames_remove_bg(path: str, bg: tuple[int, int, int],
                           tolerance: int = 15) -> list[pygame.Surface]:
    """Come ``_gif_frames`` ma rimuove un colore di sfondo specifico."""
    frames: list[pygame.Surface] = []
    gif = Image.open(path)
    for i in range(gif.n_frames):
        gif.seek(i)
        rgba = gif.convert("RGBA")
        pixels = rgba.load()
        w, h = rgba.size
        for y in range(h):
            for x in range(w):
                r, g, b, a = pixels[x, y]
                if (abs(r - bg[0]) < tolerance and
                    abs(g - bg[1]) < tolerance and
                    abs(b - bg[2]) < tolerance):
                    pixels[x, y] = (0, 0, 0, 0)
        data = rgba.tobytes()
        surf = pygame.image.fromstring(data, rgba.size, "RGBA")
        frames.append(surf)
    return frames


def _spritestrip_frames(path: str) -> list[pygame.Surface]:
    """Legge un PNG spritestrip orizzontale (frame_h == altezza immagine)."""
    img = Image.open(path).convert("RGBA")
    fw = img.height
    n = img.width // fw
    frames: list[pygame.Surface] = []
    for i in range(n):
        crop = img.crop((i * fw, 0, (i + 1) * fw, fw))
        data = crop.tobytes()
        surf = pygame.image.fromstring(data, crop.size, "RGBA")
        frames.append(surf)
    return frames


def _extract_ship_frames_from_gif(gif_path: str,
                                   row_bounds: list[tuple[int, int]],
                                   col_bounds: list[tuple[int, int]],
                                   bg: tuple[int, int, int],
                                   tolerance: int = 15,
                                   ) -> list[list[pygame.Surface]]:
    """Estrae le navicelle animate da un foglio GIF a griglia."""
    gif = Image.open(gif_path)
    n_frames = gif.n_frames

    raw_frames: list[Image.Image] = []
    for i in range(n_frames):
        gif.seek(i)
        raw_frames.append(gif.convert("RGBA").copy())

    ships: list[list[pygame.Surface]] = []
    for ry1, ry2 in row_bounds:
        for cx1, cx2 in col_bounds:
            cell_frames: list[pygame.Surface] = []
            for frame in raw_frames:
                cell = frame.crop((cx1, ry1, cx2, ry2)).copy()
                pixels = cell.load()
                w, h = cell.size
                for y in range(h):
                    for x in range(w):
                        r, g, b, a = pixels[x, y]
                        if (abs(r - bg[0]) < tolerance and
                            abs(g - bg[1]) < tolerance and
                            abs(b - bg[2]) < tolerance):
                            pixels[x, y] = (0, 0, 0, 0)
                data = cell.tobytes()
                surf = pygame.image.fromstring(data, cell.size, "RGBA")
                cell_frames.append(surf)
            ships.append(cell_frames)
    return ships


def _extract_enemy_frames_from_gif(gif_path: str,
                                    col_bounds: list[tuple[int, int]],
                                    row_bound: tuple[int, int],
                                    bg: tuple[int, int, int],
                                    tolerance: int = 18,
                                    ) -> list[list[pygame.Surface]]:
    """Estrae le navicelle nemiche da un foglio GIF (una riga, 4 colonne)."""
    gif = Image.open(gif_path)
    n_frames = gif.n_frames

    raw_frames: list[Image.Image] = []
    for i in range(n_frames):
        gif.seek(i)
        raw_frames.append(gif.convert("RGBA").copy())

    enemies: list[list[pygame.Surface]] = []
    ry1, ry2 = row_bound
    for cx1, cx2 in col_bounds:
        cell_frames: list[pygame.Surface] = []
        for frame in raw_frames:
            cell = frame.crop((cx1, ry1, cx2, ry2)).copy()
            pixels = cell.load()
            w, h = cell.size
            for y in range(h):
                for x in range(w):
                    r, g, b, a = pixels[x, y]
                    if (abs(r - bg[0]) < tolerance and
                        abs(g - bg[1]) < tolerance and
                        abs(b - bg[2]) < tolerance):
                        pixels[x, y] = (0, 0, 0, 0)
            data = cell.tobytes()
            surf = pygame.image.fromstring(data, cell.size, "RGBA")
            cell_frames.append(surf)
        enemies.append(cell_frames)
    return enemies


class Assets:
    """Contenitore statico per tutti gli asset grafici del gioco."""

    _loaded: bool = False

    # -- Navi del giocatore (5 tipi, animate) --
    player_ship_frames: list[list[pygame.Surface]] = []

    # -- Laser (sprite pre-scalati per ciascun tipo di nave) --
    laser_sprites:       list[pygame.Surface] = []
    laser_left_angular:  list[pygame.Surface] = []
    laser_right_angular: list[pygame.Surface] = []
    enemy_laser_sprite_scaled: pygame.Surface | None = None

    # -- Nemici (4 tipi, animati) --
    enemy_frames: dict[str, list[pygame.Surface]] = {}

    # -- Asteroide e scia --
    asteroid_sprite: pygame.Surface | None = None
    trail_frames:    list[pygame.Surface] = []

    # -- Carrier e power-up --
    carrier_sprites: dict[str, pygame.Surface] = {}
    powerup_sprites: dict[str, pygame.Surface] = {}

    # -- Boss varianti (5 boss, ciascuno con lista di frame) --
    boss_variant_frames: list[list[pygame.Surface]] = []

    # -- Esplosioni (frame da GIF) --
    explosion_frames:     list[pygame.Surface] = []
    explosion_frames_raw: list[pygame.Surface] = []

    @classmethod
    def load(cls) -> None:
        """Carica tutti gli asset grafici dal disco."""
        if cls._loaded:
            return

        base = _base()
        assets_dir = os.path.join(base, "Assets")
        laser_dir  = os.path.join(base, "LaserSprites")

        def img(name: str, size: tuple[int, int] | None = None) -> pygame.Surface:
            surf = pygame.image.load(os.path.join(assets_dir, name)).convert_alpha()
            return pygame.transform.scale(surf, size) if size else surf

        def lz(name: str) -> pygame.Surface:
            return pygame.transform.scale(
                pygame.image.load(os.path.join(laser_dir, name)).convert_alpha(),
                (_LASER_W, _LASER_H),
            )

        # ==============================================================
        # NAVI GIOCATORE (5 navi animate da navicelle.gif)
        # ==============================================================
        all_ships = _extract_ship_frames_from_gif(
            os.path.join(assets_dir, "navicelle.gif"),
            _NAV_ROWS, _NAV_COLS, _NAV_BG, tolerance=15,
        )
        # Seleziona 5 navi visivamente distinte dal foglio 3x4
        # Indici nel foglio: 1, 2, 5, 8, 11 (le migliori visivamente)
        selected_indices = [1, 2, 5, 8, 11]
        cls.player_ship_frames = []
        for idx in selected_indices:
            if idx < len(all_ships):
                cls.player_ship_frames.append(all_ships[idx])
            else:
                # Fallback: usa l'ultimo disponibile
                cls.player_ship_frames.append(all_ships[-1])

        # ==============================================================
        # LASER
        # ==============================================================
        _base_lasers      = [lz("11.png"), lz("16.png"), lz("12.png")]
        _base_left_angled = [lz("11LeftAngular.png"), lz("16LeftAngular.png"), lz("12LeftAngular.png")]
        _base_right_angled = [lz("11RightAngular.png"), lz("16RightAngular.png"), lz("12RightAngular.png")]

        cls.laser_sprites = [_base_lasers[i % 3] for i in range(NUM_PLAYER_SHIPS)]
        cls.laser_left_angular = [_base_left_angled[i % 3] for i in range(NUM_PLAYER_SHIPS)]
        cls.laser_right_angular = [_base_right_angled[i % 3] for i in range(NUM_PLAYER_SHIPS)]
        cls.enemy_laser_sprite_scaled = lz("14.png")

        # ==============================================================
        # NEMICI (4 tipi animati da enemy_ships.gif)
        # ==============================================================
        enemy_type_names = ["scout", "fighter", "bomber", "elite"]
        raw_enemy = _extract_enemy_frames_from_gif(
            os.path.join(assets_dir, "enemy_ships.gif"),
            _ENEMY_COLS, _ENEMY_ROW, _ENEMY_BG, tolerance=18,
        )
        cls.enemy_frames = {}
        for i, name in enumerate(enemy_type_names):
            cls.enemy_frames[name] = [
                pygame.transform.scale(f, (ENEMY_W, ENEMY_H))
                for f in raw_enemy[i]
            ]

        # ==============================================================
        # ASTEROIDE e scia
        # ==============================================================
        cls.asteroid_sprite = img(
            "asteroid_1_rotondo.png", (ASTEROID_SIZE, ASTEROID_SIZE))

        sheet = pygame.image.load(
            os.path.join(assets_dir, "asteroid_trail.png")).convert_alpha()
        cls.trail_frames = []
        for i in range(_TRAIL_N):
            frame = sheet.subsurface(
                pygame.Rect(i * _TRAIL_FW, 0, _TRAIL_FW, _TRAIL_FH)).copy()
            cls.trail_frames.append(frame)

        # ==============================================================
        # CARRIER e POWER-UP
        # ==============================================================
        for pt in POWERUP_TYPES:
            # Bomba riusa lo sprite scudo (colore diverso via tint)
            carrier_file = f"carrier_{pt}.png"
            powerup_file = f"powerup_{pt}.png"
            carrier_path = os.path.join(assets_dir, carrier_file)
            powerup_path = os.path.join(assets_dir, powerup_file)

            if os.path.exists(carrier_path):
                cls.carrier_sprites[pt] = img(carrier_file, (CARRIER_SIZE, CARRIER_SIZE))
            else:
                # Fallback: usa carrier_scudo per nuovi tipi
                cls.carrier_sprites[pt] = img("carrier_scudo.png", (CARRIER_SIZE, CARRIER_SIZE))

            if os.path.exists(powerup_path):
                cls.powerup_sprites[pt] = img(powerup_file, (POWERUP_ITEM_SIZE, POWERUP_ITEM_SIZE))
            else:
                # Fallback: usa powerup_scudo per nuovi tipi
                cls.powerup_sprites[pt] = img("powerup_scudo.png", (POWERUP_ITEM_SIZE, POWERUP_ITEM_SIZE))

        # ==============================================================
        # BOSS VARIANTI (5 boss)
        # ==============================================================
        boss_files = ["boss.gif", "boss_1.gif", "boss_2.gif", "boss_3.gif"]
        cls.boss_variant_frames = []
        for bf in boss_files:
            path = os.path.join(assets_dir, bf)
            cls.boss_variant_frames.append(_gif_frames(path))

        # boss_4: spritestrip PNG
        boss4_path = os.path.join(assets_dir, "boss_4.png")
        cls.boss_variant_frames.append(_spritestrip_frames(boss4_path))

        # ==============================================================
        # ESPLOSIONI (GIF animata)
        # ==============================================================
        cls.explosion_frames_raw = _gif_frames(
            os.path.join(assets_dir, "explosionGif.gif"))
        cls.explosion_frames = [
            pygame.transform.scale(f, (EXPLOSION_SIZE, EXPLOSION_SIZE))
            for f in cls.explosion_frames_raw
        ]

        cls._loaded = True
