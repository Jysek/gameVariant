"""
Enemy -- sprite e pattern laser per tipo.

Tipi supportati e relativi pattern di sparo:
- scout:   laser singolo veloce, intervallo breve
- fighter: laser doppio (offset laterale), intervallo intermedio
- bomber:  laser lento ma largo, lungo intervallo
- elite:   burst da 3 laser ravvicinati, intervallo medio
"""
import random
import pygame

from core.constants import ENEMY_SIZE, RED, ORANGE, YELLOW, CYAN
from core.assets import Assets
from entities.formations import Slot

# Durata del flash bianco all'hit (in frame)
_FLASH_DUR = 5

# Colore del laser per ciascun tipo di nemico
_LASER_COLOR = {
    "scout":   RED,
    "fighter": ORANGE,
    "bomber":  (180, 0, 220),   # viola
    "elite":   CYAN,
    "default": RED,
}

# Velocita' del laser per ciascun tipo di nemico
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
        x, y: Posizione iniziale (angolo superiore sinistro).
        enemy_type: Tipo di nemico ('scout', 'fighter', 'bomber', 'elite').
        hp: Punti vita iniziali.
    """

    def __init__(self, x, y, enemy_type="scout", hp=1):
        self.width  = ENEMY_SIZE
        self.height = ENEMY_SIZE
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

        # Effetto flash all'hit (contatore frame rimanenti)
        self._flash = 0
        self._flash_surf = None

    def take_damage(self, amount=1) -> bool:
        """Applica danno al nemico e attiva il flash visivo.

        Args:
            amount: Quantita' di danno da applicare.

        Returns:
            True se il nemico e' stato ucciso, False altrimenti.
        """
        self.hp -= amount
        self._flash = _FLASH_DUR
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def _sprite(self) -> pygame.Surface:
        """Restituisce lo sprite appropriato per il tipo di nemico."""
        sprite_map = {
            "scout":   Assets.enemy_scout_sprite,
            "fighter": Assets.enemy_fighter_sprite,
            "bomber":  Assets.enemy_bomber_sprite,
            "elite":   Assets.enemy_elite_sprite,
        }
        sprite = sprite_map.get(self.enemy_type)
        return sprite if sprite is not None else Assets.alien_sprite

    def build_lasers(self) -> list:
        """Costruisce i laser secondo il pattern del tipo di nemico.

        Returns:
            Lista di oggetti Laser pronti per essere aggiunti al gioco.
        """
        from entities.laser import Laser

        cx = self.x + self.width // 2   # centro X del nemico
        by = self.y + self.height       # bordo inferiore del nemico
        spd = _LASER_SPEED.get(self.enemy_type, 5)
        col = _LASER_COLOR.get(self.enemy_type, RED)
        lasers = []

        if self.enemy_type == "scout":
            # Laser singolo centrale
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))

        elif self.enemy_type == "fighter":
            # Due laser paralleli (offset +-10 px)
            lasers.append(Laser(cx - 10, by, spd, col, is_enemy=True))
            lasers.append(Laser(cx + 8,  by, spd, col, is_enemy=True))

        elif self.enemy_type == "bomber":
            # Laser largo e lento
            laser = Laser(cx - 3, by, spd, col, is_enemy=True)
            laser.width = 8
            lasers.append(laser)

        elif self.enemy_type == "elite":
            # Burst di 3 laser in rapida successione (offset Y)
            for dy in [0, 6, 12]:
                lasers.append(Laser(cx - 2, by + dy, spd, col, is_enemy=True))
        else:
            # Tipo sconosciuto: laser singolo di default
            lasers.append(Laser(cx - 2, by, spd, col, is_enemy=True))

        return lasers

    def draw(self, surf):
        """Disegna lo sprite del nemico con eventuale effetto flash all'hit."""
        if not self.alive:
            return

        sprite = self._sprite()
        surf.blit(sprite, (int(self.x), int(self.y)))

        # Flash bianco all'hit: overlay additivo temporaneo
        if self._flash > 0:
            self._flash -= 1
            ratio = self._flash / _FLASH_DUR
            sz = (self.width, self.height)
            if self._flash_surf is None or self._flash_surf.get_size() != sz:
                self._flash_surf = pygame.Surface(sz, pygame.SRCALPHA)
            self._flash_surf.fill((255, 255, 255, int(60 * ratio)))
            surf.blit(
                self._flash_surf, (int(self.x), int(self.y)),
                special_flags=pygame.BLEND_RGBA_ADD,
            )

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del nemico, leggermente ridotta rispetto allo sprite.

        La riduzione rende le collisioni piu' 'fair' per il giocatore.
        Shrink: 6px per lato (12px totali per asse).
        """
        shrink = 6
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width - shrink * 2,
            self.height - shrink * 2,
        )
