"""
Boss -- 5 varianti con animazione GIF, pattern laser unici, scaling progressivo.

Varianti:
- Boss 0 (boss.gif):   Classico, 4 cannoni, pattern standard.
- Boss 1 (boss_1.gif): Burst veloce, spara in sequenza rapida dai cannoni esterni.
- Boss 2 (boss_2.gif): Ventaglio, spara a ventaglio da un punto centrale.
- Boss 3 (boss_3.gif): Spirale, laser a cerchio rotante.
- Boss 4 (boss_4.png): Shotgun, raffica densa in cono largo.

Ad ogni sconfitta le statistiche scalano (piu' HP, piu' veloce,
intervallo sparo ridotto) e la variante del boss successivo cambia.
"""
import math
import random
import pygame

from core.constants import (
    SCREEN_WIDTH, WHITE, RED, GREEN, YELLOW, ORANGE, CYAN, MAGENTA,
    NUM_BOSS_VARIANTS,
)
from core.assets import Assets
from entities.laser import Laser


class Boss:
    """Boss con animazione GIF, pattern laser unici e barra vita.

    Args:
        variant: Indice della variante del boss (0-4).
    """

    def __init__(self, variant: int = 0):
        self.variant = variant % NUM_BOSS_VARIANTS
        self.width  = 200
        self.height = 94
        self.x = float(SCREEN_WIDTH // 2 - self.width // 2)
        self.y = float(-self.height)

        self.target_y = 30
        self.entering = True
        self.alive = True

        # Statistiche (possono essere sovrascritte da game.py)
        self.max_hp = 60
        self.hp     = self.max_hp

        # Movimento orizzontale
        self.h_speed = random.choice([-2.5, -2.0, -1.5, 1.5, 2.0, 2.5])
        self.h_dir_timer    = 0
        self.h_dir_interval = random.randint(120, 300)

        # Animazione GIF
        self.frames      = Assets.boss_variant_frames[self.variant]
        self.frame_idx   = 0
        self.frame_timer = 0
        self.frame_delay = 6

        # Posizioni cannoni (percentuali rispetto a width/height)
        self.cannon_offsets = [
            (0.12, 0.85),
            (0.38, 0.95),
            (0.62, 0.95),
            (0.88, 0.85),
        ]

        # Sparo
        self.shoot_timer    = 0
        self.shoot_interval = 40

        # Effetto hit: pulsazione sottile
        self.hit_flash     = 0
        self.hit_flash_max = 8

        # Contatore pattern per la variante spirale
        self._spiral_angle = 0.0

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(self) -> list:
        """Aggiorna il boss: movimento, animazione e sparo.

        Returns:
            Lista di Laser sparati in questo frame (vuota se nessuno).
        """
        if not self.alive:
            return []

        # Fase di ingresso
        if self.entering:
            self.y += 1.5
            if self.y >= self.target_y:
                self.y = float(self.target_y)
                self.entering = False
            return []

        # Movimento orizzontale
        self.x += self.h_speed
        self.h_dir_timer += 1
        if self.h_dir_timer >= self.h_dir_interval:
            self.h_speed = random.choice([-2.5, -2.0, -1.5, 1.5, 2.0, 2.5])
            self.h_dir_timer = 0
            self.h_dir_interval = random.randint(120, 300)

        # Rimbalzo ai bordi
        if self.x <= 10:
            self.x = 10.0
            self.h_speed = abs(self.h_speed)
        elif self.x >= SCREEN_WIDTH - self.width - 10:
            self.x = float(SCREEN_WIDTH - self.width - 10)
            self.h_speed = -abs(self.h_speed)

        # Animazione GIF
        self.frame_timer += 1
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            if self.frames:
                self.frame_idx = (self.frame_idx + 1) % len(self.frames)

        # Hit flash countdown
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # Sparo
        self.shoot_timer += 1
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            return self._fire()
        return []

    # ------------------------------------------------------------------
    # PATTERN DI SPARO PER VARIANTE
    # ------------------------------------------------------------------

    def _fire(self) -> list:
        """Esegue il pattern di sparo basato sulla variante del boss."""
        if self.variant == 0:
            return self._fire_classic()
        elif self.variant == 1:
            return self._fire_burst()
        elif self.variant == 2:
            return self._fire_fan()
        elif self.variant == 3:
            return self._fire_spiral()
        elif self.variant == 4:
            return self._fire_shotgun()
        return self._fire_classic()

    def _cannon_pos(self, idx: int) -> tuple[float, float]:
        """Calcola la posizione assoluta di un cannone."""
        ox, oy = self.cannon_offsets[idx]
        return (self.x + int(self.width * ox) - 2,
                self.y + int(self.height * oy))

    def _fire_classic(self) -> list:
        """Variante 0: pattern classico con 3 modalita' casuali."""
        pattern = random.randint(0, 2)
        lasers: list[Laser] = []

        if pattern == 0:
            for i in range(4):
                cx, cy = self._cannon_pos(i)
                lasers.append(Laser(cx, cy, 5, ORANGE, is_enemy=True))
        elif pattern == 1:
            for i in [0, 3]:
                cx, cy = self._cannon_pos(i)
                lasers.append(Laser(cx, cy, 6, RED, is_enemy=True))
        else:
            for i in [1, 2]:
                cx, cy = self._cannon_pos(i)
                lasers.append(Laser(cx, cy, 7, YELLOW, is_enemy=True))
        return lasers

    def _fire_burst(self) -> list:
        """Variante 1: burst veloce -- 3 laser ravvicinati dai cannoni esterni."""
        lasers: list[Laser] = []
        for i in [0, 3]:
            cx, cy = self._cannon_pos(i)
            for dy in [0, 8, 16]:
                lasers.append(Laser(cx, cy + dy, 6, CYAN, is_enemy=True))
        return lasers

    def _fire_fan(self) -> list:
        """Variante 2: ventaglio -- laser in 5 direzioni dal centro."""
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height
        angles = [-40, -20, 0, 20, 40]

        for angle_deg in angles:
            rad = math.radians(angle_deg)
            vx = math.sin(rad) * 4
            vy = math.cos(rad) * 5
            lasers.append(Laser(
                center_x - 2, center_y, vy, MAGENTA,
                is_enemy=True, vx=vx))
        return lasers

    def _fire_spiral(self) -> list:
        """Variante 3: spirale -- 2 laser rotanti ad ogni sparo."""
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        for offset in [0, math.pi]:
            angle = self._spiral_angle + offset
            vx = math.sin(angle) * 3.5
            vy = math.cos(angle) * 4.0 + 1.5
            lasers.append(Laser(
                center_x - 2, center_y, vy, GREEN,
                is_enemy=True, vx=vx))

        self._spiral_angle += 0.5
        return lasers

    def _fire_shotgun(self) -> list:
        """Variante 4: shotgun -- raffica densa in cono largo."""
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        n_shots = random.randint(5, 8)
        for _ in range(n_shots):
            spread = random.uniform(-50, 50)
            rad = math.radians(spread)
            vx = math.sin(rad) * 3
            vy = random.uniform(4, 7)
            lasers.append(Laser(
                center_x + random.randint(-15, 15),
                center_y,
                vy, YELLOW, is_enemy=True, vx=vx))
        return lasers

    # ------------------------------------------------------------------
    # DANNO
    # ------------------------------------------------------------------

    def take_damage(self, amount: int = 1) -> bool:
        """Applica danno al boss e attiva il flash visivo.

        Args:
            amount: Quantita' di danno.

        Returns:
            True se il boss e' stato sconfitto.
        """
        self.hp -= amount
        self.hit_flash = self.hit_flash_max
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    # ------------------------------------------------------------------
    # DRAW
    # ------------------------------------------------------------------

    def draw(self, surf: pygame.Surface) -> None:
        """Disegna il boss con effetto pulsazione all'hit."""
        if not self.alive:
            return

        if not self.frames:
            return

        frame = self.frames[self.frame_idx % len(self.frames)]

        if self.hit_flash > 0:
            ratio = self.hit_flash / self.hit_flash_max
            pulse = int(4 * ratio)
            w2 = self.width + pulse * 2
            h2 = self.height + pulse * 2
            scaled = pygame.transform.scale(frame, (w2, h2))
            surf.blit(scaled, (int(self.x) - pulse, int(self.y) - pulse))
        else:
            scaled = pygame.transform.scale(frame, (self.width, self.height))
            surf.blit(scaled, (int(self.x), int(self.y)))

    def draw_health_bar(self, surf: pygame.Surface) -> None:
        """Disegna la barra vita del boss in cima allo schermo."""
        if not self.alive:
            return

        bw, bh = 400, 16
        bx = SCREEN_WIDTH // 2 - bw // 2
        by = 8

        # Sfondo
        pygame.draw.rect(surf, (12, 12, 18), (bx - 1, by - 1, bw + 2, bh + 2))
        pygame.draw.rect(surf, (40, 40, 55), (bx, by, bw, bh))

        # Barra vita
        pct = self.hp / self.max_hp
        if pct > 0.5:
            col = GREEN
        elif pct > 0.25:
            col = YELLOW
        else:
            col = RED

        fw = int(bw * pct)
        if fw > 0:
            pygame.draw.rect(surf, col, (bx, by, fw, bh))

        # Tacche di separazione (quarti)
        for s in range(1, 4):
            sx = bx + bw * s // 4
            pygame.draw.line(surf, (12, 12, 18), (sx, by), (sx, by + bh), 1)

        # Etichetta
        variant_names = ["BOSS", "BOSS BURST", "BOSS FAN", "BOSS SPIRAL", "BOSS SHOTGUN"]
        vname = variant_names[self.variant] if self.variant < len(variant_names) else "BOSS"
        font = pygame.font.Font(None, 20)
        label = font.render(f"{vname}  {self.hp}/{self.max_hp}", True, WHITE)
        surf.blit(label, (bx + bw // 2 - label.get_width() // 2, by + 1))

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del boss."""
        return pygame.Rect(
            self.x + 15,
            self.y + 10,
            self.width - 30,
            self.height - 15,
        )
