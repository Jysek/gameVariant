"""
Nemico -- sprite GIF animato con shake + mini-esplosione al colpo.

I 4 tipi di nemici usano sprite animati estratti da ``enemy_ships.gif``:
- scout:   Laser singolo veloce, HP 1, score 1
- fighter: Doppio laser sfalsato, HP 2, score 3
- bomber:  Lento ma pesante triplo laser, HP 4, score 5
- elite:   Burst rapido di 3 laser, HP 3, score 8

Tutti i laser nemici viaggiano VERSO IL BASSO dato che il PNG del laser
punta verso il basso.
"""

import random
import pygame

from core.constants import (
    ENEMY_W, ENEMY_H, RED, ORANGE, CYAN, ENEMY_TYPE_STATS,
    ENEMY_SHOOT_INTERVALS,
)
from core.assets import Assets
from entities.formations import Slot

# ---------------------------------------------------------------------------
# Parametri shake al colpo (basati su frame)
# ---------------------------------------------------------------------------
_SHAKE_DURATION  = 8
_SHAKE_AMPLITUDE = 3

# ---------------------------------------------------------------------------
# Colore laser per tipo nemico
# ---------------------------------------------------------------------------
_LASER_COLOR: dict[str, tuple] = {
    "scout":   RED,
    "fighter": ORANGE,
    "bomber":  (180, 0, 220),
    "elite":   CYAN,
}

# Velocità laser per tipo (pixel/frame) -- tutti positivi = verso il basso
_LASER_SPEED: dict[str, int] = {
    "scout":   6,
    "fighter": 5,
    "bomber":  3,
    "elite":   5,
}


class Enemy:
    """Singolo nemico alieno con tipo, HP, sprite animato e pattern di sparo.

    Args:
        x, y:       Posizione iniziale.
        enemy_type: Stringa tipo nemico.
        hp:         Punti vita iniziali.
    """

    def __init__(self, x: float, y: float, enemy_type: str = "scout",
                 hp: int = 1):
        self.width  = ENEMY_W
        self.height = ENEMY_H
        self.x = x
        self.y = y
        self.alive = True

        self.enemy_type = enemy_type
        self.hp     = hp
        self.max_hp = hp

        self.h_speed = 0.0

        # Timer e intervallo di sparo individuale
        lo, hi = ENEMY_SHOOT_INTERVALS.get(enemy_type, (100, 200))
        self.shoot_timer    = random.randint(0, hi)
        self.shoot_interval = random.randint(lo, hi)

        # Slot logico nella griglia di formazione
        self.slot: Slot = Slot(0, 0)

        # Timer shake al colpo
        self._shake_timer = 0

        # Stato animazione GIF
        self._frame_idx   = 0
        self._frame_timer = 0
        self._frame_delay = 8

    # ------------------------------------------------------------------
    # DANNO
    # ------------------------------------------------------------------

    def take_damage(self, amount: int = 1) -> bool:
        """Applica danno e attiva l'effetto shake al colpo.

        Args:
            amount: Quantità di danno.

        Returns:
            True se il nemico è stato ucciso.
        """
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True

        # Il nemico è sopravvissuto: attiva shake
        self._shake_timer = _SHAKE_DURATION
        return False

    # ------------------------------------------------------------------
    # SPRITE ANIMATO
    # ------------------------------------------------------------------

    def _get_frames(self) -> list[pygame.Surface]:
        """Restituisce i frame di animazione per questo tipo di nemico."""
        frames = Assets.enemy_frames.get(self.enemy_type)
        if frames:
            return frames
        return Assets.enemy_frames.get("scout", [])

    # ------------------------------------------------------------------
    # GENERAZIONE LASER
    # ------------------------------------------------------------------

    def build_lasers(self) -> list:
        """Costruisce i laser secondo il pattern di sparo del tipo nemico.

        Tutti i laser viaggiano VERSO IL BASSO (velocità positiva) in
        accordo con lo sprite laser PNG orientato verso il basso.

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
            # Laser singolo veloce
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))
        elif self.enemy_type == "fighter":
            # Doppio laser parallelo
            lasers.append(Laser(cx - 10, by, spd, col, is_enemy=True))
            lasers.append(Laser(cx + 8,  by, spd, col, is_enemy=True))
        elif self.enemy_type == "bomber":
            # Triplo laser lento parallelo
            lasers.append(Laser(cx - 8, by, spd, col, is_enemy=True))
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))
            lasers.append(Laser(cx + 4, by, spd, col, is_enemy=True))
        elif self.enemy_type == "elite":
            # Burst di 3 laser rapidi a leggero sfalsamento
            for dy in [0, 6, 12]:
                lasers.append(Laser(cx - 2, by + dy, spd, col, is_enemy=True))
        else:
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))

        return lasers

    # ------------------------------------------------------------------
    # DISEGNO
    # ------------------------------------------------------------------

    def draw(self, surf: pygame.Surface) -> None:
        """Disegna lo sprite nemico animato con effetto shake opzionale.

        Args:
            surf: Surface di destinazione.
        """
        if not self.alive:
            return

        # Avanza animazione
        self._frame_timer += 1
        if self._frame_timer >= self._frame_delay:
            self._frame_timer = 0
            frames = self._get_frames()
            if frames:
                self._frame_idx = (self._frame_idx + 1) % len(frames)

        # Calcola offset shake
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
            # Fallback: rettangolo colorato (non dovrebbe mai accadere)
            pygame.draw.rect(
                surf, RED,
                (int(self.x + offset_x), int(self.y),
                 self.width, self.height))

        # Barra HP per nemici multi-HP
        if self.max_hp > 1 and self.hp > 0:
            self._draw_hp_bar(surf)

    def _draw_hp_bar(self, surf: pygame.Surface) -> None:
        """Disegna una piccola barra HP sopra il nemico.

        Args:
            surf: Surface di destinazione.
        """
        bar_w = self.width - 10
        bar_h = 3
        bar_x = self.x + 5
        bar_y = self.y - 5

        pct = self.hp / self.max_hp
        pygame.draw.rect(
            surf, (40, 40, 40),
            (int(bar_x), int(bar_y), bar_w, bar_h))

        if pct > 0.5:
            col = (50, 255, 50)
        elif pct > 0.25:
            col = (255, 255, 50)
        else:
            col = (255, 50, 50)
        pygame.draw.rect(
            surf, col,
            (int(bar_x), int(bar_y), int(bar_w * pct), bar_h))

    # ------------------------------------------------------------------
    # HITBOX
    # ------------------------------------------------------------------

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox di collisione (leggermente ridotta per equità)."""
        sx, sy = 6, 4
        return pygame.Rect(
            self.x + sx,
            self.y + sy,
            self.width - sx * 2,
            self.height - sy * 2,
        )
