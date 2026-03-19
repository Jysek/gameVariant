"""
Asteroid -- sprite with pixel-art trail and guaranteed safe corridor.

Asteroids fall from top to bottom with rotation and a luminous
particle trail. Particles use BLEND_ADD for a fire/heat effect.

A global registry ``_active_x`` prevents horizontal overlap between
active asteroids. During meteor rain, the system guarantees at least
one corridor of ``SAFE_CORRIDOR_W`` pixels free from asteroids,
so the player always has a viable path.
"""

import random
import math
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ASTEROID_SIZE
from core.assets import Assets

# ---------------------------------------------------------------------------
# Global registry of active asteroid X positions.
# ---------------------------------------------------------------------------
_active_x: list[float] = []
_MIN_GAP = 90  # minimum horizontal distance between asteroids (px)

# Minimum width of the guaranteed safe corridor during rain
SAFE_CORRIDOR_W = 100

# Trail spritesheet parameters
_N_FRAMES = 12
_FW = 32


def _safe_x(w: int) -> float:
    """Calculate a safe X position for a new asteroid.

    Tries random placement that respects minimum distance from all
    active asteroids AND doesn't completely block the last safe corridor.
    Falls back to column-based placement after 30 failed attempts.

    Args:
        w: Asteroid width in pixels.

    Returns:
        X position as float, or -1 if spawning would block the safe corridor.
    """
    corridor = _find_largest_gap()

    for _ in range(30):
        x = random.randint(20, SCREEN_WIDTH - w - 20)

        if not all(abs(x - ox) >= _MIN_GAP for ox in _active_x):
            continue

        if _would_block_corridor(x, w, corridor):
            continue

        return float(x)

    # Fallback: column-based placement
    cols = 6
    cw = (SCREEN_WIDTH - 40) // cols
    counts = [0] * cols
    for ox in _active_x:
        c = int((ox - 20) / cw)
        if 0 <= c < cols:
            counts[c] += 1

    sorted_cols = sorted(range(cols), key=lambda i: counts[i])

    for best in sorted_cols:
        x = float(20 + best * cw + random.randint(0, max(0, cw - w)))
        if not _would_block_corridor(x, w, corridor):
            return x

    return -1.0


def _find_largest_gap() -> tuple[float, float]:
    """Find the widest horizontal gap between active asteroids.

    Returns:
        Tuple (gap_start, gap_end) of the widest corridor.
        Returns the entire screen width if no asteroids are active.
    """
    if not _active_x:
        return (0.0, float(SCREEN_WIDTH))

    half_w = ASTEROID_SIZE / 2
    intervals = sorted((x - half_w, x + ASTEROID_SIZE + half_w) for x in _active_x)

    # Merge overlapping intervals
    merged: list[tuple[float, float]] = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Find the widest gap
    best_gap = (0.0, merged[0][0])
    for i in range(len(merged) - 1):
        gap_start = merged[i][1]
        gap_end   = merged[i + 1][0]
        if (gap_end - gap_start) > (best_gap[1] - best_gap[0]):
            best_gap = (gap_start, gap_end)

    final_start = merged[-1][1]
    final_end   = float(SCREEN_WIDTH)
    if (final_end - final_start) > (best_gap[1] - best_gap[0]):
        best_gap = (final_start, final_end)

    return best_gap


def _would_block_corridor(
    x: float, w: int, corridor: tuple[float, float]
) -> bool:
    """Check if placing an asteroid at ``x`` would block the safe corridor.

    Args:
        x:        Candidate X position for the new asteroid.
        w:        Asteroid width.
        corridor: Current (start, end) of the widest gap.

    Returns:
        True if spawning here would narrow the corridor below SAFE_CORRIDOR_W.
    """
    gap_w = corridor[1] - corridor[0]
    if gap_w <= SAFE_CORRIDOR_W:
        return True

    half = ASTEROID_SIZE / 2
    ast_left  = x - half
    ast_right = x + w + half

    if ast_right <= corridor[0] or ast_left >= corridor[1]:
        return False

    left_gap  = max(0, ast_left - corridor[0])
    right_gap = max(0, corridor[1] - ast_right)
    best_remaining = max(left_gap, right_gap)

    return best_remaining < SAFE_CORRIDOR_W


def clear_registry() -> None:
    """Clear the global asteroid position registry."""
    _active_x.clear()


class _Particle:
    """Single luminous trail particle for an asteroid.

    Particles drift upward slightly (simulating hot smoke), advance
    through spritesheet frames, and fade out gradually.
    """
    __slots__ = ('x', 'y', 'vx', 'vy', 'frame', 'alpha', 'sz', 'alive')

    def __init__(self, cx: float, cy: float):
        """Create a particle near the asteroid center.

        Args:
            cx: Asteroid center X (pixels).
            cy: Asteroid center Y (pixels).
        """
        self.x     = cx + random.uniform(-10, 10)
        self.y     = cy + random.uniform(-6, 6)
        self.vx    = random.uniform(-0.3, 0.3)
        self.vy    = random.uniform(-1.0, -0.15)
        self.frame = float(random.randint(0, 2))
        self.alpha = random.randint(200, 255)
        self.sz    = random.uniform(0.5, 1.2)
        self.alive = True

    def update(self) -> None:
        """Update position, frame progression, and opacity."""
        self.x += self.vx
        self.y += self.vy
        self.frame += 0.4
        self.alpha -= 16
        self.sz = max(0, self.sz - 0.02)
        if self.alpha <= 0 or self.sz < 0.05 or self.frame >= _N_FRAMES:
            self.alive = False

    def draw(self, surf: pygame.Surface, frames: list[pygame.Surface]) -> None:
        """Draw the particle using the trail spritesheet frame.

        Args:
            surf:   Target surface.
            frames: Trail spritesheet frame list.
        """
        fi = min(int(self.frame), _N_FRAMES - 1)
        src = frames[fi]
        sz = max(2, int(_FW * self.sz))
        scaled = pygame.transform.scale(src, (sz, sz))
        scaled.set_alpha(max(0, min(255, int(self.alpha))))
        surf.blit(
            scaled,
            (int(self.x - sz // 2), int(self.y - sz // 2)),
            special_flags=pygame.BLEND_ADD,
        )


class Asteroid:
    """Falling asteroid with rotation and luminous trail.

    Asteroids are indestructible (lasers don't affect them).
    Collision with the player = instant death (ignores shield).

    Class attributes:
        MIN_SPEED: Minimum fall speed.
        MAX_SPEED: Maximum fall speed (safety cap).
    """

    MIN_SPEED = 1.8
    MAX_SPEED = 3.2

    def __init__(self):
        """Create a new asteroid above the screen at a safe X position.

        If the safe-corridor system prevents spawning (returns x == -1),
        the asteroid is created but immediately deactivated.
        """
        self.width  = ASTEROID_SIZE
        self.height = ASTEROID_SIZE
        x = _safe_x(self.width)
        if x < 0:
            self.x = 0.0
            self.y = -999.0
            self.active = False
            self.fall_speed = 0.0
            self.angle = 0.0
            self.rot_speed = 0
            self.trail: list[_Particle] = []
            return

        self.x = x
        self.y = float(-self.height - random.randint(0, 40))
        self.active = True
        _active_x.append(self.x)

        self.fall_speed = random.uniform(self.MIN_SPEED, self.MAX_SPEED)
        self.angle     = 0.0
        self.rot_speed = random.choice([-3, -2, -1, 1, 2, 3])
        self.trail: list[_Particle] = []

    def update(self) -> None:
        """Update position, rotation, and trail particles."""
        if not self.active:
            return

        self.y += self.fall_speed
        self.angle = (self.angle + self.rot_speed) % 360

        # Generate trail particles
        cx = self.x + self.width // 2
        cy = self.y + self.height // 2
        for _ in range(random.randint(4, 6)):
            self.trail.append(_Particle(cx, cy))

        # Update and prune dead particles
        for p in self.trail:
            p.update()
        self.trail = [p for p in self.trail if p.alive]

        # Deactivate when off bottom of screen
        if self.y > SCREEN_HEIGHT + 60:
            self.active = False
            self._dereg()

    def _dereg(self) -> None:
        """Remove this asteroid's X from the global registry."""
        try:
            _active_x.remove(self.x)
        except ValueError:
            pass

    def deactivate(self) -> None:
        """Explicitly deactivate and unregister this asteroid."""
        if self.active:
            self.active = False
            self._dereg()

    def draw(self, surf: pygame.Surface) -> None:
        """Draw the asteroid with luminous trail and rotation.

        Args:
            surf: Target surface.
        """
        if not self.active:
            return

        # Draw trail behind the asteroid
        if Assets.trail_frames:
            for p in self.trail:
                p.draw(surf, Assets.trail_frames)

        # Draw the rotated asteroid sprite
        rot = pygame.transform.rotate(Assets.asteroid_sprite, self.angle)
        rect = rot.get_rect(center=(
            int(self.x + self.width // 2),
            int(self.y + self.height // 2),
        ))
        surf.blit(rot, rect)

    def get_rect(self) -> pygame.Rect:
        """Return the collision hitbox (shrunken by 8px per side for fairness)."""
        shrink = 8
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width - shrink * 2,
            self.height - shrink * 2,
        )
