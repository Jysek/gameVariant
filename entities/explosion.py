"""
Classe Explosion -- effetto esplosione animato tramite GIF.

L'esplosione viene centrata sul punto (x, y) e riproduce tutti i frame
della GIF explosionGif.gif. Al termine dell'animazione si disattiva
automaticamente.
"""

import pygame

from core.constants import EXPLOSION_SIZE
from core.assets import Assets


class Explosion:
    """Effetto esplosione animato tramite la GIF explosionGif.gif.

    Args:
        x, y: Centro dell'esplosione (pixel).
        size: Dimensione in pixel (default EXPLOSION_SIZE = 64).
    """

    def __init__(self, x, y, size=EXPLOSION_SIZE):
        self.x = x
        self.y = y
        self.size = size
        self.active = True

        # Se la dimensione richiesta e' diversa da quella pre-scalata,
        # genera al volo i frame alla taglia corretta.
        if size == EXPLOSION_SIZE:
            self.frames = Assets.explosion_frames
        else:
            self.frames = [
                pygame.transform.scale(f, (size, size))
                for f in Assets.explosion_frames_raw
            ]

        self.frame_index = 0
        self.frame_delay = 2   # tick di gioco per ogni frame GIF
        self.frame_timer = 0

    def update(self):
        """Avanza l'animazione di un tick; disattiva l'esplosione a fine GIF."""
        self.frame_timer += 1
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            self.frame_index += 1
            if self.frame_index >= len(self.frames):
                self.active = False

    def draw(self, surface):
        """Disegna il frame corrente centrato su (x, y).

        Args:
            surface: Surface di destinazione.
        """
        if not self.active:
            return
        frame = self.frames[self.frame_index]
        surface.blit(
            frame,
            (int(self.x - self.size // 2), int(self.y - self.size // 2)),
        )
