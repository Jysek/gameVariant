"""
Boss -- 5 varianti con animazione GIF, pattern laser unici, scaling progressivo.

Varianti (spawn CASUALE con uguale probabilita'):
- Boss 0 (Titano):      Classico, 4 cannoni con pattern rotanti.
- Boss 1 (Furia):       Burst veloce, raffiche ravvicinate devastanti.
- Boss 2 (Ventaglio):   Ventaglio, onde di laser a ventaglio alternato.
- Boss 3 (Vortice):     Spirale, laser a cerchio rotante con accelerazione.
- Boss 4 (Devastatore): Shotgun, muro di proiettili + onde d'urto.

Ad ogni sconfitta le statistiche scalano.
"""
import math
import random
import pygame

from core.constants import (
    SCREEN_WIDTH, WHITE, RED, GREEN, YELLOW, ORANGE, CYAN, MAGENTA, GOLD,
    NUM_BOSS_VARIANTS, BOSS_NAMES,
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

        # Fase del pattern (per varianti con fasi multiple)
        self._phase = 0
        self._phase_timer = 0
        self._phase_shots = 0

        # Titano: rotazione cannoni
        self._titano_rotation = 0

        # Furia: burst counter
        self._burst_count = 0
        self._burst_delay = 0

        # Ventaglio: direzione alternata
        self._fan_direction = 1
        self._fan_wave = 0

        # Vortice: velocita' spirale
        self._spiral_speed = 0.4
        self._spiral_accel = 0.01

        # Devastatore: onda d'urto timer
        self._shockwave_timer = 0
        self._shockwave_interval = 120

        # Font per la barra vita
        self._hp_font = pygame.font.Font(None, 22)

        # Cache dello sprite scalato
        self._cached_scaled: pygame.Surface | None = None
        self._cached_w = 0
        self._cached_h = 0

    @staticmethod
    def random_variant() -> int:
        """Sceglie una variante casuale con uguale probabilita' per tutti i 5 boss."""
        return random.randint(0, NUM_BOSS_VARIANTS - 1)

    # ------------------------------------------------------------------
    # UPDATE
    # ------------------------------------------------------------------

    def update(self) -> list:
        """Aggiorna il boss: movimento, animazione e sparo."""
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
                self._cached_scaled = None

        # Hit flash countdown
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # Sparo
        self.shoot_timer += 1
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            return self._fire()

        # Pattern speciali con timer secondario
        extra = self._fire_secondary()
        return extra

    # ------------------------------------------------------------------
    # PATTERN DI SPARO PER VARIANTE
    # ------------------------------------------------------------------

    def _fire(self) -> list:
        """Esegue il pattern di sparo primario basato sulla variante."""
        if self.variant == 0:
            return self._fire_titano()
        elif self.variant == 1:
            return self._fire_furia()
        elif self.variant == 2:
            return self._fire_ventaglio()
        elif self.variant == 3:
            return self._fire_vortice()
        elif self.variant == 4:
            return self._fire_devastatore()
        return self._fire_titano()

    def _fire_secondary(self) -> list:
        """Pattern secondario con timing indipendente."""
        lasers = []

        # Furia: burst rapido tra spari principali
        if self.variant == 1 and self._burst_delay > 0:
            self._burst_delay -= 1
            if self._burst_delay == 0 and self._burst_count > 0:
                self._burst_count -= 1
                self._burst_delay = 8  # 8 frame tra burst
                cx, cy = self._cannon_pos(random.choice([0, 3]))
                lasers.append(Laser(cx, cy, 7, CYAN, is_enemy=True))
                if self._burst_count <= 0:
                    self._burst_delay = 0

        # Devastatore: onde d'urto periodiche
        if self.variant == 4:
            self._shockwave_timer += 1
            if self._shockwave_timer >= self._shockwave_interval:
                self._shockwave_timer = 0
                lasers.extend(self._fire_shockwave())

        return lasers

    def _cannon_pos(self, idx: int) -> tuple[float, float]:
        """Calcola la posizione assoluta di un cannone."""
        ox, oy = self.cannon_offsets[idx]
        return (self.x + int(self.width * ox) - 2,
                self.y + int(self.height * oy))

    # -- TITANO (Boss 0): Pattern classico con cannoni rotanti --
    def _fire_titano(self) -> list:
        """Titano: 3 pattern rotanti -- tutti, a coppie alterne, salva concentrata."""
        lasers: list[Laser] = []
        self._titano_rotation = (self._titano_rotation + 1) % 4

        if self._titano_rotation == 0:
            # Tutti e 4 i cannoni sparano dritto
            for i in range(4):
                cx, cy = self._cannon_pos(i)
                lasers.append(Laser(cx, cy, 5, ORANGE, is_enemy=True))
        elif self._titano_rotation == 1:
            # Cannoni esterni: laser convergenti verso il centro
            for i in [0, 3]:
                cx, cy = self._cannon_pos(i)
                center_x = self.x + self.width // 2
                dx = (center_x - cx) * 0.03
                lasers.append(Laser(cx, cy, 5, RED, is_enemy=True, vx=dx))
        elif self._titano_rotation == 2:
            # Cannoni interni: laser divergenti
            for i in [1, 2]:
                cx, cy = self._cannon_pos(i)
                vx = -2.5 if i == 1 else 2.5
                lasers.append(Laser(cx, cy, 6, YELLOW, is_enemy=True, vx=vx))
        else:
            # Salva concentrata: tutti verso un punto random
            target_x = random.randint(100, SCREEN_WIDTH - 100)
            for i in range(4):
                cx, cy = self._cannon_pos(i)
                dx = (target_x - cx) * 0.02
                lasers.append(Laser(cx, cy, 5.5, (255, 130, 50), is_enemy=True, vx=dx))
        return lasers

    # -- FURIA (Boss 1): Burst devastanti --
    def _fire_furia(self) -> list:
        """Furia: burst di 5 laser ravvicinati dai cannoni laterali + attivazione burst secondario."""
        lasers: list[Laser] = []
        # Burst principale: 3 laser da ogni lato
        for i in [0, 3]:
            cx, cy = self._cannon_pos(i)
            for dy in [0, 10, 20]:
                speed = 6 + dy * 0.1
                lasers.append(Laser(cx, cy + dy, speed, CYAN, is_enemy=True))

        # Avvia burst secondario
        self._burst_count = 3
        self._burst_delay = 6
        return lasers

    # -- VENTAGLIO (Boss 2): Onde a ventaglio alternato --
    def _fire_ventaglio(self) -> list:
        """Ventaglio: ventaglio di 7 laser con direzione alternata e ampiezza variabile."""
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        self._fan_wave += 1
        n_rays = 7
        # Ampiezza che oscilla tra 30 e 60 gradi
        spread = 30 + 30 * abs(math.sin(self._fan_wave * 0.3))

        base_angle = self._fan_direction * 10  # offset leggero alternato
        for i in range(n_rays):
            angle_deg = base_angle + (-spread + (2 * spread / (n_rays - 1)) * i)
            rad = math.radians(angle_deg)
            vx = math.sin(rad) * 4.5
            vy = math.cos(rad) * 5
            lasers.append(Laser(
                center_x - 2, center_y, vy, MAGENTA,
                is_enemy=True, vx=vx))

        self._fan_direction *= -1
        return lasers

    # -- VORTICE (Boss 3): Spirale rotante con accelerazione --
    def _fire_vortice(self) -> list:
        """Vortice: 3 bracci di spirale rotante che accelerano gradualmente."""
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        n_arms = 3
        for arm in range(n_arms):
            offset = (2 * math.pi / n_arms) * arm
            angle = self._spiral_angle + offset
            vx = math.sin(angle) * 3.5
            vy = math.cos(angle) * 4.0 + 1.5
            lasers.append(Laser(
                center_x - 2, center_y, vy, GREEN,
                is_enemy=True, vx=vx))

        # Accelerazione graduale della spirale
        self._spiral_speed += self._spiral_accel
        if self._spiral_speed > 1.2:
            self._spiral_speed = 0.4  # reset
        self._spiral_angle += self._spiral_speed

        return lasers

    # -- DEVASTATORE (Boss 4): Muro di proiettili --
    def _fire_devastatore(self) -> list:
        """Devastatore: muro di 8-12 proiettili in cono + proiettili mirati."""
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        # Muro di proiettili
        n_shots = random.randint(8, 12)
        for _ in range(n_shots):
            spread = random.uniform(-55, 55)
            rad = math.radians(spread)
            vx = math.sin(rad) * 3.5
            vy = random.uniform(4, 7)
            lasers.append(Laser(
                center_x + random.randint(-20, 20),
                center_y,
                vy, YELLOW, is_enemy=True, vx=vx))

        return lasers

    def _fire_shockwave(self) -> list:
        """Onda d'urto: cerchio di laser in tutte le direzioni."""
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height // 2

        n = 12
        for i in range(n):
            angle = (2 * math.pi / n) * i
            vx = math.sin(angle) * 3
            vy = math.cos(angle) * 3
            lasers.append(Laser(
                center_x - 2, center_y, vy, RED,
                is_enemy=True, vx=vx))
        return lasers

    # ------------------------------------------------------------------
    # DANNO
    # ------------------------------------------------------------------

    def take_damage(self, amount: int = 1) -> bool:
        """Applica danno al boss e attiva il flash visivo."""
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
            self._cached_scaled = None
        else:
            if (self._cached_scaled is None
                    or self._cached_w != self.width
                    or self._cached_h != self.height):
                self._cached_scaled = pygame.transform.scale(
                    frame, (self.width, self.height))
                self._cached_w = self.width
                self._cached_h = self.height
            surf.blit(self._cached_scaled, (int(self.x), int(self.y)))

    def draw_health_bar(self, surf: pygame.Surface) -> None:
        """Disegna la barra vita del boss in cima allo schermo."""
        if not self.alive:
            return

        bw, bh = 400, 18
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

        # Tacche di separazione
        for s in range(1, 4):
            sx = bx + bw * s // 4
            pygame.draw.line(surf, (12, 12, 18), (sx, by), (sx, by + bh), 1)

        # Etichetta con nome boss
        vname = BOSS_NAMES[self.variant] if self.variant < len(BOSS_NAMES) else "BOSS"
        label = self._hp_font.render(
            f"{vname}  {self.hp}/{self.max_hp}", True, WHITE)
        surf.blit(label, (bx + bw // 2 - label.get_width() // 2, by + 1))

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del boss."""
        return pygame.Rect(
            self.x + 15,
            self.y + 10,
            self.width - 30,
            self.height - 15,
        )
