"""
Classe Player - navicella del giocatore.
"""

import math
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    CYAN, GREEN, MAGENTA,
)
from core.assets import Assets
from entities.laser import Laser, AngledLaser


class Player:
    """Navicella del giocatore con sistema di vite, power-up e sparo."""

    MAX_LIVES = 3

    def __init__(self, ship_type=0):
        self.width = 60
        self.height = 60
        self.x = SCREEN_WIDTH // 2 - self.width // 2
        self.y = SCREEN_HEIGHT - 80
        self.base_speed = 5
        self.speed = self.base_speed
        self.ship_type = ship_type
        self.last_shot_time = 0
        self.shot_cooldown = 300  # millisecondi
        self.alive = True

        # ---- Sistema di vite ----
        self.lives = Player.MAX_LIVES

        # Colori per tipo di navicella
        self.colors = [CYAN, GREEN, MAGENTA]
        self.color = self.colors[ship_type]

        # Limiti di movimento
        self.min_y = SCREEN_HEIGHT // 3

        # ---- Invincibilita' temporanea dopo un colpo ----
        self.invincible = False
        self.invincible_timer = 0
        self.invincible_duration = 2 * 60  # 2 secondi

        # ---- POWER-UP STATE ----
        # Scudo
        self.shield_active = False
        self.shield_timer = 0
        self.shield_duration = 5 * 60

        # Velocita'
        self.speed_boost_active = False
        self.speed_boost_timer = 0
        self.speed_boost_duration = 5 * 60
        self.speed_boost_multiplier = 1.8

        # Arma tripla
        self.triple_shot_active = False
        self.triple_shot_timer = 0
        self.triple_shot_duration = 5 * 60

    # ========================================================================
    # UPDATE
    # ========================================================================

    def update(self, keys):
        """Aggiorna posizione, power-up e invincibilita'."""
        if not self.alive:
            return

        self._update_powerup_timers()

        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False

        current_speed = self.speed

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.x -= current_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.x += current_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.y -= current_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.y += current_speed

        # Limiti schermo
        self.x = max(0, min(SCREEN_WIDTH - self.width, self.x))
        self.y = max(self.min_y, min(SCREEN_HEIGHT - self.height, self.y))

    def _update_powerup_timers(self):
        """Aggiorna i timer dei power-up attivi."""
        if self.shield_active:
            self.shield_timer -= 1
            if self.shield_timer <= 0:
                self.shield_active = False

        if self.speed_boost_active:
            self.speed_boost_timer -= 1
            if self.speed_boost_timer <= 0:
                self.speed_boost_active = False
                self.speed = self.base_speed

        if self.triple_shot_active:
            self.triple_shot_timer -= 1
            if self.triple_shot_timer <= 0:
                self.triple_shot_active = False

    # ========================================================================
    # POWER-UP
    # ========================================================================

    def apply_powerup(self, powerup_type):
        """Applica l'effetto di un power-up al giocatore."""
        if powerup_type == "vita":
            if self.lives < Player.MAX_LIVES:
                self.lives += 1
        elif powerup_type == "scudo":
            self.shield_active = True
            self.shield_timer = self.shield_duration
        elif powerup_type == "velocita":
            self.speed_boost_active = True
            self.speed_boost_timer = self.speed_boost_duration
            self.speed = self.base_speed * self.speed_boost_multiplier
        elif powerup_type == "arma":
            self.triple_shot_active = True
            self.triple_shot_timer = self.triple_shot_duration

    # ========================================================================
    # DANNO
    # ========================================================================

    def take_damage(self):
        """Il giocatore subisce danno: perde una vita.

        Returns:
            True se il giocatore e' morto (0 vite), False altrimenti.
        """
        if self.invincible or self.shield_active:
            return False

        self.lives -= 1
        if self.lives <= 0:
            self.lives = 0
            self.alive = False
            return True
        else:
            self.invincible = True
            self.invincible_timer = self.invincible_duration
            return False

    # ========================================================================
    # SPARO
    # ========================================================================

    def shoot(self, current_time):
        """Spara laser. Gestisce nave Phoenix (doppio cannone) e power-up arma.

        Returns:
            Lista di Laser creati, o lista vuota se in cooldown.
        """
        if not self.alive:
            return []
        if current_time - self.last_shot_time < self.shot_cooldown:
            return []

        self.last_shot_time = current_time
        current_sprite = Assets.laser_sprites[self.ship_type]
        lasers = []

        if self.ship_type == 2:
            lasers = self._shoot_phoenix(current_sprite)
        else:
            lasers = self._shoot_standard(current_sprite)

        return lasers

    def _shoot_phoenix(self, sprite):
        """Sparo doppio cannone della nave Phoenix."""
        cannon_offset = 16
        center_x = self.x + self.width // 2 - 10

        lasers = [
            Laser(center_x - cannon_offset, self.y, -7, self.color, sprite=sprite),
            Laser(center_x + cannon_offset, self.y, -7, self.color, sprite=sprite),
        ]

        if self.triple_shot_active:
            left_sprite = Assets.laser_left_angular[self.ship_type]
            right_sprite = Assets.laser_right_angular[self.ship_type]
            lasers.extend([
                AngledLaser(center_x - cannon_offset, self.y, -7, -45, self.color, sprite=left_sprite),
                AngledLaser(center_x + cannon_offset, self.y, -7, 45, self.color, sprite=right_sprite),
            ])

        return lasers

    def _shoot_standard(self, sprite):
        """Sparo singolo cannone centrale (Falcon / Viper)."""
        center_x = self.x + self.width // 2 - 10
        lasers = [
            Laser(center_x, self.y, -7, self.color, sprite=sprite),
        ]

        if self.triple_shot_active:
            left_sprite = Assets.laser_left_angular[self.ship_type]
            right_sprite = Assets.laser_right_angular[self.ship_type]
            lasers.extend([
                AngledLaser(center_x, self.y, -7, -45, self.color, sprite=left_sprite),
                AngledLaser(center_x, self.y, -7, 45, self.color, sprite=right_sprite),
            ])

        return lasers

    # ========================================================================
    # DRAW
    # ========================================================================

    def draw(self, surface):
        """Disegna la navicella del giocatore con effetti (lampeggio, scudo)."""
        if not self.alive:
            return

        # Effetto lampeggio durante invincibilita'
        if self.invincible and (self.invincible_timer // 4) % 2 == 0:
            pass  # frame invisibile
        else:
            scaled_ship = pygame.transform.scale(
                Assets.player_ships[self.ship_type],
                (self.width, self.height),
            )
            surface.blit(scaled_ship, (int(self.x), int(self.y)))

        # Disegna lo scudo se attivo
        if self.shield_active:
            self._draw_shield(surface)

    def _draw_shield(self, surface):
        """Disegna l'effetto scudo attorno alla nave."""
        shield_alpha = int(abs(math.sin(self.shield_timer * 0.1)) * 60) + 60
        shield_radius = max(self.width, self.height) // 2 + 10
        shield_surf = pygame.Surface(
            (shield_radius * 2, shield_radius * 2), pygame.SRCALPHA,
        )
        pygame.draw.circle(
            shield_surf, (0, 200, 255, shield_alpha),
            (shield_radius, shield_radius), shield_radius, 3,
        )
        pygame.draw.circle(
            shield_surf, (0, 200, 255, shield_alpha // 3),
            (shield_radius, shield_radius), shield_radius - 3,
        )
        cx = self.x + self.width // 2 - shield_radius
        cy = self.y + self.height // 2 - shield_radius
        surface.blit(shield_surf, (int(cx), int(cy)))

        # Barra tempo rimanente scudo
        bar_w = self.width
        bar_x = self.x
        bar_y = self.y - 8
        pct = self.shield_timer / self.shield_duration
        pygame.draw.rect(surface, (40, 40, 40), (int(bar_x), int(bar_y), bar_w, 3))
        from core.constants import CYAN as _CYAN
        pygame.draw.rect(surface, _CYAN, (int(bar_x), int(bar_y), int(bar_w * pct), 3))

    def get_rect(self):
        """Rettangolo di collisione (leggermente ridotto)."""
        return pygame.Rect(self.x + 5, self.y + 5, self.width - 10, self.height - 10)
