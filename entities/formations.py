"""
Formazioni nemici -- v5 (PRD gameVariant).

Definisce le formazioni disponibili e la logica di selezione basata sul livello
di difficolta'. Ogni formazione e' un insieme di Slot (col, row) in una griglia
logica.

Formazioni PRD:
- GRID:       Griglia classica N x M
- V_FORMATION: 9-13 nemici a V con leader
- DIVE_ATTACK: (gestito dinamicamente in formation_group.py)
- SWARM:       2 colonne di 8 scout sinusoidali
- DOUBLE_V:    Due V convergenti (wave 7+)

Le posizioni di spawn vengono calcolate garantendo che il nuovo gruppo
non si sovrapponga a nessun gruppo gia' presente sullo schermo.
"""
import random
from typing import NamedTuple
from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ENEMY_SIZE


class Slot(NamedTuple):
    """Rappresenta una cella (colonna, riga) nella griglia di una formazione."""
    col: int
    row: int


# --------------------------------------------------------------------------
# Dimensioni cella nella griglia delle formazioni.
# Il padding extra garantisce che i nemici nella stessa formazione
# abbiano un minimo di spazio tra loro.
# --------------------------------------------------------------------------
CELL_W = ENEMY_SIZE + 20   # 70 px  (50 sprite + 20 padding)
CELL_H = ENEMY_SIZE + 18   # 68 px  (50 sprite + 18 padding)

# --------------------------------------------------------------------------
# Definizione formazioni.
# Ogni formazione e' una lista di Slot(col, row).
# --------------------------------------------------------------------------
FORMATIONS = {
    # ---- Formazioni base ----
    "GRID_3x3": [Slot(c, r) for r in range(3) for c in range(3)],
    "GRID_4x2": [Slot(c, r) for r in range(2) for c in range(4)],
    "GRID_3x6": [Slot(c, r) for r in range(3) for c in range(6)],
    "GRID_4x6": [Slot(c, r) for r in range(4) for c in range(6)],
    "H_LINE":   [Slot(c, 0) for c in range(5)],

    # ---- Formazione V (PRD 4.2) -- 11 nemici ----
    "V_FORMATION": [
        Slot(3, 0),                          # leader
        Slot(2, 1), Slot(4, 1),              # riga 1
        Slot(1, 2), Slot(5, 2),              # riga 2
        Slot(0, 3), Slot(6, 3),              # riga 3
        Slot(0, 4), Slot(1, 4), Slot(5, 4), Slot(6, 4),  # ali
    ],

    # ---- V_SHAPE legacy ----
    "V_SHAPE": [
        Slot(1, 0), Slot(2, 0),
        Slot(0, 1), Slot(1, 1), Slot(2, 1), Slot(3, 1),
        Slot(0, 2), Slot(1, 2), Slot(2, 2), Slot(3, 2),
    ],

    # ---- Swarm (PRD 4.4) -- 16 scout in 2 colonne ----
    "SWARM": [Slot(c, r) for r in range(8) for c in range(2)],

    # ---- Double V Convergente (PRD 4.5) -- 2 V convergenti ----
    "DOUBLE_V": [
        # V sinistra
        Slot(0, 0), Slot(1, 1), Slot(2, 2), Slot(1, 3), Slot(0, 4),
        # V destra
        Slot(5, 0), Slot(4, 1), Slot(3, 2), Slot(4, 3), Slot(5, 4),
    ],

    "DIAMOND": [
        Slot(1, 0),
        Slot(0, 1), Slot(1, 1), Slot(2, 1),
        Slot(0, 2), Slot(1, 2), Slot(2, 2),
        Slot(1, 3),
    ],
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
}

# --------------------------------------------------------------------------
# Pool di formazioni per livello di difficolta' (PRD Wave Manager).
# --------------------------------------------------------------------------
_POOLS = [
    # Lv 0 (wave 1-2): griglie semplici di scout
    ["GRID_3x3", "GRID_4x2", "H_LINE", "GRID_3x6"],
    # Lv 1 (wave 3-4): griglia + inizio dive
    ["GRID_3x6", "GRID_4x2", "V_SHAPE", "GRID_4x6"],
    # Lv 2 (wave 5-6): V-Formation + formazioni medie
    ["V_FORMATION", "V_SHAPE", "DIAMOND", "Z_LINE"],
    # Lv 3 (wave 7): Swarm
    ["SWARM", "V_FORMATION", "Z_LINE", "PINCER"],
    # Lv 4 (wave 8): Double V
    ["DOUBLE_V", "V_FORMATION", "DIAMOND", "ARROW"],
    # Lv 5+ (wave 9+): mix completo
    ["DOUBLE_V", "V_FORMATION", "SWARM", "DIAMOND", "PINCER", "ARROW", "GRID_4x6"],
]


def pick_formation(difficulty_level: int) -> tuple[str, list[Slot]]:
    """Sceglie una formazione casuale dal pool appropriato per il livello.

    Args:
        difficulty_level: Livello di difficolta' corrente (0+).

    Returns:
        Tupla (nome_formazione, lista_di_slot).
    """
    pool = _POOLS[min(difficulty_level, len(_POOLS) - 1)]
    name = random.choice(pool)
    return name, list(FORMATIONS[name])


def build_spawn_positions(
    slots: list[Slot],
    existing_groups=None,
) -> list[dict]:
    """Calcola le posizioni di spawn per una formazione.

    La formazione viene posizionata sopra lo schermo (y negativa) e centrata
    orizzontalmente con un offset casuale. Se ci sono gruppi gia' presenti,
    la posizione orizzontale viene scelta in modo da NON sovrapporsi a
    nessun nemico esistente.

    Args:
        slots: Lista di Slot della formazione scelta.
        existing_groups: Lista opzionale di FormationGroup gia' sullo schermo
                         (usata per evitare sovrapposizioni orizzontali).

    Returns:
        Lista di dict con chiavi 'x', 'y', 'slot' per ogni nemico.
    """
    if not slots:
        return []

    max_col = max(s.col for s in slots)
    max_row = max(s.row for s in slots)
    # Dimensione totale della formazione in pixel
    fw = (max_col + 1) * CELL_W
    fh = (max_row + 1) * CELL_H

    # Calcola un offset X che non si sovrapponga ai gruppi esistenti
    ox = _find_safe_x(fw, existing_groups)

    # Posizione Y: sopra lo schermo con margine extra
    oy = -fh - 40

    return [
        {"x": float(ox + s.col * CELL_W), "y": float(oy + s.row * CELL_H), "slot": s}
        for s in slots
    ]


def _find_safe_x(formation_width: int, existing_groups) -> int:
    """Trova una posizione X che non si sovrapponga ai gruppi esistenti."""
    x_min = 15
    x_max = max(x_min, SCREEN_WIDTH - formation_width - 15)

    if not existing_groups:
        center = (SCREEN_WIDTH - formation_width) // 2
        cx_min = max(x_min, center - 80)
        cx_max = min(x_max, center + 80)
        return random.randint(cx_min, cx_max)

    occupied = []
    _SAFETY = 20
    for g in existing_groups:
        alive = g.alive_enemies
        if not alive:
            continue
        group_top = min(e.y for e in alive)
        if group_top > SCREEN_HEIGHT // 2:
            continue
        gl = min(e.x for e in alive) - _SAFETY
        gr = max(e.x + e.width for e in alive) + _SAFETY
        occupied.append((gl, gr))

    if not occupied:
        center = (SCREEN_WIDTH - formation_width) // 2
        cx_min = max(x_min, center - 80)
        cx_max = min(x_max, center + 80)
        return random.randint(cx_min, cx_max)

    for _ in range(60):
        ox = random.randint(x_min, x_max)
        new_left = ox
        new_right = ox + formation_width
        ok = True
        for gl, gr in occupied:
            if new_left < gr and new_right > gl:
                ok = False
                break
        if ok:
            return ox

    occupied.sort()
    candidates = []

    if occupied[0][0] > x_min + formation_width:
        gap = occupied[0][0] - x_min
        cx = x_min + max(0, (gap - formation_width) // 2)
        candidates.append((gap, cx))

    for i in range(len(occupied) - 1):
        gap_start = occupied[i][1]
        gap_end = occupied[i + 1][0]
        gap = gap_end - gap_start
        if gap >= formation_width:
            cx = int(gap_start + (gap - formation_width) // 2)
            candidates.append((gap, cx))

    gap_after = SCREEN_WIDTH - occupied[-1][1]
    if gap_after >= formation_width:
        cx = max(x_min, int(occupied[-1][1]))
        candidates.append((gap_after, cx))

    if candidates:
        candidates.sort(reverse=True)
        _, best_x = candidates[0]
        return max(x_min, min(x_max, best_x))

    return random.randint(x_min, x_max)
