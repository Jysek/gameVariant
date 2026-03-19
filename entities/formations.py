"""
Enemy formations -- v5.

Defines 18 available formations and the selection logic based on
difficulty level. An anti-repetition system prevents the same
formation from being chosen twice in a row.

Each formation is a set of ``Slot(col, row)`` in a logical grid.
Spawn positions are calculated ensuring the new group doesn't overlap
any existing groups on screen.
"""

import random
from typing import NamedTuple

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ENEMY_W, ENEMY_H


class Slot(NamedTuple):
    """Cell (column, row) in a formation grid."""
    col: int
    row: int


# ---------------------------------------------------------------------------
# Cell dimensions in the formation grid.
# Extra padding ensures minimum spacing between enemies.
# ---------------------------------------------------------------------------
CELL_W = ENEMY_W + 16  # 76 px
CELL_H = ENEMY_H + 20  # 80 px

# ---------------------------------------------------------------------------
# Formation catalog.
# Each formation is a list of Slot(col, row). Names are mnemonic.
# ---------------------------------------------------------------------------
FORMATIONS: dict[str, list[Slot]] = {
    # --- Simple (low levels) ---
    "H_LINE_3":  [Slot(c, 0) for c in range(3)],
    "H_LINE_5":  [Slot(c, 0) for c in range(5)],
    "V_LINE_3":  [Slot(0, r) for r in range(3)],
    "GRID_3x2":  [Slot(c, r) for r in range(2) for c in range(3)],
    "GRID_4x2":  [Slot(c, r) for r in range(2) for c in range(4)],
    "GRID_3x3":  [Slot(c, r) for r in range(3) for c in range(3)],

    # --- Intermediate ---
    "DIAMOND": [
        Slot(1, 0),
        Slot(0, 1), Slot(1, 1), Slot(2, 1),
        Slot(0, 2), Slot(1, 2), Slot(2, 2),
        Slot(1, 3),
    ],
    "V_SHAPE": [
        Slot(1, 0), Slot(2, 0),
        Slot(0, 1), Slot(1, 1), Slot(2, 1), Slot(3, 1),
        Slot(0, 2), Slot(1, 2), Slot(2, 2), Slot(3, 2),
    ],
    "CROSS": [
        Slot(1, 0),
        Slot(0, 1), Slot(1, 1), Slot(2, 1),
        Slot(1, 2),
    ],
    "T_SHAPE": [
        Slot(0, 0), Slot(1, 0), Slot(2, 0),
        Slot(1, 1),
        Slot(1, 2),
    ],
    "STAGGER_3x2": [
        Slot(0, 0), Slot(1, 0), Slot(2, 0),
        Slot(0, 1), Slot(2, 1),
    ],

    # --- Advanced (high levels) ---
    "PINCER": [
        Slot(0, 0), Slot(3, 0),
        Slot(0, 1), Slot(3, 1),
        Slot(0, 2), Slot(3, 2),
    ],
    "ARROW": [
        Slot(0, 1),
        Slot(1, 0), Slot(1, 1), Slot(1, 2),
        Slot(2, 0), Slot(2, 2),
    ],
    "Z_LINE": [
        Slot(0, 0), Slot(1, 0), Slot(2, 0),
        Slot(1, 1), Slot(2, 1), Slot(3, 1),
        Slot(2, 2), Slot(3, 2), Slot(4, 2),
    ],
    "WING": [
        Slot(0, 0), Slot(4, 0),
        Slot(1, 1), Slot(3, 1),
        Slot(2, 2),
    ],
    "CHEVRON": [
        Slot(2, 0),
        Slot(1, 1), Slot(3, 1),
        Slot(0, 2), Slot(4, 2),
    ],
    "FORTRESS": [
        Slot(0, 0), Slot(1, 0), Slot(2, 0), Slot(3, 0),
        Slot(0, 1), Slot(3, 1),
        Slot(0, 2), Slot(1, 2), Slot(2, 2), Slot(3, 2),
    ],
    "X_SHAPE": [
        Slot(0, 0), Slot(2, 0),
        Slot(1, 1),
        Slot(0, 2), Slot(2, 2),
    ],
}

# ---------------------------------------------------------------------------
# Formation pools by difficulty level.
# Each pool has at least 5 entries for variety.
# ---------------------------------------------------------------------------
_POOLS: list[list[str]] = [
    ["H_LINE_3", "V_LINE_3", "GRID_3x2", "H_LINE_5", "STAGGER_3x2", "CROSS"],
    ["H_LINE_5", "GRID_3x2", "GRID_4x2", "GRID_3x3", "T_SHAPE", "STAGGER_3x2", "CROSS"],
    ["GRID_3x3", "DIAMOND", "V_SHAPE", "Z_LINE", "CROSS", "T_SHAPE", "WING"],
    ["V_SHAPE", "DIAMOND", "Z_LINE", "PINCER", "ARROW", "CHEVRON", "X_SHAPE"],
    ["DIAMOND", "V_SHAPE", "PINCER", "ARROW", "Z_LINE", "WING",
     "CHEVRON", "FORTRESS", "X_SHAPE", "GRID_3x3", "GRID_4x2"],
]

# Recent formations history (for anti-repetition)
_recent_formations: list[str] = []
_RECENT_MAX = 3


def pick_formation(difficulty_level: int) -> tuple[str, list[Slot]]:
    """Choose a random formation from the pool appropriate for the level.

    The anti-repetition system prevents the last ``_RECENT_MAX``
    formations from being chosen again.

    Args:
        difficulty_level: Current difficulty level (0+).

    Returns:
        Tuple (formation_name, list_of_slots).
    """
    pool_idx = min(difficulty_level, len(_POOLS) - 1)
    pool = _POOLS[pool_idx]

    candidates = [n for n in pool if n not in _recent_formations]
    if not candidates:
        candidates = list(pool)

    name = random.choice(candidates)

    _recent_formations.append(name)
    if len(_recent_formations) > _RECENT_MAX:
        _recent_formations.pop(0)

    return name, list(FORMATIONS[name])


def reset_formation_history() -> None:
    """Reset the recent formation history (for new game)."""
    _recent_formations.clear()


# ---------------------------------------------------------------------------
# Spawn position calculation
# ---------------------------------------------------------------------------

def build_spawn_positions(
    slots: list[Slot],
    existing_groups=None,
) -> list[dict]:
    """Calculate spawn positions for a formation.

    The formation is placed above the screen (negative y) and centered
    horizontally with a random offset. If existing groups are present,
    the horizontal position is chosen to avoid overlapping them.

    Args:
        slots:           List of formation ``Slot`` objects.
        existing_groups: Optional list of active ``FormationGroup`` objects.

    Returns:
        List of dicts with 'x', 'y', 'slot' keys for each enemy.
    """
    if not slots:
        return []

    max_col = max(s.col for s in slots)
    max_row = max(s.row for s in slots)
    fw = (max_col + 1) * CELL_W
    fh = (max_row + 1) * CELL_H

    ox = _find_safe_x(fw, existing_groups)
    oy = -fh - 40

    return [
        {"x": float(ox + s.col * CELL_W),
         "y": float(oy + s.row * CELL_H),
         "slot": s}
        for s in slots
    ]


def _find_safe_x(formation_width: int, existing_groups) -> int:
    """Find an X position that doesn't overlap existing groups.

    Strategy:
    1. No groups: random placement in center area.
    2. Otherwise: try 60 random positions avoiding occupied zones.
    3. Fallback: find the widest gap between occupied zones.

    Args:
        formation_width: Total formation width in pixels.
        existing_groups: List of active ``FormationGroup`` objects (may be None).

    Returns:
        X coordinate (int) for the left edge of the formation.
    """
    x_min = 15
    x_max = max(x_min, SCREEN_WIDTH - formation_width - 15)

    if not existing_groups:
        center = (SCREEN_WIDTH - formation_width) // 2
        cx_min = max(x_min, center - 100)
        cx_max = min(x_max, center + 100)
        return random.randint(cx_min, cx_max)

    # Collect occupied X bands from groups in the upper half
    occupied: list[tuple[float, float]] = []
    safety = 20
    for g in existing_groups:
        alive = g.alive_enemies
        if not alive:
            continue
        if min(e.y for e in alive) > SCREEN_HEIGHT // 2:
            continue
        gl = min(e.x for e in alive) - safety
        gr = max(e.x + e.width for e in alive) + safety
        occupied.append((gl, gr))

    if not occupied:
        center = (SCREEN_WIDTH - formation_width) // 2
        cx_min = max(x_min, center - 100)
        cx_max = min(x_max, center + 100)
        return random.randint(cx_min, cx_max)

    # Try random placement avoiding occupied zones
    for _ in range(60):
        ox = random.randint(x_min, x_max)
        new_l = ox
        new_r = ox + formation_width
        if all(new_l >= gr or new_r <= gl for gl, gr in occupied):
            return ox

    # Fallback: find the widest gap
    occupied.sort()
    candidates: list[tuple[int, int]] = []

    if occupied[0][0] > x_min + formation_width:
        gap = int(occupied[0][0] - x_min)
        cx = x_min + max(0, (gap - formation_width) // 2)
        candidates.append((gap, cx))

    for i in range(len(occupied) - 1):
        gap_start = occupied[i][1]
        gap_end   = occupied[i + 1][0]
        gap = int(gap_end - gap_start)
        if gap >= formation_width:
            cx = int(gap_start + (gap - formation_width) // 2)
            candidates.append((gap, cx))

    gap_after = int(SCREEN_WIDTH - occupied[-1][1])
    if gap_after >= formation_width:
        cx = max(x_min, int(occupied[-1][1]))
        candidates.append((gap_after, cx))

    if candidates:
        candidates.sort(reverse=True)
        _, best_x = candidates[0]
        return max(x_min, min(x_max, best_x))

    return random.randint(x_min, x_max)
