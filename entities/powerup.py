"""
Classi PowerUpCarrier e FallingPowerUp -- sistema di consegna power-up.

Il carrier scende dall'alto, staziona per 5 secondi nella metà superiore
muovendosi orizzontalmente. Il giocatore deve distruggerlo (3-5 HP) per
rilasciare un power-up cadente. Se non viene distrutto, fugge con un
dash iperspaziale verso il basso.

Usa sprite propri: assets/powerups/carrier_bomba.png e
assets/powerups/powerup_bomba.png per i power-up bomba.
"""

import random
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CARRIER_SIZE, POWERUP_ITEM_SIZE, POWERUP_TYPES,
    WHITE, GREEN, YELLOW, RED,
    POWERUP_COLORS,
)
from core.assets import Assets

# Parametri shake
_CARRIER_SHAKE_DURATION  = 12
_CARRIER_SHAKE_AMPLITUDE = 3


class PowerUpCarrier:
    """Nave carrier che trasporta un power-up.

    Stati:
    - DESCENDING: Scende verso la posizione di stazionamento.
    - HOVERING:   Si muove orizzontalmente, in attesa di essere distrutto.
    - ESCAPING:   Dash iperspaziale verso il basso (non distrutto in tempo).

    Args:
        powerup_type: Tipo di power-up trasportato (casuale se None).
    """

    STATE_DESCENDING = 0
    STATE_HOVERING   = 1
    STATE_ESCAPING   = 2

    def __init__(self, powerup_type: str | None = None):
        self.width  = CARRIER_SIZE
        self.height = CARRIER_SIZE
        self.x = random.randint(20, SCREEN_WIDTH - self.width - 20)
        self.y = -self.height
        self.alive = True

        self.target_y = SCREEN_HEIGHT // 4
        self.state = PowerUpCarrier.STATE_DESCENDING
        self.descent_speed = 2.5

        # Tipo power-up (usa sprite propri da Assets)
        self.powerup_type = powerup_type or random.choice(POWERUP_TYPES)
        self.image = Assets.carrier_sprites[self.powerup_type]

        # Punti vita
        self.max_hp = random.randint(3, 5)
        self.hp = self.max_hp

        # Movimento orizzontale
        self.h_speed            = random.choice(
            [-2.0, -1.5, -1.0, 1.0, 1.5, 2.0])
        self.h_direction_timer  = 0
        self.h_change_interval  = random.randint(60, 180)

        # Durata stazionamento (5 secondi a 60 FPS)
        self.hover_timer = 5 * 60

        # Fuga iperspaziale
        self.escape_speed        = 0
        self.escape_acceleration = 1.5
        self.hit_flash = 0
        self.trail_particles: list[dict] = []

        # Effetto shake
        self._shake_timer    = 0
        self._shake_offset_x = 0
        self._shake_offset_y = 0

        # Font HUD (creato una sola volta)
        self._hud_font = pygame.font.Font(None, 18)

    # ------------------------------------------------------------------
    # AGGIORNAMENTO
    # ------------------------------------------------------------------

    def update(self) -> None:
        """Aggiorna il carrier in base al suo stato corrente."""
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

    def _update_descending(self) -> None:
        """Scende verso la posizione di stazionamento."""
        self.y += self.descent_speed
        if self.y >= self.target_y:
            self.y = self.target_y
            self.state = PowerUpCarrier.STATE_HOVERING

    def _update_hovering(self) -> None:
        """Si muove orizzontalmente e decrementa il timer di stazionamento."""
        self.x += self.h_speed
        self.h_direction_timer += 1
        if self.h_direction_timer >= self.h_change_interval:
            self.h_speed = random.choice(
                [-2.0, -1.5, -1.0, 1.0, 1.5, 2.0])
            self.h_direction_timer = 0
            self.h_change_interval = random.randint(60, 180)

        # Rimbalzo ai bordi dello schermo
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

    def _update_escaping(self) -> None:
        """Accelera verso il basso in modalità fuga iperspaziale."""
        self.escape_speed += self.escape_acceleration
        self.y += self.escape_speed

        # Genera particelle scia
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

    # ------------------------------------------------------------------
    # DANNO
    # ------------------------------------------------------------------

    def take_damage(self, amount: int = 1) -> bool:
        """Applica danno al carrier con effetto shake.

        La mini-esplosione è gestita dal chiamante (game.py) che ha
        accesso alla lista esplosioni.

        Args:
            amount: Quantità di danno.

        Returns:
            True se il carrier è stato distrutto.
        """
        self.hp -= amount
        self._shake_timer = _CARRIER_SHAKE_DURATION

        if self.hp <= 0:
            self.hp = 0
            self.alive = False
            return True
        return False

    # ------------------------------------------------------------------
    # DISEGNO
    # ------------------------------------------------------------------

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna il carrier con tutti gli effetti visivi.

        Args:
            surface: Surface di destinazione.
        """
        if not self.alive:
            return

        # Scia iperspaziale
        if self.state == PowerUpCarrier.STATE_ESCAPING:
            self._draw_trail(surface)

        draw_x = int(self.x + self._shake_offset_x)
        draw_y = int(self.y + self._shake_offset_y)

        # Stretch verticale durante la fuga
        if self.state == PowerUpCarrier.STATE_ESCAPING:
            stretch_h = min(
                self.height + int(self.escape_speed * 2),
                self.height * 3)
            draw_img = pygame.transform.scale(
                self.image, (self.width, stretch_h))
            surface.blit(draw_img, (draw_x, draw_y))
        else:
            surface.blit(self.image, (draw_x, draw_y))

        # Overlay HUD (etichetta tipo, barra HP, timer)
        if self.state != PowerUpCarrier.STATE_ESCAPING:
            self._draw_carrier_hud(surface)

    def _draw_trail(self, surface: pygame.Surface) -> None:
        """Disegna le particelle scia durante la fuga.

        Usa pygame.draw.circle direttamente invece di creare una Surface
        per ogni particella per migliori prestazioni.

        Args:
            surface: Surface di destinazione.
        """
        for p in self.trail_particles:
            size = int(p["size"])
            if size <= 0:
                continue
            alpha = int(p["alpha"])
            if alpha < 20:
                continue
            factor = alpha / 255.0
            cr = min(255, int(100 * factor))
            cg = min(255, int(180 * factor))
            cb = min(255, int(255 * factor))
            pygame.draw.circle(
                surface, (cr, cg, cb),
                (int(p["x"]), int(p["y"])), size)

    def _draw_carrier_hud(self, surface: pygame.Surface) -> None:
        """Disegna l'HUD del carrier: etichetta tipo, barra HP e timer.

        Args:
            surface: Surface di destinazione.
        """
        color = POWERUP_COLORS.get(self.powerup_type, WHITE)

        label = self._hud_font.render(
            self.powerup_type.upper(), True, color)
        label_x = self.x + self.width // 2 - label.get_width() // 2
        surface.blit(label, (int(label_x), int(self.y - 14)))

        # Barra HP
        bar_w = self.width
        bar_y = self.y + self.height + 2
        hp_pct = self.hp / self.max_hp
        pygame.draw.rect(
            surface, (60, 60, 60),
            (int(self.x), int(bar_y), bar_w, 4))
        pygame.draw.rect(
            surface, color,
            (int(self.x), int(bar_y), int(bar_w * hp_pct), 4))

        # Barra countdown timer
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
                (int(self.x), int(timer_bar_y),
                 int(bar_w * timer_pct), 3))

    # ------------------------------------------------------------------
    # HITBOX
    # ------------------------------------------------------------------

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox di collisione del carrier (leggermente ridotta)."""
        shrink = 5
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width - shrink * 2,
            self.height - shrink * 2,
        )


class FallingPowerUp:
    """Oggetto power-up che cade dopo la distruzione di un carrier.

    Usa lo sprite appropriato da Assets (incluso powerup_bomba.png per le bombe).

    Args:
        x, y:         Posizione iniziale.
        powerup_type: Tipo di power-up.
    """

    def __init__(self, x: float, y: float, powerup_type: str):
        self.width  = POWERUP_ITEM_SIZE
        self.height = POWERUP_ITEM_SIZE
        self.x = x
        self.y = y
        self.powerup_type = powerup_type
        self.image = Assets.powerup_sprites[self.powerup_type]
        self.active = True
        self.fall_speed = 2.5

    def update(self) -> None:
        """Aggiorna il power-up: cade verso il basso."""
        if not self.active:
            return
        self.y += self.fall_speed
        if self.y > SCREEN_HEIGHT + 20:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna lo sprite del power-up.

        Args:
            surface: Surface di destinazione.
        """
        if not self.active:
            return
        surface.blit(self.image, (int(self.x), int(self.y)))

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox di collisione del power-up."""
        return pygame.Rect(self.x, self.y, self.width, self.height)
