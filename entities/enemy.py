"""
Enemy -- sprite animato da GIF, shake + mini-esplosione all'hit, pattern laser.

I 4 tipi di nemico usano sprite animati estratti da ``enemy_ships.gif``:
- scout:   laser singolo veloce, HP 1, punti 1
- fighter: laser doppio (offset laterale), HP 2, punti 3
- bomber:  laser lento ma pesante, HP 4, punti 5
- elite:   burst da 3 laser ravvicinati, HP 3, punti 8
"""

import random
import pygame

from core.constants import ENEMY_W, ENEMY_H, RED, ORANGE, YELLOW, CYAN, ENEMY_TYPE_STATS
from core.assets import Assets
from entities.formations import Slot

# ---------------------------------------------------------------------------
# Parametri shake all'hit (frame-based)
# ---------------------------------------------------------------------------
_SHAKE_DURATION  = 8
_SHAKE_AMPLITUDE = 3

# ---------------------------------------------------------------------------
# Colore del laser per ciascun tipo di nemico
# ---------------------------------------------------------------------------
_LASER_COLOR = {
    "scout":   RED,
    "fighter": ORANGE,
    "bomber":  (180, 0, 220),
    "elite":   CYAN,
    "default": RED,
}

# Velocita' del laser per tipo (pixel/frame)
_LASER_SPEED = {
    "scout":   6,
    "fighter": 5,
    "bomber":  3,
    "elite":   5,
    "default": 5,
}

# Intervallo di sparo (min, max) in frame
_SHOOT_INTERVAL = {
    "scout":   (70,  160),
    "fighter": (100, 200),
    "bomber":  (160, 320),
    "elite":   (80,  180),
    "default": (100, 200),
}


class Enemy:
    """Singolo nemico alieno con tipo, HP, sprite animato e pattern di sparo.

    Args:
        x, y:       Posizione iniziale.
        enemy_type: Tipo di nemico.
        hp:         Punti vita iniziali.
    """

    def __init__(self, x: float, y: float,
                 enemy_type: str = "scout", hp: int = 1):
        self.width  = ENEMY_W
        self.height = ENEMY_H
        self.x = x
        self.y = y
        self.alive = True

        self.enemy_type = enemy_type
        self.hp     = hp
        self.max_hp = hp

        self.h_speed = 0.0

        # Timer e intervallo sparo individuale
        lo, hi = _SHOOT_INTERVAL.get(enemy_type, (100, 200))
        self.shoot_timer    = random.randint(0, hi)
        self.shoot_interval = random.randint(lo, hi)

        # Slot logico nella griglia della formazione
        self.slot: Slot = Slot(0, 0)

        # Shake all'hit
        self._shake_timer = 0

        # Animazione GIF
        self._frame_idx   = 0
        self._frame_timer = 0
        self._frame_delay = 8

    # ------------------------------------------------------------------
    # DANNO
    # ------------------------------------------------------------------

    def take_damage(self, amount: int = 1) -> bool:
        """Applica danno al nemico e attiva shake + mini-esplosione.

        Returns:
            ``True`` se il nemico e' stato ucciso.
        """
        self.hp -= amount

        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True

        # Nemico sopravvive: attiva lo shake
        self._shake_timer = _SHAKE_DURATION
        return False

    # ------------------------------------------------------------------
    # SPRITE ANIMATO
    # ------------------------------------------------------------------

    def _get_frames(self) -> list[pygame.Surface]:
        frames = Assets.enemy_frames.get(self.enemy_type)
        if frames:
            return frames
        return Assets.enemy_frames.get("scout", [])

    # ------------------------------------------------------------------
    # LASER
    # ------------------------------------------------------------------

    def build_lasers(self) -> list:
        """Costruisce i laser secondo il pattern del tipo di nemico."""
        from entities.laser import Laser

        cx  = self.x + self.width // 2
        by  = self.y + self.height
        spd = _LASER_SPEED.get(self.enemy_type, 5)
        col = _LASER_COLOR.get(self.enemy_type, RED)
        lasers: list[Laser] = []

        if self.enemy_type == "scout":
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))
        elif self.enemy_type == "fighter":
            lasers.append(Laser(cx - 10, by, spd, col, is_enemy=True))
            lasers.append(Laser(cx + 8,  by, spd, col, is_enemy=True))
        elif self.enemy_type == "bomber":
            # Bomber: laser lento ma largo (3 paralleli)
            lasers.append(Laser(cx - 8, by, spd, col, is_enemy=True))
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))
            lasers.append(Laser(cx + 4, by, spd, col, is_enemy=True))
        elif self.enemy_type == "elite":
            # Elite: burst di 3 laser rapidi
            for dy in [0, 6, 12]:
                lasers.append(Laser(cx - 2, by + dy, spd, col, is_enemy=True))
        else:
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))

        return lasers

    # ------------------------------------------------------------------
    # DRAW
    # ------------------------------------------------------------------

    def draw(self, surf: pygame.Surface) -> None:
        """Disegna lo sprite animato del nemico con eventuale shake."""
        if not self.alive:
            return

        # Avanza animazione
        self._frame_timer += 1
        if self._frame_timer >= self._frame_delay:
            self._frame_timer = 0
            frames = self._get_frames()
            if frames:
                self._frame_idx = (self._frame_idx + 1) % len(frames)

        # Calcola offset di shake
        offset_x = 0
        if self._shake_timer > 0:
            ratio = self._shake_timer / _SHAKE_DURATION
            offset_x = int(_SHAKE_AMPLITUDE * ratio) * (
                1 if self._shake_timer % 2 == 0 else -1)
            self._shake_timer -= 1

        frames = self._get_frames()
        if frames:
            frame = frames[self._frame_idx % len(frames)]
            surf.blit(frame, (int(self.x + offset_x), int(self.y)))
        else:
            pygame.draw.rect(
                surf, RED,
                (int(self.x + offset_x), int(self.y), self.width, self.height))

        # Barra HP per nemici multi-HP
        if self.max_hp > 1 and self.hp > 0:
            self._draw_hp_bar(surf)

    def _draw_hp_bar(self, surf: pygame.Surface) -> None:
        """Disegna una piccola barra HP sopra il nemico."""
        bar_w = self.width - 10
        bar_h = 3
        bar_x = self.x + 5
        bar_y = self.y - 5

        pct = self.hp / self.max_hp
        pygame.draw.rect(surf, (40, 40, 40), (int(bar_x), int(bar_y), bar_w, bar_h))

        if pct > 0.5:
            col = (50, 255, 50)
        elif pct > 0.25:
            col = (255, 255, 50)
        else:
            col = (255, 50, 50)
        pygame.draw.rect(surf, col, (int(bar_x), int(bar_y), int(bar_w * pct), bar_h))

    # ------------------------------------------------------------------
    # HITBOX
    # ------------------------------------------------------------------

    def get_rect(self) -> pygame.Rect:
        sx, sy = 6, 4
        return pygame.Rect(
            self.x + sx,
            self.y + sy,
            self.width - sx * 2,
            self.height - sy * 2,
        )
