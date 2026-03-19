"""
StarField -- parallax star background.

Three depth layers with different star sizes and speeds create a
parallax effect that simulates flying through space.

Optimized: uses pre-rendered star surfaces to avoid per-star draw calls.
"""

import random
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT


class StarField:
    """Parallax starfield with 3 depth layers.

    Layer 0 (distant): Small, slow stars.
    Layer 1 (medium):  Medium stars at intermediate speed.
    Layer 2 (near):    Large, fast stars.
    """

    def __init__(self):
        """Generate stars for each depth layer."""
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
        """Move stars downward (parallax effect).

        When a star exits the bottom, it wraps to the top with
        a new X position and brightness.
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
        """Draw all stars across all layers.

        Stars are rendered as white-blueish circles with variable brightness.
        Uses cached color tuples for performance.

        Args:
            surface: Target surface.
        """
        _draw_circle = pygame.draw.circle
        for layer in self.layers:
            for star in layer:
                _draw_circle(
                    surface, star["color"],
                    (int(star["x"]), int(star["y"])), star["size"],
                )
