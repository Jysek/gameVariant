"""
FormationGroup v4 -- movimento, sparo, anti-overlap assoluto.

Ogni FormationGroup contiene un insieme di nemici che si muovono come unita':
- Movimento orizzontale con rimbalzo ai bordi.
- Discesa periodica (ogni DROP_INTERVAL frame scendono di DROP_AMOUNT pixel).
- I nemici sparano individualmente secondo il loro tipo e intervallo.

Anti-overlap:
- Le dimensioni delle celle (CELL_W, CELL_H) garantiscono spaziatura intra-gruppo.
- La funzione build_spawn_positions() in formations.py evita sovrapposizioni
  orizzontali con i gruppi esistenti.
- game.py controlla _can_spawn_group() per evitare sovrapposizioni verticali.
"""
import random
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from entities.enemy import Enemy
from entities.formations import Slot

# Parametri di discesa del gruppo
DROP_AMOUNT   = 22   # pixel di discesa per step
DROP_INTERVAL = 75   # frame tra uno step e l'altro

# Mappa tipo nemico per nome formazione
_TYPE_MAP = {
    "GRID_3x3": "scout",
    "GRID_4x2": "scout",
    "H_LINE":   "scout",
    "V_SHAPE":  "fighter",
    "Z_LINE":   "fighter",
    "DIAMOND":  "elite",
    "PINCER":   "bomber",
    "ARROW":    "bomber",
}

# Punteggio per uccisione e HP per tipo nemico
_SCORE = {"scout": 1, "fighter": 2, "bomber": 3, "elite": 5}
_HP    = {"scout": 1, "fighter": 2, "bomber": 3, "elite": 2}


def _type_for_level(formation_name: str, difficulty: int) -> str:
    """Determina il tipo di nemico appropriato per la formazione e il livello.

    Ai livelli bassi i tipi avanzati vengono degradati a tipi piu' semplici
    per garantire una curva di difficolta' progressiva.

    Args:
        formation_name: Nome della formazione (es. "DIAMOND").
        difficulty: Livello di difficolta' corrente.

    Returns:
        Stringa con il tipo di nemico (es. "scout", "fighter", "bomber", "elite").
    """
    base = _TYPE_MAP.get(formation_name, "scout")
    # Livello 0: solo scout
    if difficulty == 0 and base in ("bomber", "elite"):
        return "scout"
    # Livello 1: no elite ancora
    if difficulty <= 1 and base == "elite":
        return "fighter"
    return base


class FormationGroup:
    """Gruppo di nemici in formazione che si muove come unita'.

    Args:
        spawn_data: Lista di dict con 'x', 'y', 'slot' per ogni nemico.
        speed_mult: Moltiplicatore di velocita' (basato sulla difficolta').
        formation_name: Nome della formazione (per determinare il tipo di nemico).
        difficulty: Livello di difficolta' corrente.
    """

    def __init__(self, spawn_data, speed_mult=1.0, formation_name="", difficulty=0):
        self.formation_name = formation_name

        # Determina tipo e statistiche dei nemici
        enemy_type = _type_for_level(formation_name, difficulty)
        hp = _HP.get(enemy_type, 1)
        self.score_per_kill = _SCORE.get(enemy_type, 1)

        # Crea i nemici alle posizioni calcolate
        self.enemies = [
            Enemy(d["x"], d["y"], enemy_type=enemy_type, hp=hp)
            for d in spawn_data
        ]
        # Assegna lo slot logico a ciascun nemico
        for enemy, data in zip(self.enemies, spawn_data):
            enemy.slot = data["slot"]

        # Velocita' orizzontale del gruppo (scalata per difficolta')
        base_speed = random.choice([-1.0, -0.7, 0.7, 1.0]) * speed_mult
        self.dx = base_speed

        # Timer per la discesa periodica
        self._drop_timer = 0

        # Laser pendenti (da trasferire a game.py ad ogni update)
        self.pending_lasers: list = []

    # ------------------------------------------------------------------
    # Proprieta' di accesso rapido
    # ------------------------------------------------------------------

    @property
    def alive_enemies(self) -> list[Enemy]:
        """Restituisce la lista dei nemici ancora vivi."""
        return [e for e in self.enemies if e.alive]

    @property
    def is_empty(self) -> bool:
        """True se tutti i nemici del gruppo sono morti."""
        return all(not e.alive for e in self.enemies)

    @property
    def left_edge(self) -> float:
        """Coordinata X del bordo sinistro del gruppo."""
        alive = self.alive_enemies
        return min(e.x for e in alive) if alive else 0.0

    @property
    def right_edge(self) -> float:
        """Coordinata X del bordo destro del gruppo (inclusa larghezza sprite)."""
        alive = self.alive_enemies
        return max(e.x + e.width for e in alive) if alive else 0.0

    @property
    def bottom_edge(self) -> float:
        """Coordinata Y del bordo inferiore del gruppo."""
        alive = self.alive_enemies
        return max(e.y + e.height for e in alive) if alive else 0.0

    @property
    def top_edge(self) -> float:
        """Coordinata Y del bordo superiore del gruppo."""
        alive = self.alive_enemies
        return min(e.y for e in alive) if alive else 0.0

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(self) -> bool:
        """Aggiorna il gruppo: movimento, sparo e controllo bordi.

        Returns:
            True se il bordo inferiore del gruppo ha raggiunto il fondo
            dello schermo (i nemici sono 'atterrati' e il giocatore perde vita).
        """
        self.pending_lasers.clear()

        if self.is_empty:
            return False

        # ---- Movimento orizzontale con rimbalzo ----
        if self.dx < 0 and self.left_edge + self.dx < 10:
            self.dx = abs(self.dx)
        elif self.dx > 0 and self.right_edge + self.dx > SCREEN_WIDTH - 10:
            self.dx = -abs(self.dx)

        for e in self.alive_enemies:
            e.x += self.dx

        # ---- Discesa periodica ----
        self._drop_timer += 1
        if self._drop_timer >= DROP_INTERVAL:
            self._drop_timer = 0
            for e in self.alive_enemies:
                e.y += DROP_AMOUNT

        # ---- Sparo individuale per nemico ----
        for e in self.alive_enemies:
            e.shoot_timer += 1
            if e.shoot_timer >= e.shoot_interval:
                e.shoot_timer = 0
                # Ricalcola il prossimo intervallo di sparo
                intervals = {
                    "scout":   (70, 160),
                    "fighter": (100, 200),
                    "bomber":  (160, 320),
                    "elite":   (80, 180),
                }
                lo, hi = intervals.get(e.enemy_type, (100, 200))
                e.shoot_interval = random.randint(lo, hi)
                self.pending_lasers.extend(e.build_lasers())

        # Controlla se il gruppo ha raggiunto il fondo
        return self.bottom_edge >= SCREEN_HEIGHT

    # ------------------------------------------------------------------
    # DRAW
    # ------------------------------------------------------------------

    def draw(self, surf):
        """Disegna tutti i nemici vivi del gruppo."""
        for e in self.alive_enemies:
            e.draw(surf)

    # ------------------------------------------------------------------
    # COLLISIONI
    # ------------------------------------------------------------------

    def get_alive_rects(self) -> list[tuple[pygame.Rect, Enemy]]:
        """Restituisce le coppie (hitbox, nemico) per tutti i nemici vivi.

        Le hitbox sono leggermente ridotte rispetto allo sprite per
        rendere le collisioni piu' 'fair' per il giocatore.
        """
        return [(e.get_rect(), e) for e in self.alive_enemies]
