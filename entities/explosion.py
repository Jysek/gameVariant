"""
Esplosione -- effetto esplosione animato da GIF.

L'esplosione è centrata su (x, y) e riproduce tutti i frame di
explosionGif.gif. Si disattiva automaticamente dopo l'ultimo frame.
"""

import pygame

from core.constants import EXPLOSION_SIZE
from core.assets import Assets


class Explosion:
    """Effetto esplosione animato usando i frame di explosionGif.gif.

    Args:
        x, y: Centro dell'esplosione (pixel).
        size: Dimensione in pixel (default EXPLOSION_SIZE = 64).
    """

    def __init__(self, x: float, y: float, size: int = EXPLOSION_SIZE):
        self.x = x
        self.y = y
        self.size = size
        self.active = True

        # Usa frame pre-scalati se la dimensione corrisponde, altrimenti scala al volo
        if size == EXPLOSION_SIZE:
            self.frames = Assets.explosion_frames
        else:
            self.frames = [
                pygame.transform.scale(f, (size, size))
                for f in Assets.explosion_frames_raw
            ]

        self.frame_index = 0
        self.frame_delay = 2  # tick di gioco per frame GIF
        self.frame_timer = 0

    def update(self) -> None:
        """Avanza l'animazione di un tick; disattiva alla fine."""
        self.frame_timer += 1
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index += 1
            if self.frame_index >= len(self.frames):
                self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna il frame corrente centrato su (x, y).

        Args:
            surface: Surface di destinazione.
        """
        if not self.active or self.frame_index >= len(self.frames):
            return
        frame = self.frames[self.frame_index]
        surface.blit(
            frame,
            (int(self.x - self.size // 2), int(self.y - self.size // 2)),
        )
