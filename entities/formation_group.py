"""
FormationGroup v6 -- movimento, sparo, anti-overlap e tipi misti.

Ogni ``FormationGroup`` contiene un insieme di nemici che si muovono come
unita'. Le formazioni hanno tipi di nemico misti: nemici deboli (scout)
nelle righe frontali e nemici forti (elite, bomber) nelle righe posteriori.
"""

import random
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ENEMY_TYPE_STATS
from entities.enemy import Enemy
from entities.formations import Slot

# ---------------------------------------------------------------------------
# Parametri di discesa del gruppo
# ---------------------------------------------------------------------------
DROP_AMOUNT   = 22   # pixel di discesa per step
DROP_INTERVAL = 75   # frame tra uno step e l'altro

# ---------------------------------------------------------------------------
# Mappa tipi di nemico per riga.
# Riga 0 (frontale) = scout/fighter, righe alte = bomber/elite
# ---------------------------------------------------------------------------
_ROW_TYPE_MAP: dict[int, list[str]] = {
    0: ["scout"],                      # Riga frontale: sempre scout
    1: ["scout", "fighter"],           # Seconda riga: scout o fighter
    2: ["fighter", "bomber"],          # Terza riga: fighter o bomber
    3: ["bomber", "elite"],            # Quarta riga: tipi forti
}

# Tipi disponibili per livello di difficolta'
_DIFFICULTY_TYPES: list[list[str]] = [
    ["scout"],                                  # Lv 0
    ["scout", "fighter"],                       # Lv 1
    ["scout", "fighter", "bomber"],             # Lv 2
    ["scout", "fighter", "bomber", "elite"],    # Lv 3+
]

# HP e punteggio per tipo nemico (da constants)
_SCORE: dict[str, int] = {k: v["score"] for k, v in ENEMY_TYPE_STATS.items()}
_HP:    dict[str, int] = {k: v["hp"] for k, v in ENEMY_TYPE_STATS.items()}


def _pick_enemy_type(row: int, difficulty: int) -> str:
    """Sceglie il tipo di nemico in base alla riga e alla difficolta'.

    Nemici deboli davanti, forti dietro. La difficolta' controlla
    quali tipi sono disponibili.

    Args:
        row:        Indice della riga nella formazione (0 = piu' in basso/frontale).
        difficulty: Livello di difficolta' corrente.

    Returns:
        Stringa con il tipo di nemico.
    """
    # Tipi disponibili per questa difficolta'
    diff_idx = min(difficulty, len(_DIFFICULTY_TYPES) - 1)
    available = _DIFFICULTY_TYPES[diff_idx]

    # Tipi suggeriti per la riga
    row_types = _ROW_TYPE_MAP.get(row, ["fighter", "bomber", "elite"])

    # Intersezione: solo tipi disponibili per la riga E la difficolta'
    candidates = [t for t in row_types if t in available]
    if not candidates:
        # Fallback: usa il tipo piu' debole disponibile
        candidates = [available[0]]

    return random.choice(candidates)


class FormationGroup:
    """Gruppo di nemici in formazione che si muove come unita'.

    Le formazioni ora hanno tipi MISTI: nemici deboli (scout) nelle righe
    frontali e nemici forti (bomber, elite) nelle righe posteriori.

    Args:
        spawn_data:     Lista di dict con ``'x'``, ``'y'``, ``'slot'``
                        per ogni nemico.
        speed_mult:     Moltiplicatore di velocita'.
        formation_name: Nome della formazione.
        difficulty:     Livello di difficolta' corrente.
    """

    def __init__(self, spawn_data: list[dict], speed_mult: float = 1.0,
                 formation_name: str = "", difficulty: int = 0):
        self.formation_name = formation_name

        # Determina le righe presenti nella formazione
        max_row = max((d["slot"].row for d in spawn_data), default=0)

        # Crea i nemici con tipi misti basati sulla riga
        self.enemies: list[Enemy] = []
        self.score_per_kill = 1  # default, verra' sovrascritto per nemico

        for d in spawn_data:
            slot: Slot = d["slot"]
            # Inverti: riga 0 nello slot = riga piu' alta (dietro),
            # max_row = riga piu' bassa (frontale/davanti)
            front_row = max_row - slot.row
            enemy_type = _pick_enemy_type(front_row, difficulty)
            hp = _HP.get(enemy_type, 1)

            enemy = Enemy(d["x"], d["y"], enemy_type=enemy_type, hp=hp)
            enemy.slot = slot
            self.enemies.append(enemy)

        # Velocita' orizzontale del gruppo (scalata per difficolta')
        base_speed = random.choice([-1.0, -0.7, 0.7, 1.0]) * speed_mult
        self.dx = base_speed

        # Timer per la discesa periodica
        self._drop_timer = 0

        # Cache dei nemici vivi
        self._cached_alive: list[Enemy] = list(self.enemies)

        # Laser pendenti
        self.pending_lasers: list = []

    # ------------------------------------------------------------------
    # Proprieta' di accesso rapido
    # ------------------------------------------------------------------

    @property
    def alive_enemies(self) -> list[Enemy]:
        return self._cached_alive

    def _refresh_alive_cache(self) -> None:
        self._cached_alive = [e for e in self.enemies if e.alive]

    @property
    def is_empty(self) -> bool:
        return all(not e.alive for e in self.enemies)

    @property
    def left_edge(self) -> float:
        alive = self.alive_enemies
        return min(e.x for e in alive) if alive else 0.0

    @property
    def right_edge(self) -> float:
        alive = self.alive_enemies
        return max(e.x + e.width for e in alive) if alive else 0.0

    @property
    def bottom_edge(self) -> float:
        alive = self.alive_enemies
        return max(e.y + e.height for e in alive) if alive else 0.0

    @property
    def top_edge(self) -> float:
        alive = self.alive_enemies
        return min(e.y for e in alive) if alive else 0.0

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(self) -> bool:
        """Aggiorna il gruppo: movimento, sparo e controllo bordi.

        Returns:
            ``True`` se il bordo inferiore ha raggiunto il fondo dello schermo.
        """
        self.pending_lasers.clear()
        self._refresh_alive_cache()

        if not self._cached_alive:
            return False

        # Movimento orizzontale con rimbalzo
        if self.dx < 0 and self.left_edge + self.dx < 10:
            self.dx = abs(self.dx)
        elif self.dx > 0 and self.right_edge + self.dx > SCREEN_WIDTH - 10:
            self.dx = -abs(self.dx)

        for e in self.alive_enemies:
            e.x += self.dx

        # Discesa periodica
        self._drop_timer += 1
        if self._drop_timer >= DROP_INTERVAL:
            self._drop_timer = 0
            for e in self.alive_enemies:
                e.y += DROP_AMOUNT

        # Sparo individuale per nemico
        for e in self.alive_enemies:
            e.shoot_timer += 1
            if e.shoot_timer >= e.shoot_interval:
                e.shoot_timer = 0
                intervals: dict[str, tuple[int, int]] = {
                    "scout":   (70, 160),
                    "fighter": (100, 200),
                    "bomber":  (160, 320),
                    "elite":   (80, 180),
                }
                lo, hi = intervals.get(e.enemy_type, (100, 200))
                e.shoot_interval = random.randint(lo, hi)
                self.pending_lasers.extend(e.build_lasers())

        return self.bottom_edge >= SCREEN_HEIGHT

    # ------------------------------------------------------------------
    # DRAW
    # ------------------------------------------------------------------

    def draw(self, surf: pygame.Surface) -> None:
        for e in self.alive_enemies:
            e.draw(surf)

    # ------------------------------------------------------------------
    # COLLISIONI
    # ------------------------------------------------------------------

    def get_alive_rects(self) -> list[tuple[pygame.Rect, Enemy]]:
        return [(e.get_rect(), e) for e in self.alive_enemies]

    def get_score_for_enemy(self, enemy: Enemy) -> int:
        """Restituisce il punteggio per aver ucciso un nemico specifico."""
        return _SCORE.get(enemy.enemy_type, 1)
