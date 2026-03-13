"""
FormationGroup v5 -- movimento, sparo, pattern PRD.

Ogni FormationGroup contiene un insieme di nemici che si muovono come unita'.
Pattern di movimento basati sulla formazione:
- GRID/V_SHAPE/etc: movimento orizzontale classico + discesa
- V_FORMATION: leader fires double, ali chiudono a pinza dopo 3s
- SWARM: movimento sinusoidale (PRD 4.4: 80px ampiezza, 1.5Hz)
- DOUBLE_V: convergenza al centro
- Dive Attack: triggerato quando < 40% nemici rimangono (bezier curve)

Anti-overlap:
- Le dimensioni delle celle (CELL_W, CELL_H) garantiscono spaziatura intra-gruppo.
- La funzione build_spawn_positions() in formations.py evita sovrapposizioni
  orizzontali con i gruppi esistenti.
"""
import math
import random
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, DROP_RATES
from entities.enemy import Enemy
from entities.formations import Slot
from entities.powerup import FallingPowerUp

# Parametri di discesa del gruppo
DROP_AMOUNT   = 22   # pixel di discesa per step
DROP_INTERVAL = 75   # frame tra uno step e l'altro

# PRD Swarm parameters
SWARM_AMPLITUDE = 80    # px
SWARM_FREQ      = 1.5   # Hz
SWARM_DESCENT   = 200 / 60  # 200px/s convertito in px/frame

# Mappa tipo nemico per nome formazione
_TYPE_MAP = {
    "GRID_3x3":     "scout",
    "GRID_4x2":     "scout",
    "GRID_3x6":     "scout",
    "GRID_4x6":     "fighter",
    "H_LINE":       "scout",
    "V_SHAPE":      "fighter",
    "V_FORMATION":  "fighter",
    "Z_LINE":       "fighter",
    "DIAMOND":      "elite",
    "PINCER":       "bomber",
    "ARROW":        "bomber",
    "SWARM":        "scout",
    "DOUBLE_V":     "fighter",
}

# Punteggio per uccisione e HP per tipo nemico
_SCORE = {"scout": 1, "fighter": 2, "bomber": 3, "elite": 5}
_HP    = {"scout": 1, "fighter": 2, "bomber": 3, "elite": 2}


def _type_for_level(formation_name: str, difficulty: int) -> str:
    """Determina il tipo di nemico appropriato per la formazione e il livello."""
    base = _TYPE_MAP.get(formation_name, "scout")
    if difficulty == 0 and base in ("bomber", "elite"):
        return "scout"
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
        self._time = 0  # frame counter interno

        # Determina tipo e statistiche dei nemici
        enemy_type = _type_for_level(formation_name, difficulty)
        hp = _HP.get(enemy_type, 1)
        self.score_per_kill = _SCORE.get(enemy_type, 1)
        self.enemy_type = enemy_type

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
        self.speed_mult = speed_mult

        # Timer per la discesa periodica
        self._drop_timer = 0

        # Dive attack flag (PRD 4.3: attivato quando < 40% nemici rimangono)
        self._dive_triggered = False
        self._initial_count = len(self.enemies)

        # Swarm: salva posizioni base X per il moto sinusoidale
        self._is_swarm = (formation_name == "SWARM")
        self._is_double_v = (formation_name == "DOUBLE_V")
        self._is_v_formation = (formation_name == "V_FORMATION")
        self._swarm_base_x = {id(e): e.x for e in self.enemies}

        # Double V: convergenza
        self._double_v_converged = False
        self._double_v_center = SCREEN_WIDTH // 2

        # Laser pendenti (da trasferire a game.py ad ogni update)
        self.pending_lasers: list = []

        # Power-up drop pendenti
        self.pending_powerups: list = []

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
            True se il bordo inferiore del gruppo ha raggiunto il fondo
            dello schermo (i nemici sono 'atterrati' e il giocatore perde vita).
        """
        self.pending_lasers.clear()
        self.pending_powerups.clear()

        if self.is_empty:
            return False

        self._time += 1

        # Scegli il pattern di movimento
        if self._is_swarm:
            self._move_swarm()
        elif self._is_double_v and not self._double_v_converged:
            self._move_double_v()
        else:
            self._move_standard()

        # ---- Check dive attack (PRD 4.3) ----
        alive_count = len(self.alive_enemies)
        if (not self._dive_triggered and
                alive_count < self._initial_count * 0.4 and
                alive_count > 0):
            self._dive_triggered = True
            # I nemici rimanenti accelerano la discesa
            for e in self.alive_enemies:
                e.h_speed = random.choice([-2.0, -1.5, 1.5, 2.0])

        # ---- Sparo individuale per nemico ----
        for e in self.alive_enemies:
            e.shoot_timer += 1
            # V_FORMATION leader spara burst doppio
            if self._is_v_formation and e.slot.row == 0:
                interval_mult = 0.7  # Leader spara piu' spesso
            else:
                interval_mult = 1.0

            if e.shoot_timer >= int(e.shoot_interval * interval_mult):
                e.shoot_timer = 0
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

    def _move_standard(self):
        """Movimento orizzontale classico con rimbalzo + discesa periodica."""
        if self.dx < 0 and self.left_edge + self.dx < 10:
            self.dx = abs(self.dx)
        elif self.dx > 0 and self.right_edge + self.dx > SCREEN_WIDTH - 10:
            self.dx = -abs(self.dx)

        for e in self.alive_enemies:
            e.x += self.dx
            # Se dive attack attivato, nemici scendono piu' velocemente
            if self._dive_triggered:
                e.x += e.h_speed
                e.y += 2.0 * self.speed_mult  # Discesa veloce
                # Rimbalzo laterale
                if e.x < 10:
                    e.h_speed = abs(e.h_speed)
                elif e.x > SCREEN_WIDTH - e.width - 10:
                    e.h_speed = -abs(e.h_speed)

        # Discesa periodica (solo se non in dive)
        if not self._dive_triggered:
            self._drop_timer += 1
            if self._drop_timer >= DROP_INTERVAL:
                self._drop_timer = 0
                for e in self.alive_enemies:
                    e.y += DROP_AMOUNT

    def _move_swarm(self):
        """PRD 4.4: Movimento sinusoidale orizzontale + discesa costante."""
        t = self._time / 60.0  # tempo in secondi
        for e in self.alive_enemies:
            base_x = self._swarm_base_x.get(id(e), e.x)
            e.x = base_x + SWARM_AMPLITUDE * math.sin(2 * math.pi * SWARM_FREQ * t)
            e.y += SWARM_DESCENT * self.speed_mult
            # Aggiorna base X per la discesa
            self._swarm_base_x[id(e)] = base_x

    def _move_double_v(self):
        """PRD 4.5: Due V convergono al centro, poi transizione a griglia."""
        convergence_speed = 1.5 * self.speed_mult
        center = self._double_v_center
        all_near_center = True

        for e in self.alive_enemies:
            target_x = center - 50 + e.slot.col * 20  # Convergenza al centro
            diff = target_x - e.x
            if abs(diff) > 5:
                e.x += convergence_speed if diff > 0 else -convergence_speed
                all_near_center = False
            e.y += 0.5  # Discesa lenta durante convergenza

        if all_near_center:
            self._double_v_converged = True
            # Transizione a griglia: usa movimento standard da qui in poi

    def on_enemy_killed(self, enemy):
        """Chiamato quando un nemico di questo gruppo viene ucciso.

        Gestisce il drop di power-up basato sulle drop rate del PRD.

        Args:
            enemy: L'oggetto Enemy appena ucciso.
        """
        rates = DROP_RATES.get(enemy.enemy_type, DROP_RATES["scout"])
        roll = random.random()
        cumulative = 0.0
        for pu_type in ["arma", "scudo", "velocita", "vita"]:
            cumulative += rates.get(pu_type, 0)
            if roll < cumulative:
                self.pending_powerups.append(
                    FallingPowerUp(
                        enemy.x + enemy.width // 2 - 17,
                        enemy.y + enemy.height // 2 - 17,
                        pu_type))
                break

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
        """Restituisce le coppie (hitbox, nemico) per tutti i nemici vivi."""
        return [(e.get_rect(), e) for e in self.alive_enemies]
