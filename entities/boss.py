"""
Boss -- 4 variants with GIF animation, unique laser patterns, progressive scaling.

Variants (random spawn with equal probability):
- Boss 0 (Titano):    Alternating cannon volleys (straight, converge, diverge).
- Boss 1 (Furia):     Double cannon shots with delayed burst follow-up.
- Boss 2 (Ventaglio): Symmetric 5-laser fan with alternating offset.
- Boss 3 (Vortice):   3 rotating arms at constant speed (predictable spiral).

All laser patterns are designed to be simple, functional, and fair:
- All projectiles travel primarily DOWNWARD (positive vy).
- Patterns are predictable enough to learn and dodge.
- No random aiming at the player -- purely geometric patterns.
"""

import math
import random
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, RED, GREEN, YELLOW, ORANGE,
    CYAN, MAGENTA, GOLD, NUM_BOSS_VARIANTS, BOSS_NAMES,
)
from core.assets import Assets
from entities.laser import Laser


class Boss:
    """Boss entity with GIF animation, unique laser patterns, and health bar.

    Each boss variant has a distinct attack pattern, making every encounter
    feel different. All projectiles travel primarily downward so the
    laser sprite (pointing down) renders correctly.

    Args:
        variant: Boss variant index (0-3).
    """

    def __init__(self, variant: int = 0):
        self.variant = variant % NUM_BOSS_VARIANTS
        self.width  = 200
        self.height = 94
        self.x = float(SCREEN_WIDTH // 2 - self.width // 2)
        self.y = float(-self.height)

        self.target_y = 30
        self.entering = True
        self.alive = True

        # Stats (may be overridden by game.py for scaling)
        self.max_hp = 60
        self.hp     = self.max_hp

        # Horizontal movement
        self.h_speed        = random.choice([-2.5, -2.0, -1.5, 1.5, 2.0, 2.5])
        self.h_dir_timer    = 0
        self.h_dir_interval = random.randint(120, 300)

        # GIF animation
        self.frames      = Assets.boss_variant_frames[self.variant]
        self.frame_idx   = 0
        self.frame_timer = 0
        self.frame_delay = 6

        # Cannon positions (percentages relative to width/height)
        self.cannon_offsets = [
            (0.12, 0.85),
            (0.38, 0.95),
            (0.62, 0.95),
            (0.88, 0.85),
        ]

        # Primary fire timer
        self.shoot_timer    = 0
        self.shoot_interval = 40

        # Hit flash visual effect
        self.hit_flash     = 0
        self.hit_flash_max = 8

        # Titano: cannon rotation sub-pattern index
        self._titano_rotation = 0

        # Furia: burst state
        self._burst_count = 0
        self._burst_delay = 0

        # Ventaglio: alternating direction and wave counter
        self._fan_direction = 1
        self._fan_wave = 0

        # Vortice: spiral angle and acceleration
        self._spiral_angle = 0.0
        self._spiral_speed = 0.4
        self._spiral_accel = 0.01

        # Health bar font
        self._hp_font = pygame.font.Font(None, 22)

        # Cached scaled sprite for performance
        self._cached_scaled: pygame.Surface | None = None
        self._cached_w = 0
        self._cached_h = 0

    @staticmethod
    def random_variant() -> int:
        """Choose a random boss variant with equal probability (0-3)."""
        return random.randint(0, NUM_BOSS_VARIANTS - 1)

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(self) -> list[Laser]:
        """Update the boss: movement, animation, and fire patterns.

        Returns:
            List of newly fired ``Laser`` objects (may be empty).
        """
        if not self.alive:
            return []

        # Entry phase: slide down from top
        if self.entering:
            self.y += 1.5
            if self.y >= self.target_y:
                self.y = float(self.target_y)
                self.entering = False
            return []

        # Horizontal movement with direction changes
        self.x += self.h_speed
        self.h_dir_timer += 1
        if self.h_dir_timer >= self.h_dir_interval:
            self.h_speed = random.choice([-2.5, -2.0, -1.5, 1.5, 2.0, 2.5])
            self.h_dir_timer = 0
            self.h_dir_interval = random.randint(120, 300)

        # Bounce off screen edges
        if self.x <= 10:
            self.x = 10.0
            self.h_speed = abs(self.h_speed)
        elif self.x >= SCREEN_WIDTH - self.width - 10:
            self.x = float(SCREEN_WIDTH - self.width - 10)
            self.h_speed = -abs(self.h_speed)

        # Advance GIF animation
        self.frame_timer += 1
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            if self.frames:
                self.frame_idx = (self.frame_idx + 1) % len(self.frames)
                self._cached_scaled = None

        # Decay hit flash
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # Primary fire on interval
        self.shoot_timer += 1
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            return self._fire()

        # Secondary/continuous pattern effects
        return self._fire_secondary()

    # ------------------------------------------------------------------
    # FIRE PATTERN DISPATCH
    # ------------------------------------------------------------------

    def _fire(self) -> list[Laser]:
        """Execute the primary fire pattern based on boss variant."""
        if self.variant == 0:
            return self._fire_titano()
        elif self.variant == 1:
            return self._fire_furia()
        elif self.variant == 2:
            return self._fire_ventaglio()
        elif self.variant == 3:
            return self._fire_vortice()
        return self._fire_titano()

    def _fire_secondary(self) -> list[Laser]:
        """Handle secondary fire patterns that operate between main shots.

        Only Furia uses a secondary burst between primary volleys.

        Returns:
            List of additional lasers (may be empty).
        """
        lasers: list[Laser] = []

        # Furia: follow-up burst shots between primary volleys
        if self.variant == 1 and self._burst_delay > 0:
            self._burst_delay -= 1
            if self._burst_delay == 0 and self._burst_count > 0:
                self._burst_count -= 1
                self._burst_delay = 10
                cx = self.x + self.width // 2
                cy = self.y + self.height
                lasers.append(Laser(cx - 2, cy, 6, CYAN, is_enemy=True))
                if self._burst_count <= 0:
                    self._burst_delay = 0

        return lasers

    def _cannon_pos(self, idx: int) -> tuple[float, float]:
        """Calculate the absolute position of a cannon.

        Args:
            idx: Cannon index (0-3).

        Returns:
            Tuple (x, y) of the cannon's screen position.
        """
        ox, oy = self.cannon_offsets[idx]
        return (
            self.x + int(self.width * ox) - 2,
            self.y + int(self.height * oy),
        )

    # ------------------------------------------------------------------
    # TITANO (Boss 0): Alternating cannon volleys
    # ------------------------------------------------------------------

    def _fire_titano(self) -> list[Laser]:
        """Titano cycles through 3 simple cannon patterns.

        Pattern 0: All 4 cannons fire straight down.
        Pattern 1: Outer cannons fire with slight inward angle.
        Pattern 2: Inner cannons fire with slight outward angle.

        All shots move primarily downward with predictable trajectories.
        """
        lasers: list[Laser] = []
        self._titano_rotation = (self._titano_rotation + 1) % 3

        if self._titano_rotation == 0:
            # All 4 cannons fire straight down
            for i in range(4):
                cx, cy = self._cannon_pos(i)
                lasers.append(Laser(cx, cy, 5, ORANGE, is_enemy=True))

        elif self._titano_rotation == 1:
            # Outer cannons converge slightly inward
            for i in [0, 3]:
                cx, cy = self._cannon_pos(i)
                vx = 1.2 if i == 0 else -1.2
                lasers.append(Laser(cx, cy, 5, RED, is_enemy=True, vx=vx))

        else:
            # Inner cannons diverge slightly outward
            for i in [1, 2]:
                cx, cy = self._cannon_pos(i)
                vx = -1.0 if i == 1 else 1.0
                lasers.append(Laser(cx, cy, 5, YELLOW, is_enemy=True, vx=vx))

        return lasers

    # ------------------------------------------------------------------
    # FURIA (Boss 1): Double cannon burst
    # ------------------------------------------------------------------

    def _fire_furia(self) -> list[Laser]:
        """Furia fires from both lateral cannons then triggers a follow-up burst.

        Primary: 1 laser from each outer cannon straight down.
        Secondary: 2 follow-up shots from the center after a short delay.

        Simple and predictable but the burst keeps pressure on the player.
        """
        lasers: list[Laser] = []
        # Fire from outer cannons
        for i in [0, 3]:
            cx, cy = self._cannon_pos(i)
            lasers.append(Laser(cx, cy, 5.5, CYAN, is_enemy=True))

        # Activate a small follow-up burst (2 shots from center)
        self._burst_count = 2
        self._burst_delay = 10
        return lasers

    # ------------------------------------------------------------------
    # VENTAGLIO (Boss 2): Fixed-angle fan
    # ------------------------------------------------------------------

    def _fire_ventaglio(self) -> list[Laser]:
        """Ventaglio fires a symmetric fan of 5 lasers from center.

        Lasers spread evenly across a fixed 60-degree arc.
        The fan alternates leaning left or right by a small offset.
        All shots have strong downward velocity (vy >= 4).
        """
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        n_rays = 5
        spread = 30  # degrees from center (total arc = 60 degrees)
        # Small alternating offset to vary the pattern slightly
        offset = self._fan_direction * 5

        for i in range(n_rays):
            angle_deg = offset + (-spread + (2 * spread / (n_rays - 1)) * i)
            rad = math.radians(angle_deg)
            vx = math.sin(rad) * 4.0
            vy = max(4.0, math.cos(rad) * 5.0)
            lasers.append(
                Laser(center_x - 2, center_y, vy, MAGENTA, is_enemy=True, vx=vx)
            )

        self._fan_direction *= -1
        return lasers

    # ------------------------------------------------------------------
    # VORTICE (Boss 3): Steady rotating arms
    # ------------------------------------------------------------------

    def _fire_vortice(self) -> list[Laser]:
        """Vortice fires 3 rotating arms at fixed rotation speed.

        Each arm is offset by 120 degrees. The rotation advances by
        a constant amount each shot, producing a predictable spiral
        the player can learn to weave through. All shots travel downward.
        """
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        n_arms = 3
        for arm in range(n_arms):
            offset = (2 * math.pi / n_arms) * arm
            angle = self._spiral_angle + offset
            vx = math.sin(angle) * 2.5
            vy = max(3.5, abs(math.cos(angle)) * 4.0 + 2.0)
            lasers.append(
                Laser(center_x - 2, center_y, vy, GREEN, is_enemy=True, vx=vx)
            )

        # Constant rotation speed -- predictable and learnable
        self._spiral_angle += 0.5

        return lasers

    # ------------------------------------------------------------------
    # DAMAGE
    # ------------------------------------------------------------------

    def take_damage(self, amount: int = 1) -> bool:
        """Apply damage to the boss and trigger the hit flash.

        Args:
            amount: Damage amount.

        Returns:
            True if the boss has been defeated (hp <= 0).
        """
        self.hp -= amount
        self.hit_flash = self.hit_flash_max
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    # ------------------------------------------------------------------
    # DRAW
    # ------------------------------------------------------------------

    def draw(self, surf: pygame.Surface) -> None:
        """Draw the boss with a pulsation effect on hit.

        Args:
            surf: Target surface.
        """
        if not self.alive or not self.frames:
            return

        frame = self.frames[self.frame_idx % len(self.frames)]

        if self.hit_flash > 0:
            ratio = self.hit_flash / self.hit_flash_max
            pulse = int(4 * ratio)
            w2 = self.width + pulse * 2
            h2 = self.height + pulse * 2
            scaled = pygame.transform.scale(frame, (w2, h2))
            surf.blit(scaled, (int(self.x) - pulse, int(self.y) - pulse))
            self._cached_scaled = None
        else:
            if (self._cached_scaled is None
                    or self._cached_w != self.width
                    or self._cached_h != self.height):
                self._cached_scaled = pygame.transform.scale(
                    frame, (self.width, self.height))
                self._cached_w = self.width
                self._cached_h = self.height
            surf.blit(self._cached_scaled, (int(self.x), int(self.y)))

    def draw_health_bar(self, surf: pygame.Surface) -> None:
        """Draw the boss health bar at the top of the screen.

        Color transitions from green -> yellow -> red as HP drops.

        Args:
            surf: Target surface.
        """
        if not self.alive:
            return

        bw, bh = 400, 18
        bx = SCREEN_WIDTH // 2 - bw // 2
        by = 8

        # Background
        pygame.draw.rect(surf, (12, 12, 18), (bx - 1, by - 1, bw + 2, bh + 2))
        pygame.draw.rect(surf, (40, 40, 55), (bx, by, bw, bh))

        # Health fill
        pct = self.hp / self.max_hp
        if pct > 0.5:
            col = GREEN
        elif pct > 0.25:
            col = YELLOW
        else:
            col = RED

        fw = int(bw * pct)
        if fw > 0:
            pygame.draw.rect(surf, col, (bx, by, fw, bh))

        # Separator marks at 25% intervals
        for s in range(1, 4):
            sx = bx + bw * s // 4
            pygame.draw.line(surf, (12, 12, 18), (sx, by), (sx, by + bh), 1)

        # Boss name label
        vname = BOSS_NAMES[self.variant] if self.variant < len(BOSS_NAMES) else "BOSS"
        label = self._hp_font.render(f"{vname}  {self.hp}/{self.max_hp}", True, WHITE)
        surf.blit(label, (bx + bw // 2 - label.get_width() // 2, by + 1))

    def get_rect(self) -> pygame.Rect:
        """Return the collision hitbox of the boss (slightly shrunken)."""
        return pygame.Rect(
            self.x + 15,
            self.y + 10,
            self.width - 30,
            self.height - 15,
        )
