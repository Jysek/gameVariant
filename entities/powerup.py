"""
Classi PowerUpCarrier e FallingPowerUp - sistema power-up.
"""

import math
import random
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CARRIER_SIZE, POWERUP_ITEM_SIZE, POWERUP_TYPES,
    WHITE, GREEN, CYAN, YELLOW, ORANGE, RED,
    POWERUP_COLORS,
)
from core.assets import Assets


class PowerUpCarrier:
    """Navicella carrier che trasporta un power-up.

    Scende dall'alto, si ferma a meta' della meta' superiore dello schermo,
    si muove orizzontalmente. Il giocatore ha 5 secondi per distruggerla.
    Se non viene distrutta, scappa verso il basso con scatto iperspaziale.
    """

    STATE_DESCENDING = 0
    STATE_HOVERING = 1
    STATE_ESCAPING = 2

    def __init__(self, powerup_type=None):
        self.width = CARRIER_SIZE
        self.height = CARRIER_SIZE
        self.x = random.randint(20, SCREEN_WIDTH - self.width - 20)
        self.y = -self.height
        self.alive = True

        self.target_y = SCREEN_HEIGHT // 4
        self.state = PowerUpCarrier.STATE_DESCENDING
        self.descent_speed = 2.5

        # Tipo di power-up
        self.powerup_type = powerup_type or random.choice(POWERUP_TYPES)
        self.image = Assets.carrier_sprites[self.powerup_type]

        # HP
        self.max_hp = random.randint(3, 5)
        self.hp = self.max_hp

        # Movimento orizzontale
        self.h_speed = random.choice([-2.0, -1.5, -1.0, 1.0, 1.5, 2.0])
        self.h_direction_timer = 0
        self.h_change_interval = random.randint(60, 180)

        # Timer di permanenza (5 secondi)
        self.hover_timer = 5 * 60

        # Fuga iperspaziale
        self.escape_speed = 0
        self.escape_acceleration = 1.5
        self.hit_flash = 0
        self.trail_particles = []

    def update(self):
        """Aggiorna il carrier in base allo stato corrente."""
        if not self.alive:
            return

        if self.hit_flash > 0:
            self.hit_flash -= 1

        if self.state == PowerUpCarrier.STATE_DESCENDING:
            self._update_descending()
        elif self.state == PowerUpCarrier.STATE_HOVERING:
            self._update_hovering()
        elif self.state == PowerUpCarrier.STATE_ESCAPING:
            self._update_escaping()

    def _update_descending(self):
        """Scende dall'alto verso la posizione target."""
        self.y += self.descent_speed
        if self.y >= self.target_y:
            self.y = self.target_y
            self.state = PowerUpCarrier.STATE_HOVERING

    def _update_hovering(self):
        """Si muove orizzontalmente e conta il timer di 5 secondi."""
        self.x += self.h_speed
        self.h_direction_timer += 1
        if self.h_direction_timer >= self.h_change_interval:
            self.h_speed = random.choice([-2.0, -1.5, -1.0, 1.0, 1.5, 2.0])
            self.h_direction_timer = 0
            self.h_change_interval = random.randint(60, 180)

        # Rimbalzo ai bordi
        if self.x < 10:
            self.x = 10
            self.h_speed = abs(self.h_speed)
        elif self.x > SCREEN_WIDTH - self.width - 10:
            self.x = SCREEN_WIDTH - self.width - 10
            self.h_speed = -abs(self.h_speed)

        self.hover_timer -= 1
        if self.hover_timer <= 0:
            self.state = PowerUpCarrier.STATE_ESCAPING
            self.escape_speed = 3

    def _update_escaping(self):
        """Scatto iperspaziale verso il basso."""
        self.escape_speed += self.escape_acceleration
        self.y += self.escape_speed

        # Scia
        if random.random() < 0.6:
            self.trail_particles.append({
                "x": self.x + self.width // 2 + random.randint(-10, 10),
                "y": self.y,
                "alpha": 200,
                "size": random.randint(2, 5),
            })

        for p in self.trail_particles:
            p["alpha"] -= 12
            p["size"] = max(0, p["size"] - 0.1)
        self.trail_particles = [p for p in self.trail_particles if p["alpha"] > 0]

        if self.y > SCREEN_HEIGHT + 50:
            self.alive = False

    def take_damage(self, amount=1):
        """Il carrier subisce danno. Restituisce True se distrutto."""
        self.hp -= amount
        self.hit_flash = 6
        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    def draw(self, surface):
        """Disegna il carrier con tutti gli effetti visivi."""
        if not self.alive:
            return

        # Scia iperspaziale
        if self.state == PowerUpCarrier.STATE_ESCAPING:
            self._draw_trail(surface)

        # Sprite
        draw_img = self.image.copy()
        if self.hit_flash > 0 and self.hit_flash % 2 == 0:
            flash_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            flash_surface.fill((255, 255, 255, 150))
            draw_img.blit(flash_surface, (0, 0))

        # Deformazione iperspaziale
        if self.state == PowerUpCarrier.STATE_ESCAPING:
            stretch_h = min(self.height + int(self.escape_speed * 2), self.height * 3)
            draw_img = pygame.transform.scale(draw_img, (self.width, stretch_h))

        surface.blit(draw_img, (int(self.x), int(self.y)))

        # HUD del carrier (nome, barra HP, timer)
        if self.state != PowerUpCarrier.STATE_ESCAPING:
            self._draw_carrier_hud(surface)

    def _draw_trail(self, surface):
        """Disegna la scia delle particelle durante la fuga."""
        for p in self.trail_particles:
            size = int(p["size"])
            if size <= 0:
                continue
            trail_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                trail_surf, (100, 180, 255, int(p["alpha"])),
                (size, size), size,
            )
            surface.blit(trail_surf, (int(p["x"] - size), int(p["y"] - size)))

    def _draw_carrier_hud(self, surface):
        """Disegna etichetta, barra HP e timer del carrier."""
        color = POWERUP_COLORS.get(self.powerup_type, WHITE)

        # Nome del power-up
        font = pygame.font.Font(None, 18)
        label = font.render(self.powerup_type.upper(), True, color)
        label_x = self.x + self.width // 2 - label.get_width() // 2
        surface.blit(label, (int(label_x), int(self.y - 14)))

        # Barra HP
        bar_w = self.width
        bar_y = self.y + self.height + 2
        hp_pct = self.hp / self.max_hp
        pygame.draw.rect(surface, (60, 60, 60), (int(self.x), int(bar_y), bar_w, 4))
        pygame.draw.rect(surface, color, (int(self.x), int(bar_y), int(bar_w * hp_pct), 4))

        # Timer countdown
        if self.state == PowerUpCarrier.STATE_HOVERING:
            timer_bar_y = self.y + self.height + 8
            timer_pct = self.hover_timer / (5 * 60)
            if timer_pct > 0.5:
                timer_color = GREEN
            elif timer_pct > 0.25:
                timer_color = YELLOW
            else:
                timer_color = RED
            pygame.draw.rect(surface, (40, 40, 40), (int(self.x), int(timer_bar_y), bar_w, 3))
            pygame.draw.rect(surface, timer_color, (int(self.x), int(timer_bar_y), int(bar_w * timer_pct), 3))

    def get_rect(self):
        return pygame.Rect(self.x + 3, self.y + 3, self.width - 6, self.height - 6)


class FallingPowerUp:
    """Power-up che cade dopo la distruzione di un carrier.

    Se il giocatore lo raccoglie (collisione), applica l'effetto.
    """

    def __init__(self, x, y, powerup_type):
        self.width = POWERUP_ITEM_SIZE
        self.height = POWERUP_ITEM_SIZE
        self.x = x
        self.y = y
        self.powerup_type = powerup_type
        self.image = Assets.powerup_sprites[self.powerup_type]
        self.active = True
        self.fall_speed = 2.5
        self.pulse_timer = 0

    def update(self):
        """Aggiorna il power-up - cade in linea retta."""
        if not self.active:
            return
        self.y += self.fall_speed
        self.pulse_timer += 0.1
        if self.y > SCREEN_HEIGHT + 20:
            self.active = False

    def draw(self, surface):
        """Disegna il power-up con effetto glow pulsante."""
        if not self.active:
            return

        glow_alpha = int(abs(math.sin(self.pulse_timer)) * 80) + 40
        glow_color = POWERUP_COLORS.get(self.powerup_type, WHITE)
        glow_size = self.width + 10
        glow_surf = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
        pygame.draw.circle(
            glow_surf, (*glow_color, glow_alpha),
            (glow_size // 2, glow_size // 2), glow_size // 2,
        )
        surface.blit(glow_surf, (int(self.x - 5), int(self.y - 5)))
        surface.blit(self.image, (int(self.x), int(self.y)))

    def get_rect(self):
        return pygame.Rect(self.x, self.y, self.width, self.height)
