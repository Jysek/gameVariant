"""
FormationGroup v7 -- movimento, sparo, anti-sovrapposizione e tipi misti.

Ogni ``FormationGroup`` contiene un insieme di nemici che si muovono come
un'unità. Le formazioni hanno tipi misti: nemici deboli (scout) nelle righe
frontali e nemici forti (elite, bomber) nelle righe posteriori.
"""

import random
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, ENEMY_TYPE_STATS,
    ENEMY_SHOOT_INTERVALS,
)
from entities.enemy import Enemy
from entities.formations import Slot

# ---------------------------------------------------------------------------
# Parametri discesa gruppo
# ---------------------------------------------------------------------------
DROP_AMOUNT   = 22  # pixel per step di discesa
DROP_INTERVAL = 75  # frame tra gli step

# ---------------------------------------------------------------------------
# Mappa tipo nemico per riga.
# Riga 0 (fronte) = scout/fighter, righe superiori = bomber/elite.
# ---------------------------------------------------------------------------
_ROW_TYPE_MAP: dict[int, list[str]] = {
    0: ["scout"],
    1: ["scout", "fighter"],
    2: ["fighter", "bomber"],
    3: ["bomber", "elite"],
}

# Tipi disponibili per livello di difficoltà
_DIFFICULTY_TYPES: list[list[str]] = [
    ["scout"],
    ["scout", "fighter"],
    ["scout", "fighter", "bomber"],
    ["scout", "fighter", "bomber", "elite"],
]

# Punteggio e HP per tipo nemico (dalle costanti)
_SCORE: dict[str, int] = {k: v["score"] for k, v in ENEMY_TYPE_STATS.items()}
_HP:    dict[str, int] = {k: v["hp"] for k, v in ENEMY_TYPE_STATS.items()}


def _pick_enemy_type(row: int, difficulty: int) -> str:
    """Sceglie un tipo nemico in base alla posizione nella riga e alla difficoltà.

    Nemici deboli davanti, nemici forti dietro. La difficoltà controlla
    quali tipi sono disponibili.

    Args:
        row:        Indice riga nella formazione (0 = fronte/più basso).
        difficulty: Livello di difficoltà corrente.

    Returns:
        Stringa tipo nemico.
    """
    diff_idx = min(difficulty, len(_DIFFICULTY_TYPES) - 1)
    available = _DIFFICULTY_TYPES[diff_idx]

    row_types = _ROW_TYPE_MAP.get(row, ["fighter", "bomber", "elite"])
    candidates = [t for t in row_types if t in available]
    if not candidates:
        candidates = [available[0]]

    return random.choice(candidates)


class FormationGroup:
    """Gruppo di nemici in formazione che si muovono come unità.

    Le formazioni hanno tipi misti: nemici deboli (scout) nelle righe
    frontali e nemici forti (bomber, elite) nelle righe posteriori.

    Args:
        spawn_data:     Lista di dict con 'x', 'y', 'slot' per ogni nemico.
        speed_mult:     Moltiplicatore velocità dalla difficoltà.
        formation_name: Nome del pattern di formazione.
        difficulty:     Livello di difficoltà corrente.
    """

    def __init__(
        self, spawn_data: list[dict], speed_mult: float = 1.0,
        formation_name: str = "", difficulty: int = 0,
    ):
        self.formation_name = formation_name

        # Determina le righe presenti nella formazione
        max_row = max((d["slot"].row for d in spawn_data), default=0)

        # Crea nemici con tipi misti basati sulla riga
        self.enemies: list[Enemy] = []

        for d in spawn_data:
            slot: Slot = d["slot"]
            front_row = max_row - slot.row
            enemy_type = _pick_enemy_type(front_row, difficulty)
            hp = _HP.get(enemy_type, 1)

            enemy = Enemy(d["x"], d["y"], enemy_type=enemy_type, hp=hp)
            enemy.slot = slot
            self.enemies.append(enemy)

        # Velocità orizzontale del gruppo (scalata dalla difficoltà)
        base_speed = random.choice([-1.0, -0.7, 0.7, 1.0]) * speed_mult
        self.dx = base_speed

        # Timer discesa periodica
        self._drop_timer = 0

        # Cache lista nemici vivi
        self._cached_alive: list[Enemy] = list(self.enemies)

        # Laser pendenti da questo frame
        self.pending_lasers: list = []

    # ------------------------------------------------------------------
    # Proprietà di accesso rapido
    # ------------------------------------------------------------------

    @property
    def alive_enemies(self) -> list[Enemy]:
        """Restituisce lista dei nemici attualmente vivi (cached)."""
        return self._cached_alive

    def _refresh_alive_cache(self) -> None:
        """Ricostruisce la cache dei nemici vivi."""
        self._cached_alive = [e for e in self.enemies if e.alive]

    @property
    def is_empty(self) -> bool:
        """Controlla se tutti i nemici in questo gruppo sono morti."""
        return all(not e.alive for e in self.enemies)

    @property
    def left_edge(self) -> float:
        """Restituisce la posizione X più a sinistra dei nemici vivi."""
        alive = self.alive_enemies
        return min(e.x for e in alive) if alive else 0.0

    @property
    def right_edge(self) -> float:
        """Restituisce la posizione X più a destra dei nemici vivi."""
        alive = self.alive_enemies
        return max(e.x + e.width for e in alive) if alive else 0.0

    @property
    def bottom_edge(self) -> float:
        """Restituisce la posizione Y più bassa dei nemici vivi."""
        alive = self.alive_enemies
        return max(e.y + e.height for e in alive) if alive else 0.0

    @property
    def top_edge(self) -> float:
        """Restituisce la posizione Y più alta dei nemici vivi."""
        alive = self.alive_enemies
        return min(e.y for e in alive) if alive else 0.0

    # ------------------------------------------------------------------
    # AGGIORNAMENTO
    # ------------------------------------------------------------------

    def update(self) -> bool:
        """Aggiorna il gruppo: movimento, sparo e controllo bordi.

        Returns:
            True se il bordo inferiore ha raggiunto il fondo dello schermo.
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

        # Sparo individuale dei nemici (usa intervalli centralizzati)
        for e in self.alive_enemies:
            e.shoot_timer += 1
            if e.shoot_timer >= e.shoot_interval:
                e.shoot_timer = 0
                lo, hi = ENEMY_SHOOT_INTERVALS.get(
                    e.enemy_type, (100, 200))
                e.shoot_interval = random.randint(lo, hi)
                self.pending_lasers.extend(e.build_lasers())

        return self.bottom_edge >= SCREEN_HEIGHT

    # ------------------------------------------------------------------
    # DISEGNO
    # ------------------------------------------------------------------

    def draw(self, surf: pygame.Surface) -> None:
        """Disegna tutti i nemici vivi in questo gruppo.

        Args:
            surf: Surface di destinazione.
        """
        for e in self.alive_enemies:
            e.draw(surf)

    # ------------------------------------------------------------------
    # HELPER DI COLLISIONE
    # ------------------------------------------------------------------

    def get_alive_rects(self) -> list[tuple[pygame.Rect, Enemy]]:
        """Restituisce coppie (hitbox, nemico) per tutti i nemici vivi."""
        return [(e.get_rect(), e) for e in self.alive_enemies]

    def get_score_for_enemy(self, enemy: Enemy) -> int:
        """Restituisce il valore in punteggio per l'uccisione di un nemico.

        Args:
            enemy: Il nemico ucciso.

        Returns:
            Valore punteggio basato sul tipo nemico.
        """
        return _SCORE.get(enemy.enemy_type, 1)
