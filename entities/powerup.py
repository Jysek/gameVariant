"""
Classi PowerUpCarrier e FallingPowerUp -- sistema power-up.

Il carrier scende dall'alto, si ferma per 5 secondi nella meta' superiore
dello schermo muovendosi orizzontalmente. Il giocatore ha tempo per
distruggerlo (3-5 HP). Se distrutto, rilascia un power-up cadente.
Se non distrutto, fugge con uno scatto iperspaziale verso il basso.

Hit feedback (come nemici multi-HP):
- Shake (oscillazione rapida)
- Mini-esplosione al punto d'impatto
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

# Parametri shake
_CARRIER_SHAKE_DURATION  = 12
_CARRIER_SHAKE_AMPLITUDE = 3


class PowerUpCarrier:
    """Navicella carrier che trasporta un power-up.

    Args:
        powerup_type: Tipo di power-up trasportato (opzionale, casuale se None).
    """

    STATE_DESCENDING = 0
    STATE_HOVERING   = 1
    STATE_ESCAPING   = 2

    def __init__(self, powerup_type=None):
        self.width  = CARRIER_SIZE
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
        self.h_direction_timer  = 0
        self.h_change_interval  = random.randint(60, 180)

        # Timer di permanenza (5 secondi a 60 FPS)
        self.hover_timer = 5 * 60

        # Fuga iperspaziale
        self.escape_speed        = 0
        self.escape_acceleration = 1.5
        self.hit_flash = 0
        self.trail_particles: list[dict] = []

        # Shake effect
        self._shake_timer = 0
        self._shake_offset_x = 0
        self._shake_offset_y = 0

        # Font per l'HUD del carrier (creato una sola volta)
        self._hud_font = pygame.font.Font(None, 18)

    def update(self):
        """Aggiorna il carrier in base allo stato corrente."""
        if not self.alive:
            return

        # Aggiorna shake
        if self._shake_timer > 0:
            ratio = self._shake_timer / _CARRIER_SHAKE_DURATION
            amp = int(_CARRIER_SHAKE_AMPLITUDE * ratio)
            self._shake_offset_x = random.randint(-amp, amp)
            self._shake_offset_y = random.randint(-amp // 2, amp // 2)
            self._shake_timer -= 1
        else:
            self._shake_offset_x = 0
            self._shake_offset_y = 0

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
        """Si muove orizzontalmente e conta il timer."""
        self.x += self.h_speed
        self.h_direction_timer += 1
        if self.h_direction_timer >= self.h_change_interval:
            self.h_speed = random.choice([-2.0, -1.5, -1.0, 1.0, 1.5, 2.0])
            self.h_direction_timer = 0
            self.h_change_interval = random.randint(60, 180)

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
        self.trail_particles = [
            p for p in self.trail_particles if p["alpha"] > 0
        ]

        if self.y > SCREEN_HEIGHT + 50:
            self.alive = False

    def take_damage(self, amount: int = 1) -> bool:
        """Il carrier subisce danno con shake.

        La mini-esplosione viene gestita dal chiamante (game.py) perche'
        serve l'accesso alla lista delle esplosioni.

        Args:
            amount: Quantita' di danno.

        Returns:
            True se il carrier e' stato distrutto.
        """
        self.hp -= amount
        self._shake_timer = _CARRIER_SHAKE_DURATION

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

        draw_img = self.image.copy()

        # Deformazione durante fuga
        if self.state == PowerUpCarrier.STATE_ESCAPING:
            stretch_h = min(
                self.height + int(self.escape_speed * 2),
                self.height * 3)
            draw_img = pygame.transform.scale(draw_img, (self.width, stretch_h))

        draw_x = int(self.x + self._shake_offset_x)
        draw_y = int(self.y + self._shake_offset_y)
        surface.blit(draw_img, (draw_x, draw_y))

        # HUD del carrier
        if self.state != PowerUpCarrier.STATE_ESCAPING:
            self._draw_carrier_hud(surface)

    def _draw_trail(self, surface):
        """Disegna la scia di particelle durante la fuga."""
        for p in self.trail_particles:
            size = int(p["size"])
            if size <= 0:
                continue
            trail_surf = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
            pygame.draw.circle(
                trail_surf, (100, 180, 255, int(p["alpha"])),
                (size, size), size)
            surface.blit(trail_surf, (int(p["x"] - size), int(p["y"] - size)))

    def _draw_carrier_hud(self, surface):
        """Disegna etichetta tipo, barra HP e barra timer."""
        color = POWERUP_COLORS.get(self.powerup_type, WHITE)

        label = self._hud_font.render(self.powerup_type.upper(), True, color)
        label_x = self.x + self.width // 2 - label.get_width() // 2
        surface.blit(label, (int(label_x), int(self.y - 14)))

        # Barra HP
        bar_w = self.width
        bar_y = self.y + self.height + 2
        hp_pct = self.hp / self.max_hp
        pygame.draw.rect(
            surface, (60, 60, 60), (int(self.x), int(bar_y), bar_w, 4))
        pygame.draw.rect(
            surface, color, (int(self.x), int(bar_y), int(bar_w * hp_pct), 4))

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
            pygame.draw.rect(
                surface, (40, 40, 40),
                (int(self.x), int(timer_bar_y), bar_w, 3))
            pygame.draw.rect(
                surface, timer_color,
                (int(self.x), int(timer_bar_y), int(bar_w * timer_pct), 3))

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del carrier."""
        shrink = 5
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width - shrink * 2,
            self.height - shrink * 2,
        )


class FallingPowerUp:
    """Power-up che cade dopo la distruzione di un carrier.

    Args:
        x, y: Posizione iniziale.
        powerup_type: Tipo di power-up.
    """

    def __init__(self, x, y, powerup_type):
        self.width  = POWERUP_ITEM_SIZE
        self.height = POWERUP_ITEM_SIZE
        self.x = x
        self.y = y
        self.powerup_type = powerup_type
        self.image = Assets.powerup_sprites[self.powerup_type]
        self.active = True
        self.fall_speed = 2.5
        self.pulse_timer = 0

    def update(self):
        """Aggiorna il power-up: cade in linea retta."""
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
        glow_size  = self.width + 10
        glow_surf  = pygame.Surface((glow_size, glow_size), pygame.SRCALPHA)
        pygame.draw.circle(
            glow_surf, (*glow_color, glow_alpha),
            (glow_size // 2, glow_size // 2), glow_size // 2)
        surface.blit(glow_surf, (int(self.x - 5), int(self.y - 5)))
        surface.blit(self.image, (int(self.x), int(self.y)))

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del power-up."""
        return pygame.Rect(self.x, self.y, self.width, self.height)
