"""
Classe StarField -- campo stellare parallax per lo sfondo.

Tre livelli di profondita' con stelle di dimensione e velocita' diverse
creano un effetto parallax che simula il movimento nello spazio.
"""

import random
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT


class StarField:
    """Campo di stelle parallax a 3 livelli di profondita'.

    Livello 0 (lontano): stelle piccole e lente.
    Livello 1 (medio):   stelle medie a velocita' intermedia.
    Livello 2 (vicino):  stelle grandi e veloci.
    """

    def __init__(self):
        """Genera le stelle per ciascun livello di profondita'."""
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
        """Muove le stelle verso il basso (effetto parallax).

        Quando una stella esce dal fondo dello schermo, viene
        riposizionata in cima con nuova posizione X e luminosita'.
        """
        for layer in self.layers:
            for star in layer:
                star["y"] += star["speed"]
                if star["y"] > SCREEN_HEIGHT:
                    star["y"] = 0
                    star["x"] = random.randint(0, SCREEN_WIDTH)
                    star["brightness"] = random.randint(100, 255)

    def draw(self, surface):
        """Disegna tutte le stelle su tutti i livelli.

        Il colore e' bianco-bluastro, con luminosita' variabile.

        Args:
            surface: Surface di destinazione.
        """
        for layer in self.layers:
            for star in layer:
                b = star["brightness"]
                color = (b, b, min(255, b + 20))
                pygame.draw.circle(
                    surface, color,
                    (int(star["x"]), int(star["y"])), star["size"],
                )
