"""
Classe Player -- navicella del giocatore con sprite animato da GIF.

Gestisce: movimento, sistema di vite, invincibilita' temporanea,
power-up (scudo, velocita', arma tripla) e sparo.

Le 12 navicelle disponibili provengono da ``navicelle.gif`` e ciascuna
ha un'animazione a piu' frame gestita da Pillow.
"""

import math
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_W, PLAYER_H,
    CYAN, GREEN, MAGENTA, SHIP_COLORS, NUM_PLAYER_SHIPS,
)
from core.assets import Assets
from entities.laser import Laser, AngledLaser


class Player:
    """Navicella del giocatore con sistema di vite, power-up e sparo.

    Args:
        ship_type: Indice della nave scelta (0-11).
    """

    MAX_LIVES = 3

    def __init__(self, ship_type: int = 0):
        self.width  = PLAYER_W
        self.height = PLAYER_H
        self.x: float = SCREEN_WIDTH // 2 - self.width // 2
        self.y: float = SCREEN_HEIGHT - 80
        self.base_speed = 5
        self.speed = self.base_speed
        self.ship_type = ship_type % NUM_PLAYER_SHIPS
        self.last_shot_time = 0
        self.shot_cooldown  = 300
        self.alive = True

        # Sistema di vite
        self.lives = Player.MAX_LIVES

        # Colore associato alla nave
        self.color = SHIP_COLORS[self.ship_type % len(SHIP_COLORS)]

        # Limiti di movimento verticale
        self.min_y = SCREEN_HEIGHT // 3

        # Invincibilita' temporanea
        self.invincible = False
        self.invincible_timer    = 0
        self.invincible_duration = 2 * 60

        # -- POWER-UP STATE --
        self.shield_active   = False
        self.shield_timer    = 0
        self.shield_duration = 5 * 60

        self.speed_boost_active     = False
        self.speed_boost_timer      = 0
        self.speed_boost_duration   = 5 * 60
        self.speed_boost_multiplier = 1.8

        self.triple_shot_active   = False
        self.triple_shot_timer    = 0
        self.triple_shot_duration = 5 * 60

        # Animazione GIF
        self._frame_idx   = 0
        self._frame_timer = 0
        self._frame_delay = 6

    # ========================================================================
    # UPDATE
    # ========================================================================

    def update(self, keys) -> None:
        """Aggiorna posizione, power-up, invincibilita' e animazione."""
        if not self.alive:
            return

        self._update_powerup_timers()

        # Aggiorna invincibilita'
        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False

        current_speed = self.speed

        # Movimento WASD / frecce
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

        # Avanza animazione GIF
        self._frame_timer += 1
        if self._frame_timer >= self._frame_delay:
            self._frame_timer = 0
            frames = self._get_frames()
            if frames:
                self._frame_idx = (self._frame_idx + 1) % len(frames)

    def _update_powerup_timers(self) -> None:
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

    def _get_frames(self) -> list[pygame.Surface]:
        """Restituisce i frame animati della nave corrente."""
        if self.ship_type < len(Assets.player_ship_frames):
            return Assets.player_ship_frames[self.ship_type]
        return []

    # ========================================================================
    # POWER-UP
    # ========================================================================

    def apply_powerup(self, powerup_type: str) -> None:
        """Applica l'effetto di un power-up al giocatore."""
        if powerup_type == "vita":
            if self.lives < Player.MAX_LIVES:
                self.lives += 1
        elif powerup_type == "scudo":
            self.shield_active = True
            self.shield_timer  = self.shield_duration
        elif powerup_type == "velocita":
            self.speed_boost_active = True
            self.speed_boost_timer  = self.speed_boost_duration
            self.speed = self.base_speed * self.speed_boost_multiplier
        elif powerup_type == "arma":
            self.triple_shot_active = True
            self.triple_shot_timer  = self.triple_shot_duration

    # ========================================================================
    # DANNO
    # ========================================================================

    def take_damage(self) -> bool:
        """Il giocatore subisce danno: perde una vita.

        Returns:
            ``True`` se il giocatore e' morto (0 vite).
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

    def shoot(self, current_time: int) -> list[Laser]:
        """Spara laser. Le navi con indice % 3 == 2 usano doppio cannone."""
        if not self.alive:
            return []
        if current_time - self.last_shot_time < self.shot_cooldown:
            return []

        self.last_shot_time = current_time
        current_sprite = Assets.laser_sprites[self.ship_type % len(Assets.laser_sprites)]

        # Le navi con indice % 3 == 2 usano doppio cannone (come Phoenix)
        if self.ship_type % 3 == 2:
            return self._shoot_double(current_sprite)
        return self._shoot_standard(current_sprite)

    def _shoot_double(self, sprite: pygame.Surface) -> list[Laser]:
        """Sparo doppio cannone laterale."""
        cannon_offset = 16
        center_x = self.x + self.width // 2 - 10

        lasers: list[Laser] = [
            Laser(center_x - cannon_offset, self.y, -7,
                  self.color, sprite=sprite),
            Laser(center_x + cannon_offset, self.y, -7,
                  self.color, sprite=sprite),
        ]

        if self.triple_shot_active:
            left_sprite  = Assets.laser_left_angular[self.ship_type % len(Assets.laser_left_angular)]
            right_sprite = Assets.laser_right_angular[self.ship_type % len(Assets.laser_right_angular)]
            lasers.extend([
                AngledLaser(center_x - cannon_offset, self.y, -7, -45,
                            self.color, sprite=left_sprite),
                AngledLaser(center_x + cannon_offset, self.y, -7,  45,
                            self.color, sprite=right_sprite),
            ])

        return lasers

    def _shoot_standard(self, sprite: pygame.Surface) -> list[Laser]:
        """Sparo singolo cannone centrale."""
        center_x = self.x + self.width // 2 - 10
        lasers: list[Laser] = [
            Laser(center_x, self.y, -7, self.color, sprite=sprite),
        ]

        if self.triple_shot_active:
            left_sprite  = Assets.laser_left_angular[self.ship_type % len(Assets.laser_left_angular)]
            right_sprite = Assets.laser_right_angular[self.ship_type % len(Assets.laser_right_angular)]
            lasers.extend([
                AngledLaser(center_x, self.y, -7, -45,
                            self.color, sprite=left_sprite),
                AngledLaser(center_x, self.y, -7,  45,
                            self.color, sprite=right_sprite),
            ])

        return lasers

    # ========================================================================
    # DRAW
    # ========================================================================

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna la navicella animata con effetti."""
        if not self.alive:
            return

        # Effetto lampeggio durante invincibilita'
        if self.invincible and (self.invincible_timer // 4) % 2 == 0:
            pass  # frame invisibile
        else:
            frames = self._get_frames()
            if frames:
                frame = frames[self._frame_idx % len(frames)]
                scaled_ship = pygame.transform.scale(frame, (self.width, self.height))
            else:
                # Fallback: rettangolo
                scaled_ship = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
                pygame.draw.rect(scaled_ship, self.color, (0, 0, self.width, self.height))
            surface.blit(scaled_ship, (int(self.x), int(self.y)))

        # Scudo
        if self.shield_active:
            self._draw_shield(surface)

    def _draw_shield(self, surface: pygame.Surface) -> None:
        """Disegna l'effetto scudo attorno alla nave."""
        shield_alpha  = int(abs(math.sin(self.shield_timer * 0.1)) * 60) + 60
        shield_radius = max(self.width, self.height) // 2 + 10

        shield_surf = pygame.Surface(
            (shield_radius * 2, shield_radius * 2), pygame.SRCALPHA)
        pygame.draw.circle(
            shield_surf, (0, 200, 255, shield_alpha),
            (shield_radius, shield_radius), shield_radius, 3)
        pygame.draw.circle(
            shield_surf, (0, 200, 255, shield_alpha // 3),
            (shield_radius, shield_radius), shield_radius - 3)

        cx = self.x + self.width // 2 - shield_radius
        cy = self.y + self.height // 2 - shield_radius
        surface.blit(shield_surf, (int(cx), int(cy)))

        # Barra tempo rimanente scudo
        bar_w = self.width
        bar_x = self.x
        bar_y = self.y - 8
        pct = self.shield_timer / self.shield_duration
        pygame.draw.rect(
            surface, (40, 40, 40), (int(bar_x), int(bar_y), bar_w, 3))
        pygame.draw.rect(
            surface, CYAN, (int(bar_x), int(bar_y), int(bar_w * pct), 3))

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del giocatore (ridotta per fairness)."""
        shrink = 8
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width  - shrink * 2,
            self.height - shrink * 2,
        )
