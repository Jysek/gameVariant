"""
Formazioni nemici -- v4.

Definisce le formazioni disponibili e la logica di selezione basata sul livello
di difficolta'. Ogni formazione e' un insieme di Slot (col, row) in una griglia
logica.

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
    "GRID_3x3": [Slot(c, r) for r in range(3) for c in range(3)],
    "GRID_4x2": [Slot(c, r) for r in range(2) for c in range(4)],
    "H_LINE":   [Slot(c, 0) for c in range(5)],
    "V_SHAPE":  [
        Slot(1, 0), Slot(2, 0),
        Slot(0, 1), Slot(1, 1), Slot(2, 1), Slot(3, 1),
        Slot(0, 2), Slot(1, 2), Slot(2, 2), Slot(3, 2),
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
# Pool di formazioni per livello di difficolta'.
# Ai livelli bassi le formazioni sono piu' semplici (griglie, linee).
# Ai livelli alti si aggiungono formazioni piu' complesse.
# --------------------------------------------------------------------------
_POOLS = [
    ["GRID_4x2", "H_LINE", "GRID_3x3"],                                # Lv 0
    ["GRID_4x2", "H_LINE", "GRID_3x3", "V_SHAPE"],                     # Lv 1
    ["GRID_3x3", "V_SHAPE", "DIAMOND", "Z_LINE"],                       # Lv 2
    ["V_SHAPE", "DIAMOND", "Z_LINE", "PINCER", "ARROW", "GRID_3x3"],    # Lv 3+
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
    """Trova una posizione X che non si sovrapponga ai gruppi esistenti.

    L'intera larghezza dello schermo (con margini di 15px) viene usata
    come range di posizionamento. Se ci sono gruppi attivi nella parte
    alta dello schermo, le loro fasce X vengono evitate con un padding
    di sicurezza.

    Tenta prima un posizionamento casuale. Se tutti i tentativi falliscono
    per overlap, cerca il gap piu' ampio tra le zone occupate.

    Args:
        formation_width: Larghezza totale della formazione in pixel.
        existing_groups: Lista di FormationGroup gia' presenti (puo' essere None).

    Returns:
        Coordinata X (int) per l'angolo sinistro della formazione.
    """
    # Range completo sullo schermo con margini laterali
    x_min = 15
    x_max = max(x_min, SCREEN_WIDTH - formation_width - 15)

    # Se non ci sono gruppi o la lista e' vuota, posizionamento casuale
    # con preferenza per la zona centrale
    if not existing_groups:
        center = (SCREEN_WIDTH - formation_width) // 2
        cx_min = max(x_min, center - 80)
        cx_max = min(x_max, center + 80)
        return random.randint(cx_min, cx_max)

    # Raccogli le fasce X occupate dai gruppi esistenti che sono ancora
    # nella parte alta dello schermo (quelli che potrebbero sovrapporsi
    # verticalmente con un nuovo gruppo che spawna in cima)
    occupied = []
    _SAFETY = 20  # margine di sicurezza aggiuntivo per lato
    for g in existing_groups:
        alive = g.alive_enemies
        if not alive:
            continue
        # Consideriamo solo gruppi che non sono gia' scesi nella meta' bassa
        group_top = min(e.y for e in alive)
        if group_top > SCREEN_HEIGHT // 2:
            continue
        gl = min(e.x for e in alive) - _SAFETY
        gr = max(e.x + e.width for e in alive) + _SAFETY
        occupied.append((gl, gr))

    # Se nessuna zona occupata, posizionamento casuale centrato
    if not occupied:
        center = (SCREEN_WIDTH - formation_width) // 2
        cx_min = max(x_min, center - 80)
        cx_max = min(x_max, center + 80)
        return random.randint(cx_min, cx_max)

    # Tenta posizionamento casuale evitando le zone occupate
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

    # Fallback: cerca il gap piu' ampio tra le zone occupate
    occupied.sort()
    candidates = []  # (gap_size, x_position)

    # Gap prima della prima zona occupata
    if occupied[0][0] > x_min + formation_width:
        gap = occupied[0][0] - x_min
        cx = x_min + max(0, (gap - formation_width) // 2)
        candidates.append((gap, cx))

    # Gap tra zone occupate consecutive
    for i in range(len(occupied) - 1):
        gap_start = occupied[i][1]
        gap_end = occupied[i + 1][0]
        gap = gap_end - gap_start
        if gap >= formation_width:
            cx = int(gap_start + (gap - formation_width) // 2)
            candidates.append((gap, cx))

    # Gap dopo l'ultima zona occupata
    gap_after = SCREEN_WIDTH - occupied[-1][1]
    if gap_after >= formation_width:
        cx = max(x_min, int(occupied[-1][1]))
        candidates.append((gap_after, cx))

    if candidates:
        # Scegli il gap piu' ampio
        candidates.sort(reverse=True)
        _, best_x = candidates[0]
        return max(x_min, min(x_max, best_x))

    # Ultimo fallback: posizionamento casuale (overlap inevitabile su schermi stretti)
    return random.randint(x_min, x_max)
