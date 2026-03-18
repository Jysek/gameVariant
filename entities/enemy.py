"""
Enemy -- sprite animato da GIF, shake + mini-esplosione all'hit, pattern laser.

I 4 tipi di nemico usano sprite animati estratti da ``enemy_ships.gif``:
- scout:   laser singolo veloce, intervallo breve
- fighter: laser doppio (offset laterale), intervallo intermedio
- bomber:  laser lento ma largo, lungo intervallo
- elite:   burst da 3 laser ravvicinati, intervallo medio

Effetto hit (nemici con >1 HP):
- Shake (oscillazione rapida dello sprite)
- Mini-esplosione (``explosion.gif``) al punto d'impatto
"""

import random
import pygame

from core.constants import ENEMY_W, ENEMY_H, RED, ORANGE, YELLOW, CYAN
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
        self._frame_delay = 8  # tick di gioco per frame GIF

    # ------------------------------------------------------------------
    # DANNO
    # ------------------------------------------------------------------

    def take_damage(self, amount: int = 1) -> bool:
        """Applica danno al nemico e attiva shake + mini-esplosione.

        Lo shake e la mini-esplosione vengono attivati **solo** se il
        nemico sopravvive (multi-HP).

        Args:
            amount: Quantita' di danno da applicare.

        Returns:
            ``True`` se il nemico e' stato ucciso, ``False`` altrimenti.
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
        """Restituisce la lista di frame per il tipo di nemico."""
        frames = Assets.enemy_frames.get(self.enemy_type)
        if frames:
            return frames
        # Fallback: scout
        return Assets.enemy_frames.get("scout", [])

    # ------------------------------------------------------------------
    # LASER
    # ------------------------------------------------------------------

    def build_lasers(self) -> list:
        """Costruisce i laser secondo il pattern del tipo di nemico.

        Returns:
            Lista di oggetti ``Laser``.
        """
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
            lasers.append(Laser(cx - 3, by, spd, col, is_enemy=True))
        elif self.enemy_type == "elite":
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
            # Fallback: rettangolo colorato
            pygame.draw.rect(
                surf, RED,
                (int(self.x + offset_x), int(self.y), self.width, self.height))

    # ------------------------------------------------------------------
    # HITBOX
    # ------------------------------------------------------------------

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del nemico, ridotta rispetto allo sprite."""
        sx, sy = 6, 4
        return pygame.Rect(
            self.x + sx,
            self.y + sy,
            self.width - sx * 2,
            self.height - sy * 2,
        )
