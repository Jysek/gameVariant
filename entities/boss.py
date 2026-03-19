"""
Boss -- 4 varianti con animazione GIF, pattern laser unici, scaling progressivo.

Varianti (spawn casuale con probabilità uguale):
- Boss 0 (Titano):    Raffiche cannon alternate (dritte, convergenti, divergenti).
- Boss 1 (Furia):     Colpi doppio cannone con burst secondario ritardato.
- Boss 2 (Ventaglio): Ventaglio simmetrico a 5 laser con offset alternato.
- Boss 3 (Vortice):   3 bracci rotanti a velocità costante (spirale prevedibile).

Tutti i pattern laser sono progettati per essere semplici, funzionali e equi:
- Tutti i proiettili viaggiano principalmente VERSO IL BASSO (vy positivo).
- I pattern sono abbastanza prevedibili da imparare e schivare.
- Nessuna mira casuale al giocatore -- pattern puramente geometrici.
"""

import math
import random
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, WHITE, RED, GREEN, YELLOW, ORANGE,
    CYAN, MAGENTA, GOLD, NUM_BOSS_VARIANTS, BOSS_NAMES,
)
from core.assets import Assets
from entities.laser import Laser


class Boss:
    """Entità boss con animazione GIF, pattern laser unici e barra salute.

    Ogni variante boss ha un pattern d'attacco distinto, rendendo ogni
    incontro diverso. Tutti i proiettili viaggiano principalmente verso
    il basso così lo sprite laser (che punta in giù) viene renderizzato
    correttamente.

    Args:
        variant: Indice variante boss (0-3).
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

        # Statistiche (possono essere sovrascrite da game.py per lo scaling)
        self.max_hp = 60
        self.hp     = self.max_hp

        # Movimento orizzontale
        self.h_speed        = random.choice(
            [-2.5, -2.0, -1.5, 1.5, 2.0, 2.5])
        self.h_dir_timer    = 0
        self.h_dir_interval = random.randint(120, 300)

        # Animazione GIF
        self.frames      = Assets.boss_variant_frames[self.variant]
        self.frame_idx   = 0
        self.frame_timer = 0
        self.frame_delay = 6

        # Posizioni cannoni (percentuali relative a larghezza/altezza)
        self.cannon_offsets = [
            (0.12, 0.85),
            (0.38, 0.95),
            (0.62, 0.95),
            (0.88, 0.85),
        ]

        # Timer sparo primario
        self.shoot_timer    = 0
        self.shoot_interval = 40

        # Effetto visivo flash al colpo
        self.hit_flash     = 0
        self.hit_flash_max = 8

        # Titano: indice sub-pattern rotazione cannoni
        self._titano_rotation = 0

        # Furia: stato burst
        self._burst_count = 0
        self._burst_delay = 0

        # Ventaglio: direzione alternata e contatore onde
        self._fan_direction = 1

        # Vortice: angolo spirale
        self._spiral_angle = 0.0

        # Font barra salute
        self._hp_font = pygame.font.Font(None, 22)

        # Sprite scalato cached per prestazioni
        self._cached_scaled: pygame.Surface | None = None
        self._cached_w = 0
        self._cached_h = 0

    @staticmethod
    def random_variant() -> int:
        """Sceglie una variante boss casuale con probabilità uguale (0-3)."""
        return random.randint(0, NUM_BOSS_VARIANTS - 1)

    # ------------------------------------------------------------------
    # AGGIORNAMENTO
    # ------------------------------------------------------------------

    def update(self) -> list[Laser]:
        """Aggiorna il boss: movimento, animazione e pattern di sparo.

        Returns:
            Lista di oggetti ``Laser`` appena sparati (può essere vuota).
        """
        if not self.alive:
            return []

        # Fase di entrata: scivola giù dall'alto
        if self.entering:
            self.y += 1.5
            if self.y >= self.target_y:
                self.y = float(self.target_y)
                self.entering = False
            return []

        # Movimento orizzontale con cambi direzione
        self.x += self.h_speed
        self.h_dir_timer += 1
        if self.h_dir_timer >= self.h_dir_interval:
            self.h_speed = random.choice(
                [-2.5, -2.0, -1.5, 1.5, 2.0, 2.5])
            self.h_dir_timer = 0
            self.h_dir_interval = random.randint(120, 300)

        # Rimbalzo ai bordi dello schermo
        if self.x <= 10:
            self.x = 10.0
            self.h_speed = abs(self.h_speed)
        elif self.x >= SCREEN_WIDTH - self.width - 10:
            self.x = float(SCREEN_WIDTH - self.width - 10)
            self.h_speed = -abs(self.h_speed)

        # Avanza animazione GIF
        self.frame_timer += 1
        if self.frame_timer >= self.frame_delay:
            self.frame_timer = 0
            if self.frames:
                self.frame_idx = (self.frame_idx + 1) % len(self.frames)
                self._cached_scaled = None

        # Diminuisci flash al colpo
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # Sparo primario a intervallo
        self.shoot_timer += 1
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            return self._fire()

        # Effetti pattern secondario/continuo
        return self._fire_secondary()

    # ------------------------------------------------------------------
    # DISPATCH PATTERN DI SPARO
    # ------------------------------------------------------------------

    def _fire(self) -> list[Laser]:
        """Esegue il pattern di sparo primario basato sulla variante boss."""
        if self.variant == 0:
            return self._fire_titano()
        elif self.variant == 1:
            return self._fire_furia()
        elif self.variant == 2:
            return self._fire_ventaglio()
        elif self.variant == 3:
            return self._fire_vortice()
        return self._fire_titano()

    def _fire_secondary(self) -> list[Laser]:
        """Gestisce pattern di sparo secondari tra i colpi principali.

        Solo Furia usa un burst secondario tra le raffiche primarie.

        Returns:
            Lista di laser aggiuntivi (può essere vuota).
        """
        lasers: list[Laser] = []

        # Furia: colpi burst di follow-up tra le raffiche primarie
        if self.variant == 1 and self._burst_delay > 0:
            self._burst_delay -= 1
            if self._burst_delay == 0 and self._burst_count > 0:
                self._burst_count -= 1
                self._burst_delay = 10
                cx = self.x + self.width // 2
                cy = self.y + self.height
                lasers.append(
                    Laser(cx - 2, cy, 6, CYAN, is_enemy=True))
                if self._burst_count <= 0:
                    self._burst_delay = 0

        return lasers

    def _cannon_pos(self, idx: int) -> tuple[float, float]:
        """Calcola la posizione assoluta di un cannone.

        Args:
            idx: Indice cannone (0-3).

        Returns:
            Tupla (x, y) della posizione del cannone sullo schermo.
        """
        ox, oy = self.cannon_offsets[idx]
        return (
            self.x + int(self.width * ox) - 2,
            self.y + int(self.height * oy),
        )

    # ------------------------------------------------------------------
    # TITANO (Boss 0): Raffiche cannon alternate
    # ------------------------------------------------------------------

    def _fire_titano(self) -> list[Laser]:
        """Titano cicla attraverso 3 semplici pattern di cannoni.

        Pattern 0: Tutti e 4 i cannoni sparano dritto in giù.
        Pattern 1: I cannoni esterni sparano con leggero angolo interno.
        Pattern 2: I cannoni interni sparano con leggero angolo esterno.

        Tutti i colpi si muovono principalmente verso il basso con
        traiettorie prevedibili.
        """
        lasers: list[Laser] = []
        self._titano_rotation = (self._titano_rotation + 1) % 3

        if self._titano_rotation == 0:
            # Tutti e 4 i cannoni sparano dritto in giù
            for i in range(4):
                cx, cy = self._cannon_pos(i)
                lasers.append(
                    Laser(cx, cy, 5, ORANGE, is_enemy=True))

        elif self._titano_rotation == 1:
            # I cannoni esterni convergono leggermente verso l'interno
            for i in [0, 3]:
                cx, cy = self._cannon_pos(i)
                vx = 1.2 if i == 0 else -1.2
                lasers.append(
                    Laser(cx, cy, 5, RED, is_enemy=True, vx=vx))

        else:
            # I cannoni interni divergono leggermente verso l'esterno
            for i in [1, 2]:
                cx, cy = self._cannon_pos(i)
                vx = -1.0 if i == 1 else 1.0
                lasers.append(
                    Laser(cx, cy, 5, YELLOW, is_enemy=True, vx=vx))

        return lasers

    # ------------------------------------------------------------------
    # FURIA (Boss 1): Burst doppio cannone
    # ------------------------------------------------------------------

    def _fire_furia(self) -> list[Laser]:
        """Furia spara da entrambi i cannoni laterali poi attiva un burst.

        Primario: 1 laser da ciascun cannone esterno dritto in giù.
        Secondario: 2 colpi di follow-up dal centro dopo un breve ritardo.

        Semplice e prevedibile ma il burst mantiene pressione sul giocatore.
        """
        lasers: list[Laser] = []
        # Spara dai cannoni esterni
        for i in [0, 3]:
            cx, cy = self._cannon_pos(i)
            lasers.append(
                Laser(cx, cy, 5.5, CYAN, is_enemy=True))

        # Attiva un piccolo burst di follow-up (2 colpi dal centro)
        self._burst_count = 2
        self._burst_delay = 10
        return lasers

    # ------------------------------------------------------------------
    # VENTAGLIO (Boss 2): Ventaglio ad angolo fisso
    # ------------------------------------------------------------------

    def _fire_ventaglio(self) -> list[Laser]:
        """Ventaglio spara un ventaglio simmetrico di 5 laser dal centro.

        I laser si distribuiscono uniformemente su un arco fisso di 60 gradi.
        Il ventaglio alterna inclinazione a sinistra o destra con un piccolo
        offset. Tutti i colpi hanno forte velocità verso il basso (vy >= 4).
        """
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        n_rays = 5
        spread = 30  # gradi dal centro (arco totale = 60 gradi)
        # Piccolo offset alternato per variare leggermente il pattern
        offset = self._fan_direction * 5

        for i in range(n_rays):
            angle_deg = offset + (-spread + (2 * spread / (n_rays - 1)) * i)
            rad = math.radians(angle_deg)
            vx = math.sin(rad) * 4.0
            vy = max(4.0, math.cos(rad) * 5.0)
            lasers.append(
                Laser(center_x - 2, center_y, vy, MAGENTA,
                      is_enemy=True, vx=vx))

        self._fan_direction *= -1
        return lasers

    # ------------------------------------------------------------------
    # VORTICE (Boss 3): Bracci rotanti costanti
    # ------------------------------------------------------------------

    def _fire_vortice(self) -> list[Laser]:
        """Vortice spara 3 bracci rotanti a velocità costante.

        Ogni braccio è sfalsato di 120 gradi. La rotazione avanza di
        una quantità costante ad ogni colpo, producendo una spirale
        prevedibile che il giocatore può imparare a schivare. Tutti i
        colpi viaggiano verso il basso.
        """
        lasers: list[Laser] = []
        center_x = self.x + self.width // 2
        center_y = self.y + self.height

        n_arms = 3
        for arm in range(n_arms):
            offset = (2 * math.pi / n_arms) * arm
            angle = self._spiral_angle + offset
            vx = math.sin(angle) * 2.5
            vy = max(3.5, abs(math.cos(angle)) * 4.0 + 2.0)
            lasers.append(
                Laser(center_x - 2, center_y, vy, GREEN,
                      is_enemy=True, vx=vx))

        # Velocità rotazione costante -- prevedibile e imparabile
        self._spiral_angle += 0.5

        return lasers

    # ------------------------------------------------------------------
    # DANNO
    # ------------------------------------------------------------------

    def take_damage(self, amount: int = 1) -> bool:
        """Applica danno al boss e attiva il flash al colpo.

        Args:
            amount: Quantità di danno.

        Returns:
            True se il boss è stato sconfitto (hp <= 0).
        """
        self.hp -= amount
        self.hit_flash = self.hit_flash_max
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    # ------------------------------------------------------------------
    # DISEGNO
    # ------------------------------------------------------------------

    def draw(self, surf: pygame.Surface) -> None:
        """Disegna il boss con effetto pulsazione al colpo.

        Args:
            surf: Surface di destinazione.
        """
        if not self.alive or not self.frames:
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
        """Disegna la barra salute del boss in cima allo schermo.

        Il colore cambia da verde -> giallo -> rosso man mano che gli HP
        diminuiscono.

        Args:
            surf: Surface di destinazione.
        """
        if not self.alive:
            return

        bw, bh = 400, 18
        bx = SCREEN_WIDTH // 2 - bw // 2
        by = 8

        # Sfondo
        pygame.draw.rect(
            surf, (12, 12, 18), (bx - 1, by - 1, bw + 2, bh + 2))
        pygame.draw.rect(
            surf, (40, 40, 55), (bx, by, bw, bh))

        # Riempimento salute
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

        # Segni separatori a intervalli del 25%
        for s in range(1, 4):
            sx = bx + bw * s // 4
            pygame.draw.line(
                surf, (12, 12, 18), (sx, by), (sx, by + bh), 1)

        # Etichetta nome boss
        vname = (BOSS_NAMES[self.variant]
                 if self.variant < len(BOSS_NAMES) else "BOSS")
        label = self._hp_font.render(
            f"{vname}  {self.hp}/{self.max_hp}", True, WHITE)
        surf.blit(label, (bx + bw // 2 - label.get_width() // 2, by + 1))

    # ------------------------------------------------------------------
    # HITBOX
    # ------------------------------------------------------------------

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox di collisione del boss (leggermente ridotta)."""
        return pygame.Rect(
            self.x + 15,
            self.y + 10,
            self.width - 30,
            self.height - 15,
        )
