"""
Classe StarField - campo stellare parallax per lo sfondo.
"""

import random
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT


class StarField:
    """Campo di stelle parallax a 3 livelli di profondita'."""

    def __init__(self):
        self.layers = []
        for speed, count, size in [(0.3, 50, 1), (0.7, 30, 2), (1.2, 15, 3)]:
            stars = []
            for _ in range(count):
                stars.append({
                    "x": random.randint(0, SCREEN_WIDTH),
                    "y": random.randint(0, SCREEN_HEIGHT),
                    "speed": speed,
                    "size": size,
                    "brightness": random.randint(100, 255),
                })
            self.layers.append(stars)

    def update(self):
        """Muove le stelle verso il basso (effetto parallax)."""
        for layer in self.layers:
            for star in layer:
                star["y"] += star["speed"]
                if star["y"] > SCREEN_HEIGHT:
                    star["y"] = 0
                    star["x"] = random.randint(0, SCREEN_WIDTH)
                    star["brightness"] = random.randint(100, 255)

    def draw(self, surface):
        """Disegna tutte le stelle su tutti i livelli."""
        for layer in self.layers:
            for star in layer:
                b = star["brightness"]
                color = (b, b, min(255, b + 20))
                pygame.draw.circle(
                    surface, color,
                    (int(star["x"]), int(star["y"])), star["size"],
                )
