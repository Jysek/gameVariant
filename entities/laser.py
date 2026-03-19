"""
Laser and AngledLaser classes -- game projectiles.

Lasers can be fired by the player (upward) or by enemies/bosses (downward).
Sprites are pre-scaled in Assets.load() to avoid expensive per-frame scaling.

Supports horizontal velocity (``vx``) for advanced boss firing patterns.
Enemy lasers use the sprite image oriented downward; no white fallback
rectangles are drawn -- if no sprite is available, a colored glow is used.
"""

import math
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, CYAN
from core.assets import Assets


class Laser:
    """Straight laser projectile (player or enemy).

    Supports optional horizontal velocity for diagonal boss patterns.

    Args:
        x, y:     Initial position (top-left corner).
        speed:    Vertical speed (negative = up, positive = down).
        color:    Fallback color if sprite is unavailable.
        is_enemy: True if this laser belongs to an enemy/boss.
        sprite:   Pre-loaded Pygame Surface (optional).
        vx:       Horizontal velocity (0 = straight). Used for boss patterns.
    """

    WIDTH  = 20
    HEIGHT = 40

    def __init__(
        self, x: float, y: float, speed: float, color: tuple = CYAN,
        is_enemy: bool = False, sprite: pygame.Surface = None,
        vx: float = 0.0,
    ):
        self.x = x
        self.y = y
        self.speed = speed
        self.vx = vx
        self.color = color
        self.is_enemy = is_enemy
        self.active = True

        if sprite:
            self.image = sprite
        elif is_enemy:
            self.image = Assets.enemy_laser_sprite_scaled
        else:
            self.image = None

    def update(self) -> None:
        """Move the laser along its trajectory; deactivate if off-screen."""
        self.y += self.speed
        self.x += self.vx
        margin = 50
        if self.y < -margin or self.y > SCREEN_HEIGHT + margin:
            self.active = False
        if self.x < -margin or self.x > SCREEN_WIDTH + margin:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the laser using its pre-scaled sprite.

        If no sprite is available, draws a colored glow ellipse instead
        of a plain white rectangle (eliminates white hitbox artifacts).
        """
        if self.image:
            surface.blit(self.image, (int(self.x), int(self.y)))
        else:
            # Draw a glowing colored ellipse instead of a white rectangle
            glow_surf = pygame.Surface(
                (self.WIDTH, self.HEIGHT), pygame.SRCALPHA
            )
            r, g, b = self.color[:3]
            # Outer glow
            pygame.draw.ellipse(
                glow_surf, (r, g, b, 80),
                (0, 0, self.WIDTH, self.HEIGHT),
            )
            # Inner bright core
            core_w = max(4, self.WIDTH // 3)
            core_x = (self.WIDTH - core_w) // 2
            pygame.draw.ellipse(
                glow_surf, (r, g, b, 200),
                (core_x, 2, core_w, self.HEIGHT - 4),
            )
            surface.blit(glow_surf, (int(self.x), int(self.y)))

    def get_rect(self) -> pygame.Rect:
        """Return the collision hitbox of this laser.

        The hitbox is slightly narrower than the visual for fairness.
        """
        shrink_x = 4
        return pygame.Rect(
            self.x + shrink_x,
            self.y,
            self.WIDTH - shrink_x * 2,
            self.HEIGHT,
        )


class AngledLaser(Laser):
    """Angled laser used by the triple-shot weapon power-up.

    Moves along a diagonal trajectory defined by the angle.

    Args:
        x, y:       Initial position.
        base_speed: Base laser speed.
        angle_deg:  Angle in degrees from vertical.
        color:      Fallback color.
        sprite:     Pre-loaded surface (optional).
    """

    def __init__(
        self, x: float, y: float, base_speed: float, angle_deg: float,
        color: tuple = CYAN, sprite: pygame.Surface = None,
    ):
        super().__init__(x, y, base_speed, color, is_enemy=False, sprite=sprite)
        rad = math.radians(angle_deg)
        self.vx = -base_speed * math.sin(rad)
        self.vy = base_speed * math.cos(rad)
        self.angle_deg = angle_deg

    def update(self) -> None:
        """Move the laser along its angled trajectory."""
        self.x += self.vx
        self.y += self.vy
        margin = 50
        if self.y < -margin or self.y > SCREEN_HEIGHT + margin:
            self.active = False
        if self.x < -margin or self.x > SCREEN_WIDTH + margin:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the angled laser using its sprite or a colored glow."""
        if self.image:
            surface.blit(self.image, (int(self.x), int(self.y)))
        else:
            # Same glow rendering as parent -- no white rectangles
            glow_surf = pygame.Surface(
                (self.WIDTH, self.HEIGHT), pygame.SRCALPHA
            )
            r, g, b = self.color[:3]
            pygame.draw.ellipse(
                glow_surf, (r, g, b, 80),
                (0, 0, self.WIDTH, self.HEIGHT),
            )
            core_w = max(4, self.WIDTH // 3)
            core_x = (self.WIDTH - core_w) // 2
            pygame.draw.ellipse(
                glow_surf, (r, g, b, 200),
                (core_x, 2, core_w, self.HEIGHT - 4),
            )
            surface.blit(glow_surf, (int(self.x), int(self.y)))
