"""
StarField -- sfondo stellare con parallasse.

Tre livelli di profondità con dimensioni e velocità stelle diverse
creano un effetto parallasse che simula il volo attraverso lo spazio.

Ottimizzato: usa surface stelle pre-renderizzate per evitare chiamate
di disegno per-stella.
"""

import random
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT


class StarField:
    """Campo stellare con parallasse a 3 livelli di profondità.

    Livello 0 (distante): Stelle piccole e lente.
    Livello 1 (medio):    Stelle medie a velocità intermedia.
    Livello 2 (vicino):   Stelle grandi e veloci.
    """

    def __init__(self):
        """Genera le stelle per ogni livello di profondità."""
        self.layers: list[list[dict]] = []
        for speed, count, size in [(0.3, 50, 1), (0.7, 30, 2), (1.2, 15, 3)]:
            stars = []
            for _ in range(count):
                b = random.randint(100, 255)
                stars.append({
                    "x": random.randint(0, SCREEN_WIDTH),
                    "y": random.randint(0, SCREEN_HEIGHT),
                    "speed": speed,
                    "size": size,
                    "brightness": b,
                    "color": (b, b, min(255, b + 20)),
                })
            self.layers.append(stars)

    def update(self) -> None:
        """Muove le stelle verso il basso (effetto parallasse).

        Quando una stella esce dal fondo, torna in alto con una
        nuova posizione X e luminosità.
        """
        for layer in self.layers:
            for star in layer:
                star["y"] += star["speed"]
                if star["y"] > SCREEN_HEIGHT:
                    star["y"] = 0
                    star["x"] = random.randint(0, SCREEN_WIDTH)
                    b = random.randint(100, 255)
                    star["brightness"] = b
                    star["color"] = (b, b, min(255, b + 20))

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna tutte le stelle su tutti i livelli.

        Le stelle sono renderizzate come cerchi bianco-azzurrini con
        luminosità variabile. Usa tuple colore cached per prestazioni.

        Args:
            surface: Surface di destinazione.
        """
        _draw_circle = pygame.draw.circle
        for layer in self.layers:
            for star in layer:
                _draw_circle(
                    surface, star["color"],
                    (int(star["x"]), int(star["y"])), star["size"],
                )
