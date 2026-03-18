"""
Enemy -- sprite, shake all'hit e pattern laser per tipo.

Tipi supportati e relativi pattern di sparo:
- scout:   laser singolo veloce, intervallo breve
- fighter: laser doppio (offset laterale), intervallo intermedio
- bomber:  laser lento ma largo, lungo intervallo
- elite:   burst da 3 laser ravvicinati, intervallo medio

Effetto hit:
- Nemici con 1 HP: nessun feedback visivo (muoiono immediatamente).
- Nemici con piu' HP: *shake* (oscillazione rapida dello sprite) invece
  di un overlay bianco.  L'effetto e' identico a quello usato dal boss.
"""

import random
import pygame

from core.constants import ENEMY_W, ENEMY_H, RED, ORANGE, YELLOW, CYAN
from core.assets import Assets
from entities.formations import Slot

# ---------------------------------------------------------------------------
# Parametri shake all'hit (frame-based)
# ---------------------------------------------------------------------------
_SHAKE_DURATION  = 8     # frame totali dell'effetto shake
_SHAKE_AMPLITUDE = 3     # pixel massimi di oscillazione

# ---------------------------------------------------------------------------
# Colore del laser per ciascun tipo di nemico
# ---------------------------------------------------------------------------
_LASER_COLOR = {
    "scout":   RED,
    "fighter": ORANGE,
    "bomber":  (180, 0, 220),   # viola
    "elite":   CYAN,
    "default": RED,
}

# Velocita' del laser per ciascun tipo di nemico (pixel/frame)
_LASER_SPEED = {
    "scout":   6,
    "fighter": 5,
    "bomber":  3,
    "elite":   5,
    "default": 5,
}

# Intervallo di sparo (min, max) in frame per ciascun tipo
_SHOOT_INTERVAL = {
    "scout":   (70,  160),
    "fighter": (100, 200),
    "bomber":  (160, 320),
    "elite":   (80,  180),
    "default": (100, 200),
}


class Enemy:
    """Singolo nemico alieno con tipo, HP, sprite e pattern di sparo.

    Args:
        x:          Posizione X iniziale (angolo superiore sinistro).
        y:          Posizione Y iniziale.
        enemy_type: Tipo di nemico (``'scout'``, ``'fighter'``,
                    ``'bomber'``, ``'elite'``).
        hp:         Punti vita iniziali.
    """

    def __init__(self, x: float, y: float,
                 enemy_type: str = "scout", hp: int = 1):
        self.width  = ENEMY_W
        self.height = ENEMY_H
        self.x = x
        self.y = y
        self.alive = True

        self.enemy_type = enemy_type
        self.hp     = hp
        self.max_hp = hp

        # Velocita' orizzontale aggiuntiva (gestita dal FormationGroup)
        self.h_speed = 0.0

        # Timer e intervallo sparo individuale
        lo, hi = _SHOOT_INTERVAL.get(enemy_type, (100, 200))
        self.shoot_timer    = random.randint(0, hi)
        self.shoot_interval = random.randint(lo, hi)

        # Slot logico nella griglia della formazione
        self.slot: Slot = Slot(0, 0)

        # -- Effetto shake all'hit (nessun overlay bianco) --
        self._shake_timer = 0

    # ------------------------------------------------------------------
    # DANNO
    # ------------------------------------------------------------------

    def take_damage(self, amount: int = 1) -> bool:
        """Applica danno al nemico e attiva lo shake visivo.

        Lo shake viene attivato **solo** se il nemico sopravvive (multi-HP).
        Se il nemico muore, non c'e' bisogno di feedback perche' segue
        immediatamente l'esplosione.

        Args:
            amount: Quantita' di danno da applicare.

        Returns:
            ``True`` se il nemico e' stato ucciso, ``False`` altrimenti.
        """
        self.hp -= amount
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        # Nemico sopravvive: attiva lo shake
        self._shake_timer = _SHAKE_DURATION
        return False

    # ------------------------------------------------------------------
    # SPRITE
    # ------------------------------------------------------------------

    def _sprite(self) -> pygame.Surface:
        """Restituisce lo sprite appropriato per il tipo di nemico.

        Tutti i tipi usano ``alien.png`` come sprite base.  Il mapping
        esiste per eventuali future differenziazioni grafiche.
        """
        sprite_map = {
            "scout":   Assets.enemy_scout_sprite,
            "fighter": Assets.enemy_fighter_sprite,
            "bomber":  Assets.enemy_bomber_sprite,
            "elite":   Assets.enemy_elite_sprite,
        }
        sprite = sprite_map.get(self.enemy_type)
        return sprite if sprite is not None else Assets.alien_sprite

    # ------------------------------------------------------------------
    # LASER
    # ------------------------------------------------------------------

    def build_lasers(self) -> list:
        """Costruisce i laser secondo il pattern del tipo di nemico.

        Returns:
            Lista di oggetti ``Laser`` pronti per essere aggiunti al gioco.
        """
        from entities.laser import Laser

        cx  = self.x + self.width // 2   # centro X del nemico
        by  = self.y + self.height       # bordo inferiore
        spd = _LASER_SPEED.get(self.enemy_type, 5)
        col = _LASER_COLOR.get(self.enemy_type, RED)
        lasers: list[Laser] = []

        if self.enemy_type == "scout":
            # Laser singolo centrale
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))

        elif self.enemy_type == "fighter":
            # Due laser paralleli (offset +-10 px)
            lasers.append(Laser(cx - 10, by, spd, col, is_enemy=True))
            lasers.append(Laser(cx + 8,  by, spd, col, is_enemy=True))

        elif self.enemy_type == "bomber":
            # Laser largo e lento
            lasers.append(Laser(cx - 3, by, spd, col, is_enemy=True))

        elif self.enemy_type == "elite":
            # Burst di 3 laser in rapida successione (offset Y)
            for dy in [0, 6, 12]:
                lasers.append(Laser(cx - 2, by + dy, spd, col, is_enemy=True))
        else:
            # Tipo sconosciuto: laser singolo di default
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))

        return lasers

    # ------------------------------------------------------------------
    # DRAW
    # ------------------------------------------------------------------

    def draw(self, surf: pygame.Surface) -> None:
        """Disegna lo sprite del nemico con eventuale effetto shake all'hit.

        Lo shake consiste in un rapido offset orizzontale alternato che
        decresce col tempo, identico al feedback del boss.  Non viene
        disegnato nessun overlay bianco sulla hitbox.

        Args:
            surf: Surface di destinazione.
        """
        if not self.alive:
            return

        # Calcola offset di shake (decresce proporzionalmente al timer)
        offset_x = 0
        if self._shake_timer > 0:
            ratio = self._shake_timer / _SHAKE_DURATION
            offset_x = int(_SHAKE_AMPLITUDE * ratio) * (
                1 if self._shake_timer % 2 == 0 else -1)
            self._shake_timer -= 1

        sprite = self._sprite()
        surf.blit(sprite, (int(self.x + offset_x), int(self.y)))

    # ------------------------------------------------------------------
    # HITBOX
    # ------------------------------------------------------------------

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del nemico, ridotta rispetto allo sprite.

        La riduzione rende le collisioni piu' 'fair' per il giocatore.
        Shrink: 6 px per lato orizzontale, 4 px per lato verticale.
        """
        sx, sy = 6, 4
        return pygame.Rect(
            self.x + sx,
            self.y + sy,
            self.width - sx * 2,
            self.height - sy * 2,
        )
