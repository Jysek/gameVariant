"""
Formazioni nemici -- v5.

Definisce 15+ formazioni disponibili e la logica di selezione basata
sul livello di difficolta'.  Un sistema anti-ripetizione impedisce che
la stessa formazione venga scelta due volte di seguito.

Ogni formazione e' un insieme di ``Slot(col, row)`` in una griglia logica.
Le posizioni di spawn vengono calcolate garantendo che il nuovo gruppo
non si sovrapponga a nessun gruppo gia' presente sullo schermo.
"""

import random
from typing import NamedTuple

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ENEMY_W, ENEMY_H


class Slot(NamedTuple):
    """Cella (colonna, riga) nella griglia di una formazione."""
    col: int
    row: int


# ---------------------------------------------------------------------------
# Dimensioni cella nella griglia delle formazioni.
# Il padding extra garantisce spaziatura minima tra nemici nella stessa
# formazione.
# ---------------------------------------------------------------------------
CELL_W = ENEMY_W + 16   # 76 px
CELL_H = ENEMY_H + 20   # 80 px

# ---------------------------------------------------------------------------
# Catalogo formazioni.
# Ogni formazione e' una lista di Slot(col, row).  Il nome e' puramente
# mnemonico e viene usato per il mapping tipo-nemico.
# ---------------------------------------------------------------------------
FORMATIONS: dict[str, list[Slot]] = {
    # --- Semplici (livelli bassi) ---
    "H_LINE_3":  [Slot(c, 0) for c in range(3)],
    "H_LINE_5":  [Slot(c, 0) for c in range(5)],
    "V_LINE_3":  [Slot(0, r) for r in range(3)],
    "GRID_3x2":  [Slot(c, r) for r in range(2) for c in range(3)],
    "GRID_4x2":  [Slot(c, r) for r in range(2) for c in range(4)],
    "GRID_3x3":  [Slot(c, r) for r in range(3) for c in range(3)],

    # --- Intermedie ---
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

    # --- Avanzate (livelli alti) ---
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
# Pool di formazioni per livello di difficolta'.
# Ai livelli bassi le formazioni sono piu' semplici.
# Ogni pool contiene almeno 5 voci per garantire varieta'.
# ---------------------------------------------------------------------------
_POOLS: list[list[str]] = [
    # Lv 0 -- introduttivo
    ["H_LINE_3", "V_LINE_3", "GRID_3x2", "H_LINE_5", "STAGGER_3x2", "CROSS"],
    # Lv 1 -- si aggiungono griglie
    ["H_LINE_5", "GRID_3x2", "GRID_4x2", "GRID_3x3", "T_SHAPE", "STAGGER_3x2", "CROSS"],
    # Lv 2 -- formazioni intermedie
    ["GRID_3x3", "DIAMOND", "V_SHAPE", "Z_LINE", "CROSS", "T_SHAPE", "WING"],
    # Lv 3 -- formazioni complesse
    ["V_SHAPE", "DIAMOND", "Z_LINE", "PINCER", "ARROW", "CHEVRON", "X_SHAPE"],
    # Lv 4+ -- tutto il catalogo
    ["DIAMOND", "V_SHAPE", "PINCER", "ARROW", "Z_LINE", "WING",
     "CHEVRON", "FORTRESS", "X_SHAPE", "GRID_3x3", "GRID_4x2"],
]

# Storico formazioni usate recentemente (per anti-ripetizione)
_recent_formations: list[str] = []
_RECENT_MAX = 3   # non ripetere le ultime N formazioni


def pick_formation(difficulty_level: int) -> tuple[str, list[Slot]]:
    """Sceglie una formazione casuale dal pool appropriato per il livello.

    Il sistema anti-ripetizione evita che le ultime ``_RECENT_MAX``
    formazioni vengano scelte nuovamente, garantendo varieta'.

    Args:
        difficulty_level: Livello di difficolta' corrente (0+).

    Returns:
        Tupla ``(nome_formazione, lista_di_slot)``.
    """
    pool_idx = min(difficulty_level, len(_POOLS) - 1)
    pool = _POOLS[pool_idx]

    # Filtra formazioni recenti
    candidates = [n for n in pool if n not in _recent_formations]
    if not candidates:
        # Se tutte sono state usate di recente, usa il pool completo
        candidates = list(pool)

    name = random.choice(candidates)

    # Aggiorna storico
    _recent_formations.append(name)
    if len(_recent_formations) > _RECENT_MAX:
        _recent_formations.pop(0)

    return name, list(FORMATIONS[name])


def reset_formation_history() -> None:
    """Resetta lo storico delle formazioni recenti (nuova partita)."""
    _recent_formations.clear()


# ---------------------------------------------------------------------------
# Calcolo posizioni di spawn
# ---------------------------------------------------------------------------

def build_spawn_positions(
    slots: list[Slot],
    existing_groups=None,
) -> list[dict]:
    """Calcola le posizioni di spawn per una formazione.

    La formazione viene posizionata sopra lo schermo (y negativa) e centrata
    orizzontalmente con un offset casuale.  Se ci sono gruppi gia' presenti,
    la posizione orizzontale viene scelta per NON sovrapporsi ai nemici
    esistenti.

    Args:
        slots:           Lista di ``Slot`` della formazione scelta.
        existing_groups: Lista opzionale di ``FormationGroup`` gia' sullo
                         schermo (usata per evitare sovrapposizioni).

    Returns:
        Lista di dict con chiavi ``'x'``, ``'y'``, ``'slot'`` per ogni nemico.
    """
    if not slots:
        return []

    max_col = max(s.col for s in slots)
    max_row = max(s.row for s in slots)
    fw = (max_col + 1) * CELL_W   # larghezza totale formazione in pixel
    fh = (max_row + 1) * CELL_H   # altezza totale formazione in pixel

    ox = _find_safe_x(fw, existing_groups)
    oy = -fh - 40   # sopra lo schermo con margine extra

    return [
        {"x": float(ox + s.col * CELL_W),
         "y": float(oy + s.row * CELL_H),
         "slot": s}
        for s in slots
    ]


def _find_safe_x(formation_width: int, existing_groups) -> int:
    """Trova una posizione X che non si sovrapponga ai gruppi esistenti.

    Strategia:
    1. Se non ci sono gruppi, posizionamento casuale nella zona centrale.
    2. Altrimenti, tenta 60 posizioni casuali evitando le fasce occupate.
    3. Fallback: cerca il gap piu' ampio tra le zone occupate.

    Args:
        formation_width: Larghezza totale della formazione in pixel.
        existing_groups: Lista di ``FormationGroup`` attivi (puo' essere ``None``).

    Returns:
        Coordinata X (int) per l'angolo sinistro della formazione.
    """
    x_min = 15
    x_max = max(x_min, SCREEN_WIDTH - formation_width - 15)

    # Nessun gruppo esistente: posizionamento casuale centrato
    if not existing_groups:
        center = (SCREEN_WIDTH - formation_width) // 2
        cx_min = max(x_min, center - 100)
        cx_max = min(x_max, center + 100)
        return random.randint(cx_min, cx_max)

    # Raccogli le fasce X occupate dai gruppi nella meta' superiore
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

    # Tenta posizionamento casuale evitando le zone occupate
    for _ in range(60):
        ox = random.randint(x_min, x_max)
        new_l = ox
        new_r = ox + formation_width
        if all(new_l >= gr or new_r <= gl for gl, gr in occupied):
            return ox

    # Fallback: cerca il gap piu' ampio
    occupied.sort()
    candidates: list[tuple[int, int]] = []

    # Gap prima della prima zona occupata
    if occupied[0][0] > x_min + formation_width:
        gap = int(occupied[0][0] - x_min)
        cx = x_min + max(0, (gap - formation_width) // 2)
        candidates.append((gap, cx))

    # Gap tra zone consecutive
    for i in range(len(occupied) - 1):
        gap_start = occupied[i][1]
        gap_end   = occupied[i + 1][0]
        gap = int(gap_end - gap_start)
        if gap >= formation_width:
            cx = int(gap_start + (gap - formation_width) // 2)
            candidates.append((gap, cx))

    # Gap dopo l'ultima zona occupata
    gap_after = int(SCREEN_WIDTH - occupied[-1][1])
    if gap_after >= formation_width:
        cx = max(x_min, int(occupied[-1][1]))
        candidates.append((gap_after, cx))

    if candidates:
        candidates.sort(reverse=True)
        _, best_x = candidates[0]
        return max(x_min, min(x_max, best_x))

    # Ultimo fallback: overlap inevitabile su schermi molto stretti
    return random.randint(x_min, x_max)
