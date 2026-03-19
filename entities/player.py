"""
Classe navicella giocatore con sprite GIF animato.

Gestisce: movimento, sistema vite, invincibilità temporanea,
power-up (scudo, velocità, sparo triplo, bomba) e sparo.

5 navi disponibili con statistiche e abilità speciali uniche.
Le ultime 2 (Nova, Zenith) hanno il doppio cannone.
"""

import math
import random
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_W, PLAYER_H,
    CYAN, SHIP_COLORS, NUM_PLAYER_SHIPS,
    SHIP_STATS, SHIP_DOUBLE_CANNON,
)
from core.assets import Assets
from entities.laser import Laser, AngledLaser


class Player:
    """Navicella giocatore con vite, power-up, speciali e sparo.

    Args:
        ship_type: Indice della nave scelta (0-4).
    """

    MAX_LIVES = 3

    def __init__(self, ship_type: int = 0):
        self.width  = PLAYER_W
        self.height = PLAYER_H
        self.x: float = SCREEN_WIDTH // 2 - self.width // 2
        self.y: float = SCREEN_HEIGHT - 80
        self.ship_type = ship_type % NUM_PLAYER_SHIPS

        # Statistiche specifiche della nave
        stats = SHIP_STATS[self.ship_type] if self.ship_type < len(SHIP_STATS) else SHIP_STATS[0]
        self.base_speed = int(5 * stats["speed"])
        self.speed = self.base_speed
        self.shot_cooldown = int(300 * stats["fire_rate"])
        self.damage = stats.get("damage", 1)
        self.special = stats.get("special", "none")

        # Doppio cannone: solo per navi con flag True
        self.has_double_cannon = (
            self.ship_type < len(SHIP_DOUBLE_CANNON)
            and SHIP_DOUBLE_CANNON[self.ship_type]
        )

        self.last_shot_time = 0
        self.alive = True

        # Sistema vite
        self.lives = Player.MAX_LIVES

        # Colore nave (per laser e HUD)
        self.color = SHIP_COLORS[self.ship_type % len(SHIP_COLORS)]

        # Limiti movimento verticale
        self.min_y = SCREEN_HEIGHT // 3

        # Invincibilità temporanea dopo aver subito danno
        self.invincible          = False
        self.invincible_timer    = 0
        self.invincible_duration = 2 * 60  # 2 secondi a 60 FPS

        # -- STATO POWER-UP --
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

        # Bomba: conteggio bombe disponibili
        self.bombs = 0
        self.max_bombs = 3
        self.bomb_cooldown = 0
        self.bomb_cooldown_max = 120  # 2 secondi

        # Cooldown abilità speciali
        self.special_cooldown = 0
        self.special_active = False
        self.special_timer = 0

        # Regen (Phoenix): rigenera 1 HP ogni 15 secondi
        self._regen_timer = 0
        self._regen_interval = 15 * 60

        # Piercing (Striker): i laser attraversano i nemici
        self.piercing_shots = (self.special == "piercing")

        # EMP (Nova): stordimento ad area
        self.emp_cooldown = 0
        self.emp_max_cooldown = 20 * 60
        self.emp_ready = False

        # Overdrive (Zenith): modalità fuoco rapido temporanea
        self.overdrive_active = False
        self.overdrive_timer = 0
        self.overdrive_duration = 5 * 60
        self.overdrive_cooldown = 0
        self.overdrive_max_cooldown = 30 * 60

        # Stato animazione GIF
        self._frame_idx   = 0
        self._frame_timer = 0
        self._frame_delay = 6

        # Particelle scia motore
        self._engine_particles: list[dict] = []

        # Surface scudo cached (riusata tra i frame)
        self._shield_surf: pygame.Surface | None = None
        self._shield_radius: int = 0

    # ========================================================================
    # AGGIORNAMENTO
    # ========================================================================

    def update(self, keys) -> None:
        """Aggiorna posizione, power-up, invincibilità e animazione.

        Args:
            keys: Stato tasti Pygame da ``pygame.key.get_pressed()``.
        """
        if not self.alive:
            return

        self._update_powerup_timers()
        self._update_special_timers()

        # Aggiorna invincibilità
        if self.invincible:
            self.invincible_timer -= 1
            if self.invincible_timer <= 0:
                self.invincible = False

        current_speed = self.speed

        # Movimento WASD / frecce
        dx, dy = 0, 0
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            dx -= current_speed
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            dx += current_speed
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            dy -= current_speed
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            dy += current_speed

        # Normalizza velocità diagonale
        if dx != 0 and dy != 0:
            factor = 0.707  # 1/sqrt(2)
            dx *= factor
            dy *= factor

        self.x += dx
        self.y += dy

        # Limita ai bordi dello schermo
        self.x = max(0, min(SCREEN_WIDTH - self.width, self.x))
        self.y = max(self.min_y, min(SCREEN_HEIGHT - self.height, self.y))

        # Avanza animazione GIF
        self._frame_timer += 1
        if self._frame_timer >= self._frame_delay:
            self._frame_timer = 0
            frames = self._get_frames()
            if frames:
                self._frame_idx = (self._frame_idx + 1) % len(frames)

        # Genera particelle scia motore
        self._update_engine_particles()

    def _update_powerup_timers(self) -> None:
        """Decrementa i timer dei power-up attivi e disattiva quelli scaduti."""
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

        if self.bomb_cooldown > 0:
            self.bomb_cooldown -= 1

    def _update_special_timers(self) -> None:
        """Decrementa i cooldown e timer delle abilità speciali."""
        # Phoenix: rigenerazione HP passiva
        if self.special == "regen" and self.lives < Player.MAX_LIVES:
            self._regen_timer += 1
            if self._regen_timer >= self._regen_interval:
                self._regen_timer = 0
                self.lives = min(Player.MAX_LIVES, self.lives + 1)

        # Nova: cooldown EMP
        if self.special == "emp":
            if self.emp_cooldown > 0:
                self.emp_cooldown -= 1
            else:
                self.emp_ready = True

        # Zenith: cooldown Overdrive
        if self.special == "overdrive":
            if self.overdrive_active:
                self.overdrive_timer -= 1
                if self.overdrive_timer <= 0:
                    self.overdrive_active = False
                    self.overdrive_cooldown = self.overdrive_max_cooldown
            elif self.overdrive_cooldown > 0:
                self.overdrive_cooldown -= 1

    def _update_engine_particles(self) -> None:
        """Genera e aggiorna le particelle scia motore dietro la nave."""
        if self.alive:
            cx = self.x + self.width // 2
            by = self.y + self.height
            self._engine_particles.append({
                "x": cx + random.uniform(-6, 6),
                "y": by + random.uniform(0, 4),
                "alpha": 180,
                "size": random.uniform(1.5, 3.5),
            })

        new_particles = []
        for p in self._engine_particles:
            p["y"] += 1.5
            p["alpha"] -= 12
            p["size"] = max(0, p["size"] - 0.08)
            if p["alpha"] > 0 and p["size"] > 0:
                new_particles.append(p)
        self._engine_particles = new_particles[-30:]  # Max 30 particelle

    def _get_frames(self) -> list[pygame.Surface]:
        """Restituisce i frame animati per il tipo di nave corrente."""
        if self.ship_type < len(Assets.player_ship_frames):
            return Assets.player_ship_frames[self.ship_type]
        return []

    # ========================================================================
    # POWER-UP
    # ========================================================================

    def apply_powerup(self, powerup_type: str) -> None:
        """Applica un effetto power-up al giocatore.

        Args:
            powerup_type: Uno tra 'vita', 'scudo', 'velocita', 'arma', 'bomba'.
        """
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
        elif powerup_type == "bomba":
            self.bombs = min(self.max_bombs, self.bombs + 1)

    # ========================================================================
    # BOMBA
    # ========================================================================

    def use_bomb(self) -> bool:
        """Tenta di usare una bomba. Restituisce True se usata con successo."""
        if self.bombs > 0 and self.bomb_cooldown <= 0:
            self.bombs -= 1
            self.bomb_cooldown = self.bomb_cooldown_max
            return True
        return False

    # ========================================================================
    # ABILITÀ SPECIALI
    # ========================================================================

    def activate_emp(self) -> bool:
        """Attiva EMP (solo Nova). Restituisce True se attivato."""
        if self.special == "emp" and self.emp_ready:
            self.emp_ready = False
            self.emp_cooldown = self.emp_max_cooldown
            return True
        return False

    def activate_overdrive(self) -> bool:
        """Attiva Overdrive (solo Zenith). Restituisce True se attivato."""
        if (self.special == "overdrive" and not self.overdrive_active
                and self.overdrive_cooldown <= 0):
            self.overdrive_active = True
            self.overdrive_timer = self.overdrive_duration
            return True
        return False

    # ========================================================================
    # DANNO
    # ========================================================================

    def take_damage(self) -> bool:
        """Il giocatore subisce danno: perde una vita.

        Scudo e invincibilità vengono controllati prima di applicare il danno.

        Returns:
            True se il giocatore è morto (0 vite rimanenti).
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
        """Spara laser in base al tipo di nave e power-up attivi.

        Le navi con doppio cannone sparano due laser paralleli. Lo sparo
        triplo aggiunge laser angolati. L'overdrive dimezza il cooldown.

        Args:
            current_time: Tempo corrente in ms (da pygame.time.get_ticks).

        Returns:
            Lista di nuovi oggetti ``Laser``.
        """
        if not self.alive:
            return []

        cooldown = self.shot_cooldown
        if self.overdrive_active:
            cooldown = cooldown // 2

        if current_time - self.last_shot_time < cooldown:
            return []

        self.last_shot_time = current_time
        current_sprite = Assets.laser_sprites[
            self.ship_type % len(Assets.laser_sprites)]

        if self.has_double_cannon:
            return self._shoot_double(current_sprite)
        return self._shoot_standard(current_sprite)

    def _shoot_double(self, sprite: pygame.Surface) -> list[Laser]:
        """Spara dai doppi cannoni laterali.

        Args:
            sprite: Sprite laser da usare.

        Returns:
            Lista di oggetti ``Laser``.
        """
        cannon_offset = 16
        center_x = self.x + self.width // 2 - 10

        lasers: list[Laser] = [
            Laser(center_x - cannon_offset, self.y, -7,
                  self.color, sprite=sprite),
            Laser(center_x + cannon_offset, self.y, -7,
                  self.color, sprite=sprite),
        ]

        if self.triple_shot_active:
            left_sprite = Assets.laser_left_angular[
                self.ship_type % len(Assets.laser_left_angular)]
            right_sprite = Assets.laser_right_angular[
                self.ship_type % len(Assets.laser_right_angular)]
            lasers.extend([
                AngledLaser(center_x - cannon_offset, self.y, -7, -45,
                            self.color, sprite=left_sprite),
                AngledLaser(center_x + cannon_offset, self.y, -7, 45,
                            self.color, sprite=right_sprite),
            ])

        return lasers

    def _shoot_standard(self, sprite: pygame.Surface) -> list[Laser]:
        """Spara dal cannone centrale singolo.

        Args:
            sprite: Sprite laser da usare.

        Returns:
            Lista di oggetti ``Laser``.
        """
        center_x = self.x + self.width // 2 - 10
        lasers: list[Laser] = [
            Laser(center_x, self.y, -7, self.color, sprite=sprite),
        ]

        if self.triple_shot_active:
            left_sprite = Assets.laser_left_angular[
                self.ship_type % len(Assets.laser_left_angular)]
            right_sprite = Assets.laser_right_angular[
                self.ship_type % len(Assets.laser_right_angular)]
            lasers.extend([
                AngledLaser(center_x, self.y, -7, -45,
                            self.color, sprite=left_sprite),
                AngledLaser(center_x, self.y, -7, 45,
                            self.color, sprite=right_sprite),
            ])

        return lasers

    # ========================================================================
    # DISEGNO
    # ========================================================================

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna lo sprite nave animato con effetti visivi.

        Gestisce: scia motore, lampeggio invincibilità, tinta overdrive, scudo.

        Args:
            surface: Surface di destinazione.
        """
        if not self.alive:
            return

        # Disegna scia motore dietro la nave
        self._draw_engine_trail(surface)

        # Effetto lampeggio durante invincibilità
        if self.invincible and (self.invincible_timer // 4) % 2 == 0:
            pass  # Frame invisibile
        else:
            frames = self._get_frames()
            if frames:
                frame = frames[self._frame_idx % len(frames)]
                scaled_ship = pygame.transform.scale(
                    frame, (self.width, self.height))
            else:
                scaled_ship = pygame.Surface(
                    (self.width, self.height), pygame.SRCALPHA)
                pygame.draw.rect(
                    scaled_ship, self.color,
                    (0, 0, self.width, self.height))

            # Tinta dorata overdrive
            if self.overdrive_active:
                overlay = pygame.Surface(
                    (self.width, self.height), pygame.SRCALPHA)
                alpha = int(
                    abs(math.sin(self.overdrive_timer * 0.15)) * 60) + 30
                overlay.fill((255, 215, 0, alpha))
                scaled_ship.blit(
                    overlay, (0, 0), special_flags=pygame.BLEND_ADD)

            surface.blit(scaled_ship, (int(self.x), int(self.y)))

        # Effetto visivo scudo
        if self.shield_active:
            self._draw_shield(surface)

    def _draw_engine_trail(self, surface: pygame.Surface) -> None:
        """Disegna particelle scia motore luminose dietro la nave.

        Usa disegno diretto di cerchi invece di creare una Surface per
        particella, significativamente più veloce.

        Args:
            surface: Surface di destinazione.
        """
        r, g, b = self.color
        for p in self._engine_particles:
            size = max(1, int(p["size"]))
            alpha = max(0, min(255, int(p["alpha"])))
            if alpha < 30:
                continue  # Salta particelle quasi invisibili
            factor = alpha / 255.0
            cr = min(255, int(r * factor))
            cg = min(255, int(g * factor))
            cb = min(255, int(b * factor))
            pygame.draw.circle(
                surface, (cr, cg, cb),
                (int(p["x"]), int(p["y"])), size,
            )

    def _draw_shield(self, surface: pygame.Surface) -> None:
        """Disegna la bolla scudo e la sua barra tempo rimanente.

        Riusa una surface scudo cached e ridisegna solo le parti dinamiche.

        Args:
            surface: Surface di destinazione.
        """
        shield_alpha  = int(
            abs(math.sin(self.shield_timer * 0.1)) * 60) + 60
        shield_radius = max(self.width, self.height) // 2 + 10

        # Ricrea la surface scudo solo se il raggio è cambiato
        if self._shield_surf is None or self._shield_radius != shield_radius:
            self._shield_radius = shield_radius
            self._shield_surf = pygame.Surface(
                (shield_radius * 2, shield_radius * 2), pygame.SRCALPHA)

        self._shield_surf.fill((0, 0, 0, 0))
        pygame.draw.circle(
            self._shield_surf, (0, 200, 255, shield_alpha),
            (shield_radius, shield_radius), shield_radius, 3)
        pygame.draw.circle(
            self._shield_surf, (0, 200, 255, shield_alpha // 3),
            (shield_radius, shield_radius), shield_radius - 3)

        cx = self.x + self.width // 2 - shield_radius
        cy = self.y + self.height // 2 - shield_radius
        surface.blit(self._shield_surf, (int(cx), int(cy)))

        # Barra tempo scudo
        bar_w = self.width
        bar_x = self.x
        bar_y = self.y - 8
        pct = self.shield_timer / self.shield_duration
        pygame.draw.rect(
            surface, (40, 40, 40),
            (int(bar_x), int(bar_y), bar_w, 3))
        pygame.draw.rect(
            surface, CYAN,
            (int(bar_x), int(bar_y), int(bar_w * pct), 3))

    # ========================================================================
    # HITBOX
    # ========================================================================

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del giocatore (ridotta per equità).

        La hitbox è 16px più piccola dello sprite visivo su ogni asse.
        """
        shrink = 8
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width - shrink * 2,
            self.height - shrink * 2,
        )
