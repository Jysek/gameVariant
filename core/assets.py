"""
Caricamento centralizzato degli asset grafici.

Tutti gli sprite (navi, nemici, laser, asteroidi, boss, esplosioni, power-up)
vengono caricati e pre-scalati una sola volta in ``Assets.load()``.

Le GIF animate (boss, esplosioni, navi giocatore, nemici) vengono decomposte
in singoli frame tramite Pillow (PIL) e convertite in Surface Pygame
per il rendering in tempo reale.

Gli sprite laser vengono puliti dall'alone semi-trasparente durante il
caricamento per evitare rettangoli colorati. La soglia alpha e alta (180)
e dopo la scalatura tutti i pixel con alpha < 255 vengono azzerati per
ottenere sprite binari (completamente opachi o completamente trasparenti).
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
# Dimensioni laser pre-scalati
# ---------------------------------------------------------------------------
_LASER_W = 20
_LASER_H = 40

# ---------------------------------------------------------------------------
# Parametri spritestrip scia asteroide (striscia orizzontale, 12 frame)
# ---------------------------------------------------------------------------
_TRAIL_FW = 32
_TRAIL_FH = 32
_TRAIL_N  = 12

# ---------------------------------------------------------------------------
# Bounding box delle navi in navicelle.gif (3 righe x 4 colonne).
# Derivate da analisi automatica dei pixel (bg = RGB(29,35,40)).
# ---------------------------------------------------------------------------
_NAV_ROWS = [(30, 284), (316, 571), (603, 857)]
_NAV_COLS = [(25, 217), (246, 439), (466, 658), (687, 881)]
_NAV_BG   = (29, 35, 40)

# ---------------------------------------------------------------------------
# Bounding box dei 4 nemici in enemy_ships.gif.
# bg = RGB(255,255,255)
# ---------------------------------------------------------------------------
_ENEMY_COLS = [(38, 162), (202, 290), (341, 425), (479, 559)]
_ENEMY_ROW  = (44, 160)
_ENEMY_BG   = (255, 255, 255)

# Soglia alpha per rimuovere l'alone glow dagli sprite laser.
# I pixel con alpha <= questa soglia diventano completamente trasparenti.
# Valore alto (180) per eliminare completamente i rettangoli semi-trasparenti
# che apparivano quando un laser passava sopra carrier, nemici o testi HUD.
_LASER_GLOW_ALPHA_THRESHOLD = 180


def _base() -> str:
    """Restituisce il percorso della directory root del progetto."""
    return os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))


def _strip_laser_glow(surf: pygame.Surface) -> pygame.Surface:
    """Rimuove l'alone semi-trasparente da uno sprite laser.

    I PNG dei laser hanno una grande area semi-trasparente di glow che crea
    rettangoli colorati visibili quando lo sprite viene disegnato sopra il
    testo dell'HUD. Questa funzione imposta tutti i pixel sotto la soglia
    alpha a completamente trasparenti, mantenendo solo il nucleo luminoso.

    Usa numpy per manipolazione pixel veloce.

    Args:
        surf: Surface Pygame sorgente con alpha.

    Returns:
        La stessa surface con il glow rimosso.
    """
    arr = pygame.surfarray.pixels_alpha(surf)
    arr[arr <= _LASER_GLOW_ALPHA_THRESHOLD] = 0
    del arr  # Rilascia il lock sui pixel
    return surf


def _gif_frames(path: str) -> list[pygame.Surface]:
    """Decompone una GIF animata in singoli frame.

    Usa Pillow per leggere ogni frame della GIF, converte in RGBA,
    e trasforma in una Surface Pygame.

    Args:
        path: Percorso assoluto del file GIF.

    Returns:
        Lista di ``pygame.Surface`` (uno per frame).
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
    """Come ``_gif_frames`` ma rimuove un colore di sfondo specifico.

    Usa numpy per un'elaborazione pixel significativamente più veloce.

    Args:
        path:      Percorso del file GIF.
        bg:        Colore di sfondo da rimuovere (R, G, B).
        tolerance: Tolleranza di matching del colore.

    Returns:
        Lista di Surface Pygame con sfondo rimosso.
    """
    frames: list[pygame.Surface] = []
    gif = Image.open(path)
    for i in range(gif.n_frames):
        gif.seek(i)
        rgba = gif.convert("RGBA")
        arr = np.array(rgba)
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
    """Legge uno spritestrip orizzontale PNG (frame_h == altezza immagine).

    Args:
        path: Percorso del file PNG.

    Returns:
        Lista di Surface Pygame (uno per frame).
    """
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
    """Estrae navi animate da uno spritesheet GIF a griglia.

    Usa numpy per rimozione sfondo significativamente più veloce.

    Args:
        gif_path:   Percorso del file GIF.
        row_bounds: Lista di (y_start, y_end) per ogni riga.
        col_bounds: Lista di (x_start, x_end) per ogni colonna.
        bg:         Colore di sfondo da rimuovere.
        tolerance:  Tolleranza matching colore.

    Returns:
        Lista di liste di frame nave (una lista per cella della griglia).
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
    """Estrae frame nemici animati da una GIF (una riga, 4 colonne).

    Usa numpy per rimozione sfondo significativamente più veloce.

    Args:
        gif_path:   Percorso del file GIF.
        col_bounds: Lista di (x_start, x_end) per ogni colonna nemico.
        row_bound:  (y_start, y_end) per la singola riga.
        bg:         Colore di sfondo da rimuovere.
        tolerance:  Tolleranza matching colore.

    Returns:
        Lista di liste di frame nemico (una lista per tipo nemico).
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
    """Contenitore statico per tutti gli asset grafici del gioco.

    Tutti gli sprite vengono caricati una sola volta con ``Assets.load()``
    dopo la creazione della finestra Pygame, così ``convert_alpha()`` funziona.
    """

    _loaded: bool = False

    # -- Navi giocatore (5 tipi, animate) --
    player_ship_frames: list[list[pygame.Surface]] = []

    # -- Laser (sprite pre-scalati per ogni tipo di nave) --
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

    # -- Varianti boss (4 boss, ciascuno con una lista di frame) --
    boss_variant_frames: list[list[pygame.Surface]] = []

    # -- Esplosioni (frame da GIF) --
    explosion_frames:     list[pygame.Surface] = []
    explosion_frames_raw: list[pygame.Surface] = []

    @classmethod
    def load(cls) -> None:
        """Carica tutti gli asset grafici dal disco.

        Questo metodo va chiamato una volta dopo ``pygame.display.set_mode()``
        affinche ``convert_alpha()`` funzioni correttamente.

        Struttura directory attesa: assets/ con sottocartelle
        ships/, enemies/, bosses/, sprites/, effects/, powerups/, lasers/.
        """
        if cls._loaded:
            return

        base = _base()
        assets_dir = os.path.join(base, "assets")

        ships_dir    = os.path.join(assets_dir, "ships")
        enemies_dir  = os.path.join(assets_dir, "enemies")
        bosses_dir   = os.path.join(assets_dir, "bosses")
        sprites_dir  = os.path.join(assets_dir, "sprites")
        effects_dir  = os.path.join(assets_dir, "effects")
        powerups_dir = os.path.join(assets_dir, "powerups")
        laser_dir    = os.path.join(assets_dir, "lasers")

        def img(directory: str, name: str,
                size: tuple[int, int] | None = None) -> pygame.Surface:
            """Carica e opzionalmente scala un PNG da una directory."""
            surf = pygame.image.load(
                os.path.join(directory, name)).convert_alpha()
            return pygame.transform.scale(surf, size) if size else surf

        def lz(name: str) -> pygame.Surface:
            """Carica, rimuovi glow e scala uno sprite laser.

            Rimuove l'alone semi-trasparente prima della scalatura, poi
            elimina i pixel semi-trasparenti residui introdotti dalla
            scalatura bilineare. Dopo lo scaling, qualsiasi pixel con
            alpha < 255 viene reso completamente trasparente per
            evitare rettangoli visibili su carrier, nemici e HUD.
            """
            raw = pygame.image.load(
                os.path.join(laser_dir, name)).convert_alpha()
            _strip_laser_glow(raw)
            scaled = pygame.transform.scale(raw, (_LASER_W, _LASER_H))
            # Dopo la scalatura, rendi completamente trasparenti tutti
            # i pixel semi-trasparenti residui (alpha < 255).
            arr = pygame.surfarray.pixels_alpha(scaled)
            arr[arr < 255] = 0
            del arr
            return scaled

        # ==============================================================
        # NAVI GIOCATORE (5 navi animate da navicelle.gif)
        # ==============================================================
        all_ships = _extract_ship_frames_from_gif(
            os.path.join(ships_dir, "navicelle.gif"),
            _NAV_ROWS, _NAV_COLS, _NAV_BG, tolerance=15,
        )
        # Seleziona 5 navi visivamente distinte dal foglio 3x4
        selected_indices = [1, 2, 5, 8, 11]
        cls.player_ship_frames = []
        for idx in selected_indices:
            if idx < len(all_ships):
                cls.player_ship_frames.append(all_ships[idx])
            else:
                cls.player_ship_frames.append(all_ships[-1])

        # ==============================================================
        # LASER
        # ==============================================================
        _base_lasers       = [lz("11.png"), lz("16.png"), lz("12.png")]
        _base_left_angled  = [lz("11LeftAngular.png"), lz("16LeftAngular.png"),
                              lz("12LeftAngular.png")]
        _base_right_angled = [lz("11RightAngular.png"), lz("16RightAngular.png"),
                              lz("12RightAngular.png")]

        cls.laser_sprites       = [_base_lasers[i % 3]
                                   for i in range(NUM_PLAYER_SHIPS)]
        cls.laser_left_angular  = [_base_left_angled[i % 3]
                                   for i in range(NUM_PLAYER_SHIPS)]
        cls.laser_right_angular = [_base_right_angled[i % 3]
                                   for i in range(NUM_PLAYER_SHIPS)]
        cls.enemy_laser_sprite_scaled = lz("14.png")

        # ==============================================================
        # NEMICI (4 tipi animati da enemy_ships.gif)
        # ==============================================================
        enemy_type_names = ["scout", "fighter", "bomber", "elite"]
        raw_enemy = _extract_enemy_frames_from_gif(
            os.path.join(enemies_dir, "enemy_ships.gif"),
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
            sprites_dir, "asteroid_1_rotondo.png",
            (ASTEROID_SIZE, ASTEROID_SIZE))

        sheet = pygame.image.load(
            os.path.join(sprites_dir, "asteroid_trail.png")).convert_alpha()
        cls.trail_frames = []
        for i in range(_TRAIL_N):
            frame = sheet.subsurface(
                pygame.Rect(i * _TRAIL_FW, 0, _TRAIL_FW, _TRAIL_FH)).copy()
            cls.trail_frames.append(frame)

        # ==============================================================
        # CARRIER e POWER-UP (inclusa la bomba con sprite propri)
        # ==============================================================
        for pt in POWERUP_TYPES:
            carrier_file = f"carrier_{pt}.png"
            powerup_file = f"powerup_{pt}.png"
            carrier_path = os.path.join(powerups_dir, carrier_file)
            powerup_path = os.path.join(powerups_dir, powerup_file)

            if os.path.exists(carrier_path):
                cls.carrier_sprites[pt] = img(
                    powerups_dir, carrier_file,
                    (CARRIER_SIZE, CARRIER_SIZE))
            else:
                cls.carrier_sprites[pt] = img(
                    powerups_dir, "carrier_scudo.png",
                    (CARRIER_SIZE, CARRIER_SIZE))

            if os.path.exists(powerup_path):
                cls.powerup_sprites[pt] = img(
                    powerups_dir, powerup_file,
                    (POWERUP_ITEM_SIZE, POWERUP_ITEM_SIZE))
            else:
                cls.powerup_sprites[pt] = img(
                    powerups_dir, "powerup_scudo.png",
                    (POWERUP_ITEM_SIZE, POWERUP_ITEM_SIZE))

        # ==============================================================
        # VARIANTI BOSS (4 boss)
        # ==============================================================
        # Alcune GIF boss (es. boss_3.gif) hanno uno sfondo scuro
        # opaco (16,16,20) che crea rettangoli visibili durante il
        # rendering. Rimuoviamo lo sfondo scuro quasi-nero e lo
        # sfondo bianco per ottenere la trasparenza corretta.
        boss_files = ["boss.gif", "boss_1.gif", "boss_2.gif", "boss_3.gif"]
        _boss_bg_colors = [
            (0, 0, 0),        # boss.gif: sfondo nero
            (255, 255, 255),  # boss_1.gif: sfondo bianco
            (0, 0, 0),        # boss_2.gif: sfondo nero
            (16, 16, 20),     # boss_3.gif: sfondo scuro quasi-nero
        ]
        cls.boss_variant_frames = []
        for bf, bg_color in zip(boss_files, _boss_bg_colors):
            path = os.path.join(bosses_dir, bf)
            cls.boss_variant_frames.append(
                _gif_frames_remove_bg(path, bg=bg_color, tolerance=20))

        # ==============================================================
        # ESPLOSIONI (GIF animata, sfondo bianco rimosso)
        # ==============================================================
        # La GIF esplosione usa bianco (255,255,255) come colore di sfondo
        # trasparente. _gif_frames_remove_bg elimina i pixel di sfondo
        # residui che possono apparire come rettangoli bianchi durante
        # l'animazione, specialmente nei frame intermedi.
        cls.explosion_frames_raw = _gif_frames_remove_bg(
            os.path.join(effects_dir, "explosionGif.gif"),
            bg=(255, 255, 255), tolerance=8)
        cls.explosion_frames = [
            pygame.transform.scale(f, (EXPLOSION_SIZE, EXPLOSION_SIZE))
            for f in cls.explosion_frames_raw
        ]

        cls._loaded = True
