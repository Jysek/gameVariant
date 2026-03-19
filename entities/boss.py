"""
Boss -- 4 variants with GIF animation, unique laser patterns, progressive scaling.

Variants (random spawn with equal probability):
- Boss 0 (Titano):    Classic, 4 cannons with rotating sub-patterns.
- Boss 1 (Furia):     Burst, rapid-fire volleys from lateral cannons.
- Boss 2 (Ventaglio): Fan, alternating fan waves of lasers.
- Boss 3 (Vortice):   Spiral, rotating spiral arms that accelerate.

Boss_4 (Devastatore) has been removed.

All laser patterns ensure projectiles travel DOWNWARD (positive vy)
since the enemy laser PNG sprite points downward. Patterns are designed
to be challenging but fair -- the player can always dodge them.
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

        Returns:
            List of additional lasers (may be empty).
        """
        lasers: list[Laser] = []

        # Furia: rapid burst between main shots
        if self.variant == 1 and self._burst_delay > 0:
            self._burst_delay -= 1
            if self._burst_delay == 0 and self._burst_count > 0:
                self._burst_count -= 1
                self._burst_delay = 8
                cx, cy = self._cannon_pos(random.choice([0, 3]))
                # Burst shots go straight down
                lasers.append(Laser(cx, cy, 7, CYAN, is_enemy=True))
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
    # TITANO (Boss 0): Classic rotating cannon patterns
    # ------------------------------------------------------------------

    def _fire_titano(self) -> list[Laser]:
        """Titano fires 4 rotating sub-patterns from its 4 cannons.

        Sub-patterns cycle through:
        0: All 4 cannons fire straight down.
        1: Outer cannons fire converging shots toward screen center.
        2: Inner cannons fire slightly diverging shots.
        3: All cannons fire at a random target X position.

        All shots move primarily downward (vy > 0) with small vx offsets.
        """
        lasers: list[Laser] = []
        self._titano_rotation = (self._titano_rotation + 1) % 4

        if self._titano_rotation == 0:
            # All 4 cannons fire straight down
            for i in range(4):
                cx, cy = self._cannon_pos(i)
                lasers.append(Laser(cx, cy, 5, ORANGE, is_enemy=True))

        elif self._titano_rotation == 1:
            # Outer cannons: converging shots toward center
            center_x = self.x + self.width // 2
            for i in [0, 3]:
                cx, cy = self._cannon_pos(i)
                dx = (center_x - cx) * 0.03
                lasers.append(Laser(cx, cy, 5, RED, is_enemy=True, vx=dx))

        elif self._titano_rotation == 2:
            # Inner cannons: slightly diverging shots
            for i in [1, 2]:
                cx, cy = self._cannon_pos(i)
                vx = -1.5 if i == 1 else 1.5
                lasers.append(Laser(cx, cy, 5, YELLOW, is_enemy=True, vx=vx))

        else:
            # Focused salvo: all cannons aim at a random screen position
            target_x = random.randint(100, SCREEN_WIDTH - 100)
            for i in range(4):
                cx, cy = self._cannon_pos(i)
                dx = (target_x - cx) * 0.018
                lasers.append(
                    Laser(cx, cy, 5, (255, 130, 50), is_enemy=True, vx=dx)
                )

        return lasers

    # ------------------------------------------------------------------
    # FURIA (Boss 1): Devastating burst attacks
    # ------------------------------------------------------------------

    def _fire_furia(self) -> list[Laser]:
        """Furia fires rapid bursts from lateral cannons.

        Primary: 3 lasers per side at staggered vertical offsets.
        Secondary: Activates a burst counter for follow-up shots.

        All shots travel straight down (no horizontal velocity on primary).
        """
        lasers: list[Laser] = []
        for i in [0, 3]:
            cx, cy = self._cannon_pos(i)
            for dy in [0, 10, 20]:
                speed = 5.5 + dy * 0.08
                lasers.append(Laser(cx, cy + dy, speed, CYAN, is_enemy=True))

        # Activate secondary burst
        self._burst_count = 3
        self._burst_delay = 6
        return lasers

    # ------------------------------------------------------------------
    # VENTAGLIO (Boss 2): Alternating fan waves
    # ------------------------------------------------------------------

    def _fire_ventaglio(self) -> list[Laser]:
        """Ventaglio fires a fan of 5 lasers with alternating direction.

        The spread angle oscillates over time, creating varied wave patterns.
        All shots have a guaranteed downward component (vy >= 3.5).
        The fan width and offset alternate to prevent memorization.
        """
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        self._fan_wave += 1
        n_rays = 5
        # Spread oscillates between 25 and 50 degrees
        spread = 25 + 25 * abs(math.sin(self._fan_wave * 0.25))

        base_angle = self._fan_direction * 8
        for i in range(n_rays):
            angle_deg = base_angle + (-spread + (2 * spread / max(1, n_rays - 1)) * i)
            rad = math.radians(angle_deg)
            vx = math.sin(rad) * 3.5
            # Ensure vy is always positive (downward) and substantial
            vy = max(3.5, math.cos(rad) * 5.0)
            lasers.append(
                Laser(center_x - 2, center_y, vy, MAGENTA, is_enemy=True, vx=vx)
            )

        self._fan_direction *= -1
        return lasers

    # ------------------------------------------------------------------
    # VORTICE (Boss 3): Rotating spiral arms
    # ------------------------------------------------------------------

    def _fire_vortice(self) -> list[Laser]:
        """Vortice fires 3 rotating spiral arms that accelerate gradually.

        Each arm is offset by 120 degrees. The rotation speed increases
        over time then resets, creating rhythmic patterns the player
        can learn to dodge. All shots have positive vy (downward).
        """
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        n_arms = 3
        for arm in range(n_arms):
            offset = (2 * math.pi / n_arms) * arm
            angle = self._spiral_angle + offset
            vx = math.sin(angle) * 3.0
            # Always ensure downward movement (vy positive and > 2)
            vy = max(2.5, abs(math.cos(angle)) * 4.0 + 1.5)
            lasers.append(
                Laser(center_x - 2, center_y, vy, GREEN, is_enemy=True, vx=vx)
            )

        # Gradually accelerate spiral, then reset for rhythmic feel
        self._spiral_speed += self._spiral_accel
        if self._spiral_speed > 1.0:
            self._spiral_speed = 0.4
        self._spiral_angle += self._spiral_speed

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
