"""
PowerUpCarrier and FallingPowerUp classes -- power-up delivery system.

The carrier descends from above, hovers for 5 seconds in the upper half
while moving horizontally. The player must destroy it (3-5 HP) to
release a falling power-up. If not destroyed, it escapes with a
hyperspace dash downward.

Uses proper sprites: Assets/carrier_bomba.png and Assets/powerup_bomba.png
for bomb power-ups.
"""

import random
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CARRIER_SIZE, POWERUP_ITEM_SIZE, POWERUP_TYPES,
    WHITE, GREEN, CYAN, YELLOW, ORANGE, RED,
    POWERUP_COLORS,
)
from core.assets import Assets

# Shake parameters
_CARRIER_SHAKE_DURATION  = 12
_CARRIER_SHAKE_AMPLITUDE = 3


class PowerUpCarrier:
    """Carrier ship that transports a power-up.

    States:
    - DESCENDING: Moving down to hover position.
    - HOVERING:   Moving horizontally, waiting to be destroyed.
    - ESCAPING:   Hyperspace dash downward (not destroyed in time).

    Args:
        powerup_type: Type of power-up carried (random if None).
    """

    STATE_DESCENDING = 0
    STATE_HOVERING   = 1
    STATE_ESCAPING   = 2

    def __init__(self, powerup_type: str | None = None):
        self.width  = CARRIER_SIZE
        self.height = CARRIER_SIZE
        self.x = random.randint(20, SCREEN_WIDTH - self.width - 20)
        self.y = -self.height
        self.alive = True

        self.target_y = SCREEN_HEIGHT // 4
        self.state = PowerUpCarrier.STATE_DESCENDING
        self.descent_speed = 2.5

        # Power-up type (uses proper sprites from Assets)
        self.powerup_type = powerup_type or random.choice(POWERUP_TYPES)
        self.image = Assets.carrier_sprites[self.powerup_type]

        # Hit points
        self.max_hp = random.randint(3, 5)
        self.hp = self.max_hp

        # Horizontal movement
        self.h_speed            = random.choice([-2.0, -1.5, -1.0, 1.0, 1.5, 2.0])
        self.h_direction_timer  = 0
        self.h_change_interval  = random.randint(60, 180)

        # Hover duration (5 seconds at 60 FPS)
        self.hover_timer = 5 * 60

        # Hyperspace escape
        self.escape_speed        = 0
        self.escape_acceleration = 1.5
        self.hit_flash = 0
        self.trail_particles: list[dict] = []

        # Shake effect
        self._shake_timer    = 0
        self._shake_offset_x = 0
        self._shake_offset_y = 0

        # HUD font (created once)
        self._hud_font = pygame.font.Font(None, 18)

    def update(self) -> None:
        """Update the carrier based on its current state."""
        if not self.alive:
            return

        # Update shake
        if self._shake_timer > 0:
            ratio = self._shake_timer / _CARRIER_SHAKE_DURATION
            amp = int(_CARRIER_SHAKE_AMPLITUDE * ratio)
            self._shake_offset_x = random.randint(-amp, amp)
            self._shake_offset_y = random.randint(-amp // 2, amp // 2)
            self._shake_timer -= 1
        else:
            self._shake_offset_x = 0
            self._shake_offset_y = 0

        if self.hit_flash > 0:
            self.hit_flash -= 1

        if self.state == PowerUpCarrier.STATE_DESCENDING:
            self._update_descending()
        elif self.state == PowerUpCarrier.STATE_HOVERING:
            self._update_hovering()
        elif self.state == PowerUpCarrier.STATE_ESCAPING:
            self._update_escaping()

    def _update_descending(self) -> None:
        """Move down to the target hover position."""
        self.y += self.descent_speed
        if self.y >= self.target_y:
            self.y = self.target_y
            self.state = PowerUpCarrier.STATE_HOVERING

    def _update_hovering(self) -> None:
        """Move horizontally and count down the hover timer."""
        self.x += self.h_speed
        self.h_direction_timer += 1
        if self.h_direction_timer >= self.h_change_interval:
            self.h_speed = random.choice([-2.0, -1.5, -1.0, 1.0, 1.5, 2.0])
            self.h_direction_timer = 0
            self.h_change_interval = random.randint(60, 180)

        # Bounce off screen edges
        if self.x < 10:
            self.x = 10
            self.h_speed = abs(self.h_speed)
        elif self.x > SCREEN_WIDTH - self.width - 10:
            self.x = SCREEN_WIDTH - self.width - 10
            self.h_speed = -abs(self.h_speed)

        self.hover_timer -= 1
        if self.hover_timer <= 0:
            self.state = PowerUpCarrier.STATE_ESCAPING
            self.escape_speed = 3

    def _update_escaping(self) -> None:
        """Accelerate downward in hyperspace escape mode."""
        self.escape_speed += self.escape_acceleration
        self.y += self.escape_speed

        # Generate trail particles
        if random.random() < 0.6:
            self.trail_particles.append({
                "x": self.x + self.width // 2 + random.randint(-10, 10),
                "y": self.y,
                "alpha": 200,
                "size": random.randint(2, 5),
            })

        for p in self.trail_particles:
            p["alpha"] -= 12
            p["size"] = max(0, p["size"] - 0.1)
        self.trail_particles = [p for p in self.trail_particles if p["alpha"] > 0]

        if self.y > SCREEN_HEIGHT + 50:
            self.alive = False

    def take_damage(self, amount: int = 1) -> bool:
        """Apply damage to the carrier with shake effect.

        The mini-explosion is handled by the caller (game.py) which
        has access to the explosions list.

        Args:
            amount: Damage amount.

        Returns:
            True if the carrier has been destroyed.
        """
        self.hp -= amount
        self._shake_timer = _CARRIER_SHAKE_DURATION

        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the carrier with all visual effects.

        Args:
            surface: Target surface.
        """
        if not self.alive:
            return

        # Hyperspace trail
        if self.state == PowerUpCarrier.STATE_ESCAPING:
            self._draw_trail(surface)

        draw_x = int(self.x + self._shake_offset_x)
        draw_y = int(self.y + self._shake_offset_y)

        # Vertical stretch during escape (only case needing transform)
        if self.state == PowerUpCarrier.STATE_ESCAPING:
            stretch_h = min(
                self.height + int(self.escape_speed * 2),
                self.height * 3)
            draw_img = pygame.transform.scale(self.image, (self.width, stretch_h))
            surface.blit(draw_img, (draw_x, draw_y))
        else:
            surface.blit(self.image, (draw_x, draw_y))

        # HUD overlay (type label, HP bar, timer)
        if self.state != PowerUpCarrier.STATE_ESCAPING:
            self._draw_carrier_hud(surface)

    def _draw_trail(self, surface: pygame.Surface) -> None:
        """Draw escape trail particles using direct circle drawing.

        Uses pygame.draw.circle directly instead of creating a Surface
        per particle for better performance.

        Args:
            surface: Target surface.
        """
        for p in self.trail_particles:
            size = int(p["size"])
            if size <= 0:
                continue
            alpha = int(p["alpha"])
            if alpha < 20:
                continue
            factor = alpha / 255.0
            cr = min(255, int(100 * factor))
            cg = min(255, int(180 * factor))
            cb = min(255, int(255 * factor))
            pygame.draw.circle(
                surface, (cr, cg, cb),
                (int(p["x"]), int(p["y"])), size)

    def _draw_carrier_hud(self, surface: pygame.Surface) -> None:
        """Draw the carrier's HUD: type label, HP bar, and timer bar.

        Args:
            surface: Target surface.
        """
        color = POWERUP_COLORS.get(self.powerup_type, WHITE)

        label = self._hud_font.render(self.powerup_type.upper(), True, color)
        label_x = self.x + self.width // 2 - label.get_width() // 2
        surface.blit(label, (int(label_x), int(self.y - 14)))

        # HP bar
        bar_w = self.width
        bar_y = self.y + self.height + 2
        hp_pct = self.hp / self.max_hp
        pygame.draw.rect(surface, (60, 60, 60), (int(self.x), int(bar_y), bar_w, 4))
        pygame.draw.rect(surface, color, (int(self.x), int(bar_y), int(bar_w * hp_pct), 4))

        # Timer countdown bar
        if self.state == PowerUpCarrier.STATE_HOVERING:
            timer_bar_y = self.y + self.height + 8
            timer_pct = self.hover_timer / (5 * 60)
            if timer_pct > 0.5:
                timer_color = GREEN
            elif timer_pct > 0.25:
                timer_color = YELLOW
            else:
                timer_color = RED
            pygame.draw.rect(
                surface, (40, 40, 40),
                (int(self.x), int(timer_bar_y), bar_w, 3))
            pygame.draw.rect(
                surface, timer_color,
                (int(self.x), int(timer_bar_y), int(bar_w * timer_pct), 3))

    def get_rect(self) -> pygame.Rect:
        """Return the carrier's collision hitbox (slightly shrunken)."""
        shrink = 5
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width - shrink * 2,
            self.height - shrink * 2,
        )


class FallingPowerUp:
    """Power-up item that falls after a carrier is destroyed.

    Uses the proper sprite from Assets (including powerup_bomba.png for bombs).

    Args:
        x, y:         Initial position.
        powerup_type: Type of power-up.
    """

    def __init__(self, x: float, y: float, powerup_type: str):
        self.width  = POWERUP_ITEM_SIZE
        self.height = POWERUP_ITEM_SIZE
        self.x = x
        self.y = y
        self.powerup_type = powerup_type
        self.image = Assets.powerup_sprites[self.powerup_type]
        self.active = True
        self.fall_speed = 2.5
        self.pulse_timer = 0.0

    def update(self) -> None:
        """Update the power-up: falls straight down."""
        if not self.active:
            return
        self.y += self.fall_speed
        self.pulse_timer += 0.1
        if self.y > SCREEN_HEIGHT + 20:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Draw the power-up sprite (no glow effect).

        Args:
            surface: Target surface.
        """
        if not self.active:
            return

        self.pulse_timer += 0  # keep timer alive for potential future use
        surface.blit(self.image, (int(self.x), int(self.y)))

    def get_rect(self) -> pygame.Rect:
        """Return the power-up's collision hitbox."""
        return pygame.Rect(self.x, self.y, self.width, self.height)
