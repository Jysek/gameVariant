"""
Centralized asset loading.

All sprites (ships, enemies, lasers, asteroids, bosses, explosions, power-ups)
are loaded and pre-scaled once in ``Assets.load()``.

Animated GIFs (bosses, explosions, player ships, enemies) are decomposed
into individual frames via Pillow (PIL) and converted to Pygame Surfaces
for real-time rendering.

Laser sprites are cleaned of their semi-transparent glow halo during loading
to prevent colored rectangles from appearing when lasers pass over HUD text.
"""

import os
import pygame
from PIL import Image
import numpy as np

from core.constants import (
    ENEMY_W, ENEMY_H, ASTEROID_SIZE, CARRIER_SIZE,
    POWERUP_ITEM_SIZE, EXPLOSION_SIZE, POWERUP_TYPES,
    NUM_PLAYER_SHIPS, NUM_BOSS_VARIANTS, PLAYER_W, PLAYER_H,
)

# ---------------------------------------------------------------------------
# Pre-scaled laser dimensions
# ---------------------------------------------------------------------------
_LASER_W = 20
_LASER_H = 40

# ---------------------------------------------------------------------------
# Asteroid trail spritesheet params (horizontal strip, 12 frames)
# ---------------------------------------------------------------------------
_TRAIL_FW = 32
_TRAIL_FH = 32
_TRAIL_N  = 12

# ---------------------------------------------------------------------------
# Bounding boxes for ships in navicelle.gif (3 rows x 4 columns).
# Derived from automatic pixel analysis (bg = RGB(29,35,40)).
# ---------------------------------------------------------------------------
_NAV_ROWS = [(30, 284), (316, 571), (603, 857)]
_NAV_COLS = [(25, 217), (246, 439), (466, 658), (687, 881)]
_NAV_BG   = (29, 35, 40)

# ---------------------------------------------------------------------------
# Bounding boxes for the 4 enemy ships in enemy_ships.gif.
# bg = RGB(255,255,255)
# ---------------------------------------------------------------------------
_ENEMY_COLS = [(38, 162), (202, 290), (341, 425), (479, 559)]
_ENEMY_ROW  = (44, 160)
_ENEMY_BG   = (255, 255, 255)


def _base() -> str:
    """Return the project root directory path."""
    return os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))


# Alpha threshold for stripping glow halos from laser sprites.
# Pixels with alpha <= this value are made fully transparent.
_LASER_GLOW_ALPHA_THRESHOLD = 80


def _strip_laser_glow(surf: pygame.Surface) -> pygame.Surface:
    """Remove the semi-transparent glow halo from a laser sprite.

    Laser PNGs have a large semi-transparent glow area that creates
    visible colored rectangles when the sprite is drawn over HUD text.
    This function sets all pixels below the alpha threshold to fully
    transparent, keeping only the bright core of the laser.

    Uses numpy for fast pixel manipulation.

    Args:
        surf: Source Pygame surface with alpha.

    Returns:
        New surface with the glow stripped.
    """
    w, h = surf.get_size()
    # Get pixel data as a 3D numpy array (h, w, 4) for RGBA
    arr = pygame.surfarray.pixels_alpha(surf)
    # Set pixels with low alpha to fully transparent
    arr[arr <= _LASER_GLOW_ALPHA_THRESHOLD] = 0
    del arr  # Release the pixel lock
    return surf


def _gif_frames(path: str) -> list[pygame.Surface]:
    """Decompose an animated GIF into individual frames.

    Uses Pillow to read each GIF frame, converts to RGBA,
    and transforms into a Pygame Surface.

    Args:
        path: Absolute path to the GIF file.

    Returns:
        List of ``pygame.Surface`` (one per frame).
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


def _gif_frames_remove_bg(
    path: str, bg: tuple[int, int, int], tolerance: int = 15
) -> list[pygame.Surface]:
    """Like ``_gif_frames`` but removes a specific background color.

    Uses numpy for significantly faster pixel processing.
    """
    frames: list[pygame.Surface] = []
    gif = Image.open(path)
    for i in range(gif.n_frames):
        gif.seek(i)
        rgba = gif.convert("RGBA")
        arr = np.array(rgba)
        # Build a boolean mask for pixels matching the background color
        mask = (
            (np.abs(arr[:, :, 0].astype(int) - bg[0]) < tolerance)
            & (np.abs(arr[:, :, 1].astype(int) - bg[1]) < tolerance)
            & (np.abs(arr[:, :, 2].astype(int) - bg[2]) < tolerance)
        )
        arr[mask] = [0, 0, 0, 0]
        cleaned = Image.fromarray(arr, "RGBA")
        data = cleaned.tobytes()
        surf = pygame.image.fromstring(data, cleaned.size, "RGBA")
        frames.append(surf)
    return frames


def _spritestrip_frames(path: str) -> list[pygame.Surface]:
    """Read a horizontal PNG spritestrip (frame_h == image height)."""
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


def _extract_ship_frames_from_gif(
    gif_path: str,
    row_bounds: list[tuple[int, int]],
    col_bounds: list[tuple[int, int]],
    bg: tuple[int, int, int],
    tolerance: int = 15,
) -> list[list[pygame.Surface]]:
    """Extract animated ships from a grid-layout GIF spritesheet.

    Uses numpy for significantly faster background removal.

    Args:
        gif_path:   Path to the GIF file.
        row_bounds: List of (y_start, y_end) for each row.
        col_bounds: List of (x_start, x_end) for each column.
        bg:         Background color to remove.
        tolerance:  Color matching tolerance.

    Returns:
        List of ship frame lists (one list per ship cell).
    """
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
                arr = np.array(cell)
                mask = (
                    (np.abs(arr[:, :, 0].astype(int) - bg[0]) < tolerance)
                    & (np.abs(arr[:, :, 1].astype(int) - bg[1]) < tolerance)
                    & (np.abs(arr[:, :, 2].astype(int) - bg[2]) < tolerance)
                )
                arr[mask] = [0, 0, 0, 0]
                cleaned = Image.fromarray(arr, "RGBA")
                data = cleaned.tobytes()
                surf = pygame.image.fromstring(data, cleaned.size, "RGBA")
                cell_frames.append(surf)
            ships.append(cell_frames)
    return ships


def _extract_enemy_frames_from_gif(
    gif_path: str,
    col_bounds: list[tuple[int, int]],
    row_bound: tuple[int, int],
    bg: tuple[int, int, int],
    tolerance: int = 18,
) -> list[list[pygame.Surface]]:
    """Extract enemy ship frames from a GIF (one row, 4 columns).

    Uses numpy for significantly faster background removal.

    Args:
        gif_path:   Path to the GIF file.
        col_bounds: List of (x_start, x_end) for each enemy column.
        row_bound:  (y_start, y_end) for the single row.
        bg:         Background color to remove.
        tolerance:  Color matching tolerance.

    Returns:
        List of enemy frame lists (one list per enemy type).
    """
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
            arr = np.array(cell)
            mask = (
                (np.abs(arr[:, :, 0].astype(int) - bg[0]) < tolerance)
                & (np.abs(arr[:, :, 1].astype(int) - bg[1]) < tolerance)
                & (np.abs(arr[:, :, 2].astype(int) - bg[2]) < tolerance)
            )
            arr[mask] = [0, 0, 0, 0]
            cleaned = Image.fromarray(arr, "RGBA")
            data = cleaned.tobytes()
            surf = pygame.image.fromstring(data, cleaned.size, "RGBA")
            cell_frames.append(surf)
        enemies.append(cell_frames)
    return enemies


class Assets:
    """Static container for all graphical game assets."""

    _loaded: bool = False

    # -- Player ships (5 types, animated) --
    player_ship_frames: list[list[pygame.Surface]] = []

    # -- Lasers (pre-scaled sprites for each ship type) --
    laser_sprites:       list[pygame.Surface] = []
    laser_left_angular:  list[pygame.Surface] = []
    laser_right_angular: list[pygame.Surface] = []
    enemy_laser_sprite_scaled: pygame.Surface | None = None

    # -- Enemies (4 types, animated) --
    enemy_frames: dict[str, list[pygame.Surface]] = {}

    # -- Asteroid and trail --
    asteroid_sprite: pygame.Surface | None = None
    trail_frames:    list[pygame.Surface] = []

    # -- Carriers and power-ups --
    carrier_sprites: dict[str, pygame.Surface] = {}
    powerup_sprites: dict[str, pygame.Surface] = {}

    # -- Boss variants (4 bosses, each with a list of frames) --
    boss_variant_frames: list[list[pygame.Surface]] = []

    # -- Explosions (frames from GIF) --
    explosion_frames:     list[pygame.Surface] = []
    explosion_frames_raw: list[pygame.Surface] = []

    @classmethod
    def load(cls) -> None:
        """Load all graphical assets from disk.

        This method should be called once after ``pygame.display.set_mode()``
        so that ``convert_alpha()`` works correctly.
        """
        if cls._loaded:
            return

        base = _base()
        assets_dir = os.path.join(base, "Assets")
        laser_dir  = os.path.join(base, "LaserSprites")

        def img(name: str, size: tuple[int, int] | None = None) -> pygame.Surface:
            """Load and optionally scale a PNG from the Assets directory."""
            surf = pygame.image.load(os.path.join(assets_dir, name)).convert_alpha()
            return pygame.transform.scale(surf, size) if size else surf

        def lz(name: str) -> pygame.Surface:
            """Load, strip glow, and scale a laser sprite.

            Strips the semi-transparent glow halo before scaling to
            prevent colored rectangles appearing over HUD text.
            """
            raw = pygame.image.load(os.path.join(laser_dir, name)).convert_alpha()
            _strip_laser_glow(raw)
            return pygame.transform.scale(raw, (_LASER_W, _LASER_H))

        # ==============================================================
        # PLAYER SHIPS (5 animated ships from navicelle.gif)
        # ==============================================================
        all_ships = _extract_ship_frames_from_gif(
            os.path.join(assets_dir, "navicelle.gif"),
            _NAV_ROWS, _NAV_COLS, _NAV_BG, tolerance=15,
        )
        # Select 5 visually distinct ships from the 3x4 sheet
        selected_indices = [1, 2, 5, 8, 11]
        cls.player_ship_frames = []
        for idx in selected_indices:
            if idx < len(all_ships):
                cls.player_ship_frames.append(all_ships[idx])
            else:
                cls.player_ship_frames.append(all_ships[-1])

        # ==============================================================
        # LASERS
        # ==============================================================
        _base_lasers       = [lz("11.png"), lz("16.png"), lz("12.png")]
        _base_left_angled  = [lz("11LeftAngular.png"), lz("16LeftAngular.png"),
                              lz("12LeftAngular.png")]
        _base_right_angled = [lz("11RightAngular.png"), lz("16RightAngular.png"),
                              lz("12RightAngular.png")]

        cls.laser_sprites       = [_base_lasers[i % 3] for i in range(NUM_PLAYER_SHIPS)]
        cls.laser_left_angular  = [_base_left_angled[i % 3] for i in range(NUM_PLAYER_SHIPS)]
        cls.laser_right_angular = [_base_right_angled[i % 3] for i in range(NUM_PLAYER_SHIPS)]
        cls.enemy_laser_sprite_scaled = lz("14.png")

        # ==============================================================
        # ENEMIES (4 animated types from enemy_ships.gif)
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
        # ASTEROID and trail
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
        # CARRIERS and POWER-UPS (including bomb with proper sprites)
        # ==============================================================
        for pt in POWERUP_TYPES:
            carrier_file = f"carrier_{pt}.png"
            powerup_file = f"powerup_{pt}.png"
            carrier_path = os.path.join(assets_dir, carrier_file)
            powerup_path = os.path.join(assets_dir, powerup_file)

            if os.path.exists(carrier_path):
                cls.carrier_sprites[pt] = img(carrier_file, (CARRIER_SIZE, CARRIER_SIZE))
            else:
                cls.carrier_sprites[pt] = img("carrier_scudo.png", (CARRIER_SIZE, CARRIER_SIZE))

            if os.path.exists(powerup_path):
                cls.powerup_sprites[pt] = img(powerup_file, (POWERUP_ITEM_SIZE, POWERUP_ITEM_SIZE))
            else:
                cls.powerup_sprites[pt] = img("powerup_scudo.png", (POWERUP_ITEM_SIZE, POWERUP_ITEM_SIZE))

        # ==============================================================
        # BOSS VARIANTS (4 bosses -- boss_4 removed)
        # ==============================================================
        boss_files = ["boss.gif", "boss_1.gif", "boss_2.gif", "boss_3.gif"]
        cls.boss_variant_frames = []
        for bf in boss_files:
            path = os.path.join(assets_dir, bf)
            cls.boss_variant_frames.append(_gif_frames(path))

        # ==============================================================
        # EXPLOSIONS (animated GIF)
        # ==============================================================
        cls.explosion_frames_raw = _gif_frames(
            os.path.join(assets_dir, "explosionGif.gif"))
        cls.explosion_frames = [
            pygame.transform.scale(f, (EXPLOSION_SIZE, EXPLOSION_SIZE))
            for f in cls.explosion_frames_raw
        ]

        cls._loaded = True
