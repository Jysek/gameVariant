"""
Boss -- animazione GIF / PNG, 4 cannoni, scaling progressivo, varianti multiple.

Il boss appare preceduto da un warning di 3 secondi, scende dall'alto,
si muove orizzontalmente e spara con 3 pattern casuali.
Ad ogni sconfitta le sue statistiche scalano (piu' HP, piu' veloce,
intervallo sparo ridotto).

Supporta 4 varianti visive: boss.gif (animato) e boss_1/2/3.png (statici).
La variante viene scelta progressivamente o a caso.
"""
import random
import pygame

from core.constants import (
    SCREEN_WIDTH, WHITE, RED, GREEN, YELLOW, ORANGE,
    NUM_BOSS_VARIANTS,
)
from core.assets import Assets
from entities.laser import Laser


class Boss:
    """Boss con animazione, 4 cannoni e barra vita.

    Fasi:
    1. Entering: scende dall'alto fino a target_y.
    2. Attivo: si muove orizzontalmente e spara.

    Args:
        variant: Indice della variante visiva (0-3). Default 0 (boss.gif).
    """

    def __init__(self, variant=0):
        """Inizializza il boss sopra lo schermo."""
        self.variant = variant % max(1, len(Assets.boss_variants))
        self.width  = 200
        self.height = 120
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

        # Frame (animazione o statico)
        self.frames = Assets.boss_variants[self.variant] if self.variant < len(Assets.boss_variants) else Assets.boss_frames
        if not self.frames:
            self.frames = Assets.boss_frames  # fallback

        self.frame_idx   = 0
        self.frame_timer = 0
        self.frame_delay = 6  # frame di gioco per frame GIF

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

    def update(self) -> list:
        """Aggiorna il boss: movimento, animazione e sparo.

        Returns:
            Lista di Laser sparati in questo frame (vuota se nessuno).
        """
        if not self.alive:
            return []

        # ---- Fase di ingresso ----
        if self.entering:
            self.y += 1.5
            if self.y >= self.target_y:
                self.y = float(self.target_y)
                self.entering = False
            return []

        # ---- Movimento orizzontale ----
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

        # ---- Animazione frame ----
        if len(self.frames) > 1:
            self.frame_timer += 1
            if self.frame_timer >= self.frame_delay:
                self.frame_timer = 0
                self.frame_idx = (self.frame_idx + 1) % len(self.frames)

        # ---- Hit flash countdown ----
        if self.hit_flash > 0:
            self.hit_flash -= 1

        # ---- Sparo ----
        self.shoot_timer += 1
        if self.shoot_timer >= self.shoot_interval:
            self.shoot_timer = 0
            return self._fire()
        return []

    def _fire(self) -> list:
        """Esegue uno dei 3 pattern di sparo casuali.

        Pattern 0: tutti e 4 i cannoni, velocita' media (arancione).
        Pattern 1: cannoni esterni (0 e 3), velocita' alta (rosso).
        Pattern 2: cannoni interni (1 e 2), velocita' molto alta (giallo).

        Returns:
            Lista di Laser sparati.
        """
        pattern = random.randint(0, 2)
        lasers = []

        if pattern == 0:
            # Tutti e 4 i cannoni
            for ox, oy in self.cannon_offsets:
                lasers.append(Laser(
                    self.x + int(self.width * ox) - 2,
                    self.y + int(self.height * oy),
                    5, ORANGE, is_enemy=True))

        elif pattern == 1:
            # Cannoni esterni
            for i in [0, 3]:
                ox, oy = self.cannon_offsets[i]
                lasers.append(Laser(
                    self.x + int(self.width * ox) - 2,
                    self.y + int(self.height * oy),
                    6, RED, is_enemy=True))

        else:
            # Cannoni interni
            for i in [1, 2]:
                ox, oy = self.cannon_offsets[i]
                lasers.append(Laser(
                    self.x + int(self.width * ox) - 2,
                    self.y + int(self.height * oy),
                    7, YELLOW, is_enemy=True))

        return lasers

    def take_damage(self, amount=1) -> bool:
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

    def draw(self, surf):
        """Disegna il boss con effetto pulsazione all'hit.

        All'hit lo sprite viene leggermente ingrandito per un effetto
        pulsazione sottile, senza overlay colorati.

        Args:
            surf: Surface di destinazione.
        """
        if not self.alive:
            return

        frame = self.frames[self.frame_idx % len(self.frames)]

        if self.hit_flash > 0:
            # Pulsazione: ingrandimento proporzionale al flash rimanente
            ratio = self.hit_flash / self.hit_flash_max
            pulse = int(4 * ratio)
            w2 = self.width + pulse * 2
            h2 = self.height + pulse * 2
            scaled = pygame.transform.scale(frame, (w2, h2))
            surf.blit(scaled, (int(self.x) - pulse, int(self.y) - pulse))
        else:
            scaled = pygame.transform.scale(frame, (self.width, self.height))
            surf.blit(scaled, (int(self.x), int(self.y)))

    def draw_health_bar(self, surf):
        """Disegna la barra vita del boss in cima allo schermo.

        La barra cambia colore: verde > 50%, giallo > 25%, rosso altrimenti.
        4 tacche di separazione dividono la barra in quarti.

        Args:
            surf: Surface di destinazione.
        """
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

        # Etichetta con nome variante
        variant_names = ["BOSS", "MOTH BOSS", "CYBER BOSS", "BUG BOSS"]
        vn = variant_names[self.variant % len(variant_names)]
        font = pygame.font.Font(None, 20)
        label = font.render(f"{vn}  {self.hp}/{self.max_hp}", True, WHITE)
        surf.blit(label, (bx + bw // 2 - label.get_width() // 2, by + 1))

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del boss.

        La hitbox e' ridotta rispetto allo sprite per ignorare le
        estremita' trasparenti dell'animazione.
        """
        return pygame.Rect(
            self.x + 15,
            self.y + 10,
            self.width - 30,
            self.height - 15,
        )
