"""Space Shooter -- Infinite Survival  |  game.py v10 (release)

Autori: Ceccariglia Emanuele & Andrea Cestelli -- ITSUmbria 2026

Game loop principale, gestione stati, spawn, collisioni, HUD e pausa.

Novita' v10:
- Fix critico: grace period ora permette al giocatore di muoversi.
- Fix: direzione boss h_speed ora casuale (non sempre a destra).
- Fix: scudo assorbe completamente il colpo asteroide (senza perdere vita).
- Fix: invincibilita' temporanea attivata dopo rottura scudo in tutti i casi.
- Fix: collisione boss con scudo attivo ora da' invincibilita' temporanea.
- Miglioramento: coerenza logica di tutte le collisioni con scudo/invincibilita'.
- Test completi: 45+ test automatizzati passati con successo.
"""

import math
import random
import sys

import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    BLACK, WHITE, RED, GREEN, YELLOW, CYAN, MAGENTA, ORANGE, GOLD,
    DARK_GRAY, POWERUP_ITEM_SIZE,
    DIFFICULTY_INTERVAL, DIFFICULTY_SPEED_SCALE, DIFFICULTY_MAX_LEVEL,
    NUM_PLAYER_SHIPS, SHIP_NAMES, SHIP_DESCRIPTIONS, SHIP_COLORS,
    SHIP_UNLOCK_SCORES, NUM_BOSS_VARIANTS, SHIP_STATS,
    SHIP_DOUBLE_CANNON,
    COMBO_TIMEOUT_FRAMES, COMBO_MULT_THRESHOLDS, COMBO_SCORE_BONUS,
    SHAKE_INTENSITY_LIGHT, SHAKE_INTENSITY_MEDIUM, SHAKE_INTENSITY_HEAVY,
    GRACE_PERIOD_FRAMES, SLOW_MO_DURATION, SLOW_MO_FACTOR,
    BOSS_NAMES, ENEMY_TYPE_STATS,
)
from core.assets import Assets
from core.sounds import create_sounds, generate_background_music
from core.save_manager import load_save_data, save_data, check_unlocks

from entities.player import Player
from entities.boss import Boss
from entities.laser import Laser
from entities.explosion import Explosion
from entities.powerup import PowerUpCarrier, FallingPowerUp
from entities.asteroid import Asteroid, clear_registry
from entities.formations import (
    pick_formation, build_spawn_positions, reset_formation_history,
)
from entities.formation_group import FormationGroup

from world.starfield import StarField

# Costante anti-overlap verticale tra gruppi
_MIN_GROUP_V_GAP = 140


def _fmt_time(total_secs: int) -> str:
    """Formatta i secondi come M:SS."""
    m, s = divmod(total_secs, 60)
    return f"{m}:{s:02d}"


class Game:
    """Classe principale del gioco."""

    # ======================================================================
    # INIT
    # ======================================================================

    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter - Infinite Survival")
        self.clock = pygame.time.Clock()

        Assets.load()

        self.sounds   = create_sounds()
        self.bg_music = generate_background_music(duration_ms=8000, volume=0.12)
        self.stars    = StarField()
        self.save     = load_save_data()

        # Font -- dimensioni corrette per leggibilita'
        self.font_title  = pygame.font.Font(None, 72)
        self.font_large  = pygame.font.Font(None, 52)
        self.font_medium = pygame.font.Font(None, 34)
        self.font_small  = pygame.font.Font(None, 26)
        self.font_tiny   = pygame.font.Font(None, 20)
        self.font_hud    = pygame.font.Font(None, 28)

        # Stato
        self.state: str            = "menu"
        self.selected_ship: int    = 0
        self._prev_selected_ship: int = 0
        self.menu_selection: int   = 0
        self._music_channel        = None
        self._credits_scroll: float = float(SCREEN_HEIGHT)
        self._pause_selection: int = 0

        # Pagina corrente nella selezione navi
        self._ship_page: int = 0

        # Risultato sblocco navi
        self._newly_unlocked: list[int] = []

        # Screen shake
        self._shake_timer: int    = 0
        self._shake_intensity: int = 0
        self._shake_offset_x: int = 0
        self._shake_offset_y: int = 0

        # Slow motion
        self._slow_mo_timer: int = 0

        self.reset_game()

    # ======================================================================
    # MUSICA
    # ======================================================================

    def _start_music(self) -> None:
        if self._music_channel is None or not self._music_channel.get_busy():
            self._music_channel = self.bg_music.play(loops=-1)

    def _stop_music(self) -> None:
        if self._music_channel:
            self._music_channel.stop()

    # ======================================================================
    # RESET
    # ======================================================================

    def reset_game(self) -> None:
        clear_registry()
        reset_formation_history()

        self.player = Player(self.selected_ship)

        self.formation_groups: list[FormationGroup] = []
        self.player_lasers:    list[Laser]          = []
        self.enemy_lasers:     list[Laser]          = []
        self.explosions:       list[Explosion]       = []
        self.carriers:         list[PowerUpCarrier]  = []
        self.falling_powerups: list[FallingPowerUp]  = []
        self.asteroids:        list[Asteroid]        = []

        self.score     = 0
        self.game_time = 0

        self.spawn_timer    = 0
        self.spawn_interval = random.randint(120, 300)

        # Boss
        self.boss: Boss | None     = None
        self.boss_active: bool     = False
        self.boss_warning: bool    = False
        self.boss_warning_timer    = 0
        self.boss_warning_dur      = 180
        self.boss_defeated_count   = 0
        self.next_boss_time        = random.randint(50 * 60, 90 * 60)

        # Carrier power-up
        self.carrier_timer    = 0
        self.carrier_interval = random.randint(12 * 60, 28 * 60)

        # Asteroidi singoli
        self.asteroid_timer    = 0
        self.asteroid_interval = random.randint(10 * 60, 22 * 60)

        # Pioggia di asteroidi
        self.rain_active: bool   = False
        self.rain_warning: bool  = False
        self.rain_w_timer        = 0
        self.rain_w_dur          = 180
        self.rain_timer          = 0
        self.rain_dur            = 0
        self.rain_spawn_t        = 0
        self.rain_spawn_i        = 35
        self.next_rain           = random.randint(180 * 60, 360 * 60)
        self.rain_cooldown       = 0
        self.rain_max            = 0
        self.rain_draining: bool = False

        # Difficolta'
        self._diff_level = 0
        self._next_diff  = DIFFICULTY_INTERVAL * 60

        # Pausa
        self._paused: bool     = False
        self._pause_selection  = 0

        # Combo system
        self._combo_count: int   = 0
        self._combo_timer: int   = 0
        self._combo_mult: float  = 0.0
        self._combo_display: int = 0
        self._combo_best: int    = 0
        self._total_kills: int   = 0

        # Grace period
        self._grace_timer: int = GRACE_PERIOD_FRAMES
        self._grace_active: bool = True

        # Damage numbers floating
        self._damage_numbers: list[dict] = []

        # Slow motion
        self._slow_mo_timer = 0

        # EMP visual effect
        self._emp_flash: int = 0

        # Bomb visual effect
        self._bomb_flash: int = 0

    # ======================================================================
    # DIFFICOLTA'
    # ======================================================================

    def _speed_mult(self) -> float:
        return DIFFICULTY_SPEED_SCALE ** self._diff_level

    def _update_diff(self) -> None:
        if self._diff_level >= DIFFICULTY_MAX_LEVEL:
            return
        if self.game_time >= self._next_diff:
            self._diff_level += 1
            self._next_diff += DIFFICULTY_INTERVAL * 60

    # ======================================================================
    # SCREEN SHAKE
    # ======================================================================

    def _trigger_shake(self, intensity: int) -> None:
        self._shake_intensity = intensity
        self._shake_timer = max(self._shake_timer, intensity * 2)

    def _update_shake(self) -> None:
        if self._shake_timer > 0:
            self._shake_timer -= 1
            ratio = self._shake_timer / max(1, self._shake_intensity * 2)
            amp = int(self._shake_intensity * ratio)
            self._shake_offset_x = random.randint(-amp, amp)
            self._shake_offset_y = random.randint(-amp, amp)
        else:
            self._shake_offset_x = 0
            self._shake_offset_y = 0

    # ======================================================================
    # COMBO SYSTEM
    # ======================================================================

    def _register_kill(self, base_score: int, x: float, y: float) -> int:
        self._combo_count += 1
        self._combo_timer = COMBO_TIMEOUT_FRAMES
        self._total_kills += 1
        if self._combo_count > self._combo_best:
            self._combo_best = self._combo_count

        self._combo_mult = 0.0
        for i, threshold in enumerate(COMBO_MULT_THRESHOLDS):
            if self._combo_count >= threshold:
                self._combo_mult = COMBO_SCORE_BONUS[i]

        effective_score = int(base_score * (1.0 + self._combo_mult))
        self._combo_display = 90

        self._damage_numbers.append({
            "x": x, "y": y, "text": f"+{effective_score}",
            "timer": 60, "color": YELLOW if self._combo_mult > 0 else WHITE,
        })
        if self._combo_count >= 3:
            self._damage_numbers.append({
                "x": x, "y": y - 20,
                "text": f"x{self._combo_count} COMBO!",
                "timer": 60,
                "color": ORANGE if self._combo_count >= 10 else CYAN,
            })

        return effective_score

    def _update_combo(self) -> None:
        if self._combo_timer > 0:
            self._combo_timer -= 1
            if self._combo_timer <= 0:
                self._combo_count = 0
                self._combo_mult = 0.0
        if self._combo_display > 0:
            self._combo_display -= 1
        for dn in self._damage_numbers:
            dn["timer"] -= 1
            dn["y"] -= 0.8
        self._damage_numbers = [d for d in self._damage_numbers if d["timer"] > 0]

    # ======================================================================
    # ANTI-OVERLAP TRA GRUPPI
    # ======================================================================

    def _can_spawn_group(self) -> bool:
        if not self.formation_groups:
            return True
        if len(self.formation_groups) >= 3:
            return False
        for g in self.formation_groups:
            if not g.is_empty and g.top_edge < _MIN_GROUP_V_GAP:
                return False
        return True

    def _total_alive(self) -> int:
        return sum(len(g.alive_enemies) for g in self.formation_groups)

    # ======================================================================
    # SPAWN
    # ======================================================================

    def _spawn_formation(self) -> None:
        if self.boss_active or self.boss_warning:
            return
        if self.rain_active or self.rain_warning or self.rain_draining:
            return

        max_alive = 6 + self._diff_level * 2
        if self._total_alive() >= max_alive:
            return
        if not self._can_spawn_group():
            return

        self.spawn_timer += 1
        if self.spawn_timer < self.spawn_interval:
            return

        self.spawn_timer = 0
        base_min = max(80, 220 - self._diff_level * 18)
        base_max = max(base_min + 40, 440 - self._diff_level * 35)
        self.spawn_interval = random.randint(base_min, base_max)

        name, slots = pick_formation(self._diff_level)
        data  = build_spawn_positions(slots, self.formation_groups)
        group = FormationGroup(data, self._speed_mult(), name, self._diff_level)
        self.formation_groups.append(group)

    def _spawn_carriers(self) -> None:
        self.carrier_timer += 1
        if self.carrier_timer >= self.carrier_interval:
            self.carrier_timer = 0
            self.carrier_interval = random.randint(12 * 60, 28 * 60)
            if len(self.carriers) < 2:
                self.carriers.append(PowerUpCarrier())

    def _spawn_asteroids(self) -> None:
        if self.rain_active or self.rain_warning or self.rain_draining:
            return
        self.asteroid_timer += 1
        if self.asteroid_timer >= self.asteroid_interval:
            self.asteroid_timer = 0
            self.asteroid_interval = random.randint(10 * 60, 22 * 60)
            if len(self.asteroids) < 2:
                ast = Asteroid()
                if ast.active:
                    self.asteroids.append(ast)
                    self.sounds["asteroid_warning"].play()

    # ======================================================================
    # EVENTI SPECIALI: BOSS
    # ======================================================================

    def _check_boss(self) -> None:
        if self.boss_active or self.boss_warning:
            return
        if self.rain_active or self.rain_warning or self.rain_draining:
            return
        if self.game_time >= self.next_boss_time:
            self.boss_warning = True
            self.boss_warning_timer = 0
            self.sounds["boss_warning"].play()

    def _do_spawn_boss(self) -> None:
        # Boss casuale con uguale probabilita' per ognuno dei 5
        variant = Boss.random_variant()
        self.boss = Boss(variant=variant)
        self.boss_active  = True
        self.boss_warning = False

        bonus = self.boss_defeated_count * 10
        self.boss.max_hp = 60 + bonus
        self.boss.hp     = self.boss.max_hp
        base_h = 2.0 + self.boss_defeated_count * 0.3
        self.boss.h_speed = random.choice([-1, 1]) * base_h
        self.boss.shoot_interval = max(22, 55 - self.boss_defeated_count * 4)

        self.formation_groups.clear()
        self.enemy_lasers.clear()

    def _on_boss_defeated(self) -> None:
        cx = self.boss.x + self.boss.width // 2
        cy = self.boss.y + self.boss.height // 2

        self.explosions.append(Explosion(cx, cy, size=128))
        for _ in range(6):
            self.explosions.append(Explosion(
                self.boss.x + random.randint(0, self.boss.width),
                self.boss.y + random.randint(0, self.boss.height),
                size=random.randint(48, 80)))
        self.sounds["boss_defeated"].play()
        self._trigger_shake(SHAKE_INTENSITY_HEAVY)

        # Slow motion
        self._slow_mo_timer = SLOW_MO_DURATION

        base_score = 25 + self.boss_defeated_count * 8
        pts = self._register_kill(base_score, cx, cy)
        self.score += pts
        self.boss_defeated_count += 1
        self.boss_active = False
        self.boss = None

        self.next_boss_time = self.game_time + random.randint(50 * 60, 90 * 60)
        self.enemy_lasers.clear()

    # ======================================================================
    # NUOVE MECCANICHE: BOMBA, EMP
    # ======================================================================

    def _use_bomb(self) -> None:
        """Attiva una bomba: distrugge tutti i nemici e laser sullo schermo."""
        if not self.player.use_bomb():
            return

        self._bomb_flash = 30
        self._trigger_shake(SHAKE_INTENSITY_HEAVY)
        self.sounds["explosion"].play()

        # Distruggi tutti i nemici
        for group in self.formation_groups:
            for enemy in group.alive_enemies:
                if enemy.alive:
                    enemy.alive = False
                    ex = enemy.x + enemy.width // 2
                    ey = enemy.y + enemy.height // 2
                    self.explosions.append(Explosion(ex, ey))
                    pts = self._register_kill(
                        group.get_score_for_enemy(enemy), ex, ey)
                    self.score += pts

        # Cancella laser nemici
        self.enemy_lasers.clear()

        # Danneggia boss (50% HP residuo)
        if self.boss_active and self.boss and self.boss.alive:
            dmg = max(5, self.boss.hp // 4)
            if self.boss.take_damage(dmg):
                self._on_boss_defeated()

    def _use_emp(self) -> None:
        """Attiva EMP: rallenta tutti i nemici e cancella i loro laser."""
        if not self.player.activate_emp():
            return

        self._emp_flash = 25
        self._trigger_shake(SHAKE_INTENSITY_LIGHT)
        self.sounds["shield_active"].play()

        # Cancella tutti i laser nemici
        self.enemy_lasers.clear()

        # Stordisci nemici: azzera i loro timer di sparo
        for group in self.formation_groups:
            for enemy in group.alive_enemies:
                enemy.shoot_timer = 0
                enemy.shoot_interval = int(enemy.shoot_interval * 1.5)

    def _use_overdrive(self) -> None:
        """Attiva Overdrive (Zenith): fuoco rapido temporaneo."""
        if self.player.activate_overdrive():
            self.sounds["powerup_collect"].play()

    # ======================================================================
    # EVENTI SPECIALI: PIOGGIA DI ASTEROIDI
    # ======================================================================

    def _check_rain(self) -> None:
        if self.rain_active or self.rain_warning or self.rain_draining:
            return
        if self.boss_active or self.boss_warning:
            return
        if self.rain_cooldown > 0:
            self.rain_cooldown -= 1
            return
        if self.game_time >= self.next_rain:
            self.rain_warning = True
            self.rain_w_timer = 0
            self.sounds["asteroid_rain_warning"].play()

    def _start_rain(self) -> None:
        self.rain_active   = True
        self.rain_warning  = False
        self.rain_draining = False

        base_dur = 20 * 60 + self._diff_level * 20
        self.rain_dur     = min(base_dur, 40 * 60)
        self.rain_timer   = 0
        self.rain_spawn_t = 0
        self.rain_spawn_i = max(22, 45 - self._diff_level * 3)
        self.rain_max     = 4 + self._diff_level

        self.formation_groups.clear()
        self.enemy_lasers.clear()
        for a in self.asteroids:
            a.deactivate()
        self.asteroids.clear()
        clear_registry()

    def _end_rain(self) -> None:
        self.rain_active   = False
        self.rain_draining = True

    def _finish_rain_drain(self) -> None:
        self.rain_draining = False
        self.rain_cooldown = random.randint(120 * 60, 240 * 60)
        self.next_rain     = self.game_time + random.randint(180 * 60, 360 * 60)
        clear_registry()

    # ======================================================================
    # UPDATE GAMEPLAY
    # ======================================================================

    def update_game(self) -> None:
        if self._paused:
            return

        self._update_shake()
        self._update_combo()

        # EMP/Bomb flash decay
        if self._emp_flash > 0:
            self._emp_flash -= 1
        if self._bomb_flash > 0:
            self._bomb_flash -= 1

        # Slow motion: salta frame
        if self._slow_mo_timer > 0:
            self._slow_mo_timer -= 1
            if random.random() > SLOW_MO_FACTOR:
                return  # Skip frame per effetto slow-mo

        # Grace period: il giocatore puo' muoversi ma i nemici non spawnano
        if self._grace_active:
            self._grace_timer -= 1
            if self._grace_timer <= 0:
                self._grace_active = False

        self.game_time += 1
        self._update_diff()
        keys = pygame.key.get_pressed()

        # Durante il grace period aggiorna solo il giocatore
        if self._grace_active:
            self.player.update(keys)
            return

        if self.boss_warning:
            self._upd_boss_warning(keys)
        elif self.rain_warning:
            self._upd_rain_warning(keys)
        elif self.rain_active:
            self._upd_rain(keys)
        elif self.rain_draining:
            self._upd_rain_drain(keys)
        else:
            self._upd_normal(keys)

    def _upd_boss_warning(self, keys) -> None:
        self.boss_warning_timer += 1
        if self.boss_warning_timer >= self.boss_warning_dur:
            self._do_spawn_boss()
        self.player.update(keys)
        for g in self.formation_groups:
            g.update()
        self._upd_explosions()
        self._upd_asteroids()

    def _upd_rain_warning(self, keys) -> None:
        self.rain_w_timer += 1
        if self.rain_w_timer >= self.rain_w_dur:
            self._start_rain()
        self.player.update(keys)
        self._upd_explosions()

    def _upd_rain(self, keys) -> None:
        self.rain_timer += 1
        if self.rain_timer >= self.rain_dur:
            self._end_rain()
        else:
            self.rain_spawn_t += 1
            if (self.rain_spawn_t >= self.rain_spawn_i
                    and len(self.asteroids) < self.rain_max):
                self.rain_spawn_t = 0
                ast = Asteroid()
                if ast.active:
                    self.asteroids.append(ast)

        self.player.update(keys)
        self._shoot(keys)
        self._upd_all_entities()

        pr = self.player.get_rect()
        self._chk_asteroid_player(pr)
        self._chk_pu_player(pr)
        self._cleanup()
        if not self.player.alive:
            self._game_over()

    def _upd_rain_drain(self, keys) -> None:
        self.player.update(keys)
        self._shoot(keys)
        self._upd_all_entities()

        pr = self.player.get_rect()
        self._chk_asteroid_player(pr)
        self._chk_pu_player(pr)
        self._cleanup()

        if not self.asteroids:
            self._finish_rain_drain()

        if not self.player.alive:
            self._game_over()

    def _upd_normal(self, keys) -> None:
        self.player.update(keys)
        self._shoot(keys)

        self._check_boss()
        self._check_rain()

        self._spawn_formation()
        self._spawn_carriers()
        self._spawn_asteroids()

        # Update boss
        if self.boss_active and self.boss and self.boss.alive:
            for bl in self.boss.update():
                self.enemy_lasers.append(bl)
                if random.random() < 0.3:
                    self.sounds["boss_laser"].play()

        # Update formazioni
        hit_bottom = False
        for g in self.formation_groups:
            fell = g.update()
            if fell:
                hit_bottom = True
            for laser in g.pending_lasers:
                self.enemy_lasers.append(laser)
                if random.random() < 0.5:
                    self.sounds["enemy_laser"].play()

        if hit_bottom:
            dead = self.player.take_damage()
            self._trigger_shake(SHAKE_INTENSITY_MEDIUM)
            if dead:
                self._player_death_expl()
            else:
                self.sounds["player_hit"].play()
            self.formation_groups = [
                g for g in self.formation_groups
                if g.bottom_edge < SCREEN_HEIGHT
            ]

        self._upd_all_entities()
        self._check_all()
        self._cleanup()

        if not self.player.alive:
            self._game_over()

    # -- Utilita' di update --

    def _shoot(self, keys) -> None:
        if keys[pygame.K_SPACE]:
            lasers = self.player.shoot(pygame.time.get_ticks())
            if lasers:
                self.player_lasers.extend(lasers)
                self.sounds["laser"].play()

    def _upd_all_entities(self) -> None:
        for laser in self.player_lasers:
            laser.update()
        for laser in self.enemy_lasers:
            laser.update()
        for expl in self.explosions:
            expl.update()
        for carrier in self.carriers:
            carrier.update()
        for pu in self.falling_powerups:
            pu.update()
        for ast in self.asteroids:
            ast.update()

    def _upd_explosions(self) -> None:
        for expl in self.explosions:
            expl.update()
        self.explosions = [e for e in self.explosions if e.active]

    def _upd_asteroids(self) -> None:
        for ast in self.asteroids:
            ast.update()
        self.asteroids = [a for a in self.asteroids if a.active]

    def _cleanup(self) -> None:
        self.player_lasers    = [l for l in self.player_lasers    if l.active]
        self.enemy_lasers     = [l for l in self.enemy_lasers     if l.active]
        self.formation_groups = [g for g in self.formation_groups if not g.is_empty]
        self.explosions       = [e for e in self.explosions       if e.active]
        self.carriers         = [c for c in self.carriers         if c.alive]
        self.falling_powerups = [p for p in self.falling_powerups if p.active]
        self.asteroids        = [a for a in self.asteroids        if a.active]

    # ======================================================================
    # COLLISIONI
    # ======================================================================

    def _check_all(self) -> None:
        pr = self.player.get_rect()
        self._chk_pl_vs_boss()
        self._chk_pl_vs_carrier()
        self._chk_pl_vs_formations()
        self._chk_el_vs_player(pr)
        self._chk_boss_vs_player(pr)
        self._chk_formation_vs_player(pr)
        self._chk_asteroid_player(pr)
        self._chk_pu_player(pr)

    def _chk_pl_vs_boss(self) -> None:
        """Laser giocatore -> boss."""
        if not (self.boss_active and self.boss and self.boss.alive):
            return
        dmg = self.player.damage
        for laser in self.player_lasers:
            if not laser.active:
                continue
            if self.boss is None or not self.boss.alive:
                break
            if laser.get_rect().colliderect(self.boss.get_rect()):
                laser.active = False
                self.sounds["boss_hit"].play()
                self._trigger_shake(SHAKE_INTENSITY_LIGHT)
                self.explosions.append(Explosion(
                    laser.x + Laser.WIDTH // 2,
                    laser.y, size=32))
                if self.boss.take_damage(dmg):
                    self._on_boss_defeated()
                    break

    def _chk_pl_vs_carrier(self) -> None:
        """Laser giocatore -> carrier."""
        dmg = self.player.damage
        for laser in self.player_lasers:
            if not laser.active:
                continue
            for carrier in self.carriers:
                if not carrier.alive:
                    continue
                if laser.get_rect().colliderect(carrier.get_rect()):
                    laser.active = False
                    destroyed = carrier.take_damage(dmg)
                    if destroyed:
                        self.explosions.append(Explosion(
                            carrier.x + carrier.width // 2,
                            carrier.y + carrier.height // 2))
                        self.sounds["carrier_destroyed"].play()
                        self.falling_powerups.append(FallingPowerUp(
                            carrier.x + carrier.width // 2 - POWERUP_ITEM_SIZE // 2,
                            carrier.y + carrier.height // 2 - POWERUP_ITEM_SIZE // 2,
                            carrier.powerup_type))
                    else:
                        self.sounds["carrier_hit"].play()
                        self.explosions.append(Explosion(
                            laser.x + Laser.WIDTH // 2,
                            laser.y, size=28))
                    break

    def _chk_pl_vs_formations(self) -> None:
        """Laser giocatore -> nemici nelle formazioni."""
        dmg = self.player.damage
        piercing = self.player.piercing_shots
        for laser in self.player_lasers:
            if not laser.active:
                continue
            hit = False
            for group in self.formation_groups:
                for rect, enemy in group.get_alive_rects():
                    if laser.get_rect().colliderect(rect):
                        if not piercing:
                            laser.active = False
                        dead = enemy.take_damage(dmg)
                        if dead:
                            ex = enemy.x + enemy.width // 2
                            ey = enemy.y + enemy.height // 2
                            pts = self._register_kill(
                                group.get_score_for_enemy(enemy), ex, ey)
                            self.score += pts
                            self.explosions.append(Explosion(ex, ey))
                            self.sounds["explosion"].play()
                        else:
                            self.sounds["boss_hit"].play()
                            self.explosions.append(Explosion(
                                laser.x + Laser.WIDTH // 2,
                                laser.y, size=28))
                        hit = True
                        if not piercing:
                            break
                if hit and not piercing:
                    break

    def _chk_el_vs_player(self, pr: pygame.Rect) -> None:
        """Laser nemici -> giocatore."""
        for laser in self.enemy_lasers:
            if not laser.active:
                continue
            if laser.get_rect().colliderect(pr):
                laser.active = False
                if self.player.shield_active:
                    self.sounds["shield_active"].play()
                    self._trigger_shake(SHAKE_INTENSITY_LIGHT)
                    self.player.shield_timer = max(
                        0, self.player.shield_timer - 30)
                    if self.player.shield_timer <= 0:
                        self.player.shield_active = False
                        self.sounds["shield_break"].play()
                        # Attiva invincibilita' temporanea dopo rottura scudo
                        self.player.invincible = True
                        self.player.invincible_timer = self.player.invincible_duration // 2
                elif not self.player.invincible:
                    dead = self.player.take_damage()
                    self._trigger_shake(SHAKE_INTENSITY_MEDIUM)
                    if dead:
                        self._player_death_expl()
                    else:
                        self.sounds["player_hit"].play()

    def _chk_boss_vs_player(self, pr: pygame.Rect) -> None:
        """Corpo boss -> giocatore."""
        if not (self.boss_active and self.boss and self.boss.alive):
            return
        if self.boss.get_rect().colliderect(pr):
            if self.player.shield_active:
                self.sounds["shield_active"].play()
                self.player.shield_active = False
                self.player.shield_timer = 0
                self.sounds["shield_break"].play()
                self._trigger_shake(SHAKE_INTENSITY_MEDIUM)
                # Invincibilita' temporanea dopo rottura scudo dal boss
                self.player.invincible = True
                self.player.invincible_timer = self.player.invincible_duration
            elif not self.player.invincible:
                self.player.lives = 0
                self.player.alive = False
                self._player_death_expl()
                self._trigger_shake(SHAKE_INTENSITY_HEAVY)

    def _chk_formation_vs_player(self, pr: pygame.Rect) -> None:
        """Corpo nemico -> giocatore."""
        for group in self.formation_groups:
            for rect, enemy in group.get_alive_rects():
                if rect.colliderect(pr):
                    enemy.alive = False
                    self.explosions.append(Explosion(
                        enemy.x + enemy.width // 2,
                        enemy.y + enemy.height // 2))
                    if self.player.shield_active:
                        self.sounds["shield_active"].play()
                        self.player.shield_timer = max(
                            0, self.player.shield_timer - 60)
                        if self.player.shield_timer <= 0:
                            self.player.shield_active = False
                            self.sounds["shield_break"].play()
                            # Invincibilita' post-rottura scudo
                            self.player.invincible = True
                            self.player.invincible_timer = self.player.invincible_duration // 2
                        self._trigger_shake(SHAKE_INTENSITY_LIGHT)
                    elif not self.player.invincible:
                        dead = self.player.take_damage()
                        self._trigger_shake(SHAKE_INTENSITY_MEDIUM)
                        if dead:
                            self._player_death_expl()
                        else:
                            self.sounds["player_hit"].play()
                    return

    def _chk_asteroid_player(self, pr: pygame.Rect) -> None:
        """Asteroide -> giocatore.

        Asteroide e' devastante:
        - Con scudo: lo scudo si rompe ma assorbe il colpo.
        - Senza scudo (e non invincibile): morte istantanea.
        """
        for ast in self.asteroids:
            if not ast.active:
                continue
            if ast.get_rect().colliderect(pr):
                if self.player.shield_active:
                    # Lo scudo assorbe il colpo dell'asteroide
                    self.player.shield_active = False
                    self.player.shield_timer = 0
                    self.sounds["shield_break"].play()
                    self._trigger_shake(SHAKE_INTENSITY_HEAVY)
                    # Attiva invincibilita' temporanea
                    self.player.invincible = True
                    self.player.invincible_timer = self.player.invincible_duration
                elif self.player.invincible:
                    pass
                else:
                    # Morte istantanea
                    self.player.lives = 0
                    self.player.alive = False
                    self.explosions.append(Explosion(
                        self.player.x + self.player.width // 2,
                        self.player.y + self.player.height // 2,
                        size=128))
                    self.sounds["game_over"].play()
                    self._trigger_shake(SHAKE_INTENSITY_HEAVY)
                return

    def _chk_pu_player(self, pr: pygame.Rect) -> None:
        """Power-up cadente -> giocatore."""
        for pu in self.falling_powerups:
            if not pu.active:
                continue
            if pu.get_rect().colliderect(pr):
                pu.active = False
                self.player.apply_powerup(pu.powerup_type)
                self.sounds["powerup_collect"].play()
                if pu.powerup_type == "scudo":
                    self.sounds["shield_active"].play()
                elif pu.powerup_type == "bomba":
                    self._damage_numbers.append({
                        "x": pu.x, "y": pu.y - 20,
                        "text": "BOMBA!",
                        "timer": 60, "color": MAGENTA,
                    })

    def _player_death_expl(self) -> None:
        self.explosions.append(Explosion(
            self.player.x + self.player.width // 2,
            self.player.y + self.player.height // 2,
            size=96))
        self.sounds["game_over"].play()

    # ======================================================================
    # GAME OVER
    # ======================================================================

    def _game_over(self) -> None:
        self._stop_music()

        if self.score > self.save["high_score"]:
            self.save["high_score"] = self.score

        self._newly_unlocked = check_unlocks(self.save)
        if self._newly_unlocked:
            self.sounds["unlock"].play()

        # Aggiorna statistiche cumulative
        self.save["total_playtime"] = self.save.get("total_playtime", 0) + self.game_time // 60
        self.save["total_kills"] = self.save.get("total_kills", 0) + self._total_kills
        self.save["bosses_defeated"] = self.save.get("bosses_defeated", 0) + self.boss_defeated_count

        self.save["best_scores"].append(self.score)
        self.save["best_scores"].sort(reverse=True)
        self.save["best_scores"] = self.save["best_scores"][:10]
        save_data(self.save)

        self.state = "game_over"

    # ======================================================================
    # PAUSA
    # ======================================================================

    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        self._pause_selection = 0
        if self._paused:
            self.sounds["pause"].play()
            if self._music_channel:
                self._music_channel.pause()
        else:
            self.sounds["resume"].play()
            if self._music_channel:
                self._music_channel.unpause()

    def _resume_from_pause(self) -> None:
        self._paused = False
        self._pause_selection = 0
        self.sounds["resume"].play()
        if self._music_channel:
            self._music_channel.unpause()

    def _quit_to_menu_from_pause(self) -> None:
        self._paused = False
        self._pause_selection = 0
        self._stop_music()
        self.state = "menu"
        self.sounds["select"].play()

    # ======================================================================
    # DRAW
    # ======================================================================

    # -- MENU --

    def draw_menu(self) -> None:
        self.screen.fill(DARK_GRAY)
        self.stars.draw(self.screen)

        t1 = self.font_title.render("SPACE SHOOTER", True, CYAN)
        t2 = self.font_medium.render("Infinite Survival", True, WHITE)
        self.screen.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 60))
        self.screen.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 130))

        frames = Assets.player_ship_frames
        if self.selected_ship < len(frames) and frames[self.selected_ship]:
            preview = pygame.transform.scale(
                frames[self.selected_ship][0], (70, 70))
            self.screen.blit(preview, (SCREEN_WIDTH // 2 - 35, 170))

            name = SHIP_NAMES[self.selected_ship] if self.selected_ship < len(SHIP_NAMES) else ""
            nt = self.font_small.render(name, True, SHIP_COLORS[self.selected_ship % len(SHIP_COLORS)])
            self.screen.blit(nt, (SCREEN_WIDTH // 2 - nt.get_width() // 2, 245))

        items = ["GIOCA", "NAVICELLE", "CREDITI", "ESCI"]
        for i, item in enumerate(items):
            col = YELLOW if i == self.menu_selection else WHITE
            pre = "> " if i == self.menu_selection else "  "
            txt = self.font_medium.render(f"{pre}{item}", True, col)
            self.screen.blit(
                txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 280 + i * 48))

        hint = self.font_tiny.render(
            "W/S per navigare  |  INVIO per confermare", True, (100, 100, 130))
        self.screen.blit(
            hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 495))

        hs = self.font_small.render(
            f"Record: {self.save['high_score']} punti", True, YELLOW)
        self.screen.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 525))

        cr = self.font_tiny.render(
            "Ceccariglia Emanuele & Andrea Cestelli -- ITSUmbria 2026",
            True, (90, 90, 110))
        self.screen.blit(cr, (SCREEN_WIDTH // 2 - cr.get_width() // 2, 565))

    def handle_menu_input(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        n = 4
        if event.key in (pygame.K_UP, pygame.K_w):
            self.menu_selection = (self.menu_selection - 1) % n
            self.sounds["select"].play()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            self.menu_selection = (self.menu_selection + 1) % n
            self.sounds["select"].play()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.sounds["confirm"].play()
            if self.menu_selection == 0:
                self.reset_game()
                self.state = "playing"
                self._start_music()
            elif self.menu_selection == 1:
                self._prev_selected_ship = self.selected_ship
                self._ship_page = 0
                self.state = "ship_select"
            elif self.menu_selection == 2:
                self._credits_scroll = float(SCREEN_HEIGHT)
                self.state = "credits"
            elif self.menu_selection == 3:
                pygame.quit()
                sys.exit()

    # -- CREDITI --

    def draw_credits(self) -> None:
        self.screen.fill(BLACK)
        self.stars.draw(self.screen)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        lines = [
            ("SPACE SHOOTER", self.font_title, CYAN),
            ("Infinite Survival", self.font_medium, WHITE),
            ("", self.font_small, WHITE),
            ("=" * 34, self.font_tiny, (80, 80, 120)),
            ("", self.font_small, WHITE),
            ("SVILUPPATORI", self.font_medium, YELLOW),
            ("Ceccariglia Emanuele", self.font_small, WHITE),
            ("Andrea Cestelli", self.font_small, WHITE),
            ("", self.font_small, WHITE),
            ("CORSO", self.font_medium, YELLOW),
            ("ITSUmbria 2026", self.font_small, WHITE),
            ("", self.font_small, WHITE),
            ("TECNOLOGIE", self.font_medium, YELLOW),
            ("Python 3 / Pygame / Pillow", self.font_small, WHITE),
            ("", self.font_small, WHITE),
            ("CONTROLLI", self.font_medium, YELLOW),
            ("WASD/Frecce = Movimento", self.font_small, WHITE),
            ("SPAZIO = Spara", self.font_small, WHITE),
            ("B = Bomba  |  F = Speciale", self.font_small, WHITE),
            ("ESC/P = Pausa", self.font_small, WHITE),
            ("", self.font_small, WHITE),
            ("Premi ESC per tornare al menu", self.font_small, (150, 150, 180)),
        ]
        y = self._credits_scroll
        for text, font, color in lines:
            s = font.render(text, True, color)
            if -50 < y < SCREEN_HEIGHT + 10:
                self.screen.blit(
                    s, (SCREEN_WIDTH // 2 - s.get_width() // 2, int(y)))
            y += font.size(text)[1] + 6
        self._credits_scroll -= 1.0
        if y < 0:
            self._credits_scroll = float(SCREEN_HEIGHT)

    def handle_credits_input(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN and event.key in (
                pygame.K_ESCAPE, pygame.K_RETURN):
            self.state = "menu"
            self.sounds["select"].play()

    # -- SELEZIONE NAVE --

    def draw_ship_select(self) -> None:
        self.screen.fill(DARK_GRAY)
        self.stars.draw(self.screen)

        title = self.font_large.render("SCEGLI LA TUA NAVE", True, CYAN)
        self.screen.blit(
            title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 12))

        # Mostra tutte e 5 le navi in una riga
        n_cards = NUM_PLAYER_SHIPS
        card_w = 148
        gap = 6
        total_w = n_cards * card_w + (n_cards - 1) * gap
        start_x = (SCREEN_WIDTH - total_w) // 2

        for i in range(n_cards):
            bx = start_x + i * (card_w + gap)
            self._ship_card(bx, i, card_w)

        instr = self.font_small.render(
            "A/D = Scegli  |  INVIO = Conferma  |  ESC = Indietro",
            True, (150, 150, 170))
        self.screen.blit(
            instr, (SCREEN_WIDTH // 2 - instr.get_width() // 2, 555))

    def _ship_card(self, bx: int, ship_idx: int, card_w: int) -> None:
        by, bh = 55, 490

        is_sel      = (ship_idx == self.selected_ship)
        is_unlocked = (ship_idx < len(self.save["unlocked_ships"])
                       and self.save["unlocked_ships"][ship_idx])

        border = YELLOW if is_sel else (80, 80, 100)
        bg     = (30, 30, 50) if is_unlocked else (20, 15, 15)
        pygame.draw.rect(self.screen, bg, (bx, by, card_w, bh))
        pygame.draw.rect(self.screen, border, (bx, by, card_w, bh), 2 if not is_sel else 3)

        # Nome nave
        name = SHIP_NAMES[ship_idx] if ship_idx < len(SHIP_NAMES) else f"Nave {ship_idx}"
        nc = SHIP_COLORS[ship_idx % len(SHIP_COLORS)] if is_unlocked else (100, 100, 100)
        ns = self.font_small.render(name, True, nc)
        self.screen.blit(ns, (bx + card_w // 2 - ns.get_width() // 2, by + 8))

        # Preview nave
        frames = Assets.player_ship_frames
        if ship_idx < len(frames) and frames[ship_idx]:
            preview = pygame.transform.scale(frames[ship_idx][0], (55, 55))
            if not is_unlocked:
                preview.set_alpha(80)
            self.screen.blit(preview, (bx + card_w // 2 - 27, by + 38))
        else:
            pygame.draw.rect(self.screen, (60, 60, 60),
                           (bx + card_w // 2 - 27, by + 38, 55, 55))

        # Descrizione
        desc = SHIP_DESCRIPTIONS[ship_idx] if ship_idx < len(SHIP_DESCRIPTIONS) else ""
        dc = WHITE if is_unlocked else (80, 80, 80)
        ds = self.font_tiny.render(desc, True, dc)
        self.screen.blit(ds, (bx + card_w // 2 - ds.get_width() // 2, by + 100))

        # Tipo cannone
        has_double = ship_idx < len(SHIP_DOUBLE_CANNON) and SHIP_DOUBLE_CANNON[ship_idx]
        shoot_type = "Doppio cannone" if has_double else "Cannone singolo"
        st_col = GOLD if has_double else (150, 150, 180)
        if not is_unlocked:
            st_col = (70, 70, 70)
        st_surf = self.font_tiny.render(shoot_type, True, st_col)
        self.screen.blit(st_surf, (bx + card_w // 2 - st_surf.get_width() // 2, by + 118))

        # Speciale
        if is_unlocked and ship_idx < len(SHIP_STATS):
            special = SHIP_STATS[ship_idx].get("special", "none")
            special_names = {
                "none": "",
                "regen": "Rigenerazione HP",
                "piercing": "Laser perforanti",
                "emp": "EMP (tasto F)",
                "overdrive": "Overdrive (tasto F)",
            }
            sp_name = special_names.get(special, "")
            if sp_name:
                sp_surf = self.font_tiny.render(sp_name, True, MAGENTA)
                self.screen.blit(sp_surf, (bx + card_w // 2 - sp_surf.get_width() // 2, by + 136))

        # Statistiche nave (barre)
        if ship_idx < len(SHIP_STATS):
            stats = SHIP_STATS[ship_idx]
            bar_start_y = by + 158
            stat_items = [
                ("VEL", stats["speed"], 1.5, GREEN),
                ("ROF", 1.0 / stats["fire_rate"], 1.8, CYAN),
                ("DAN", stats["damage"] / 2.0, 1.0, ORANGE),
            ]
            for si, (label, val, max_val, scol) in enumerate(stat_items):
                if not is_unlocked:
                    scol = (60, 60, 60)
                sy = bar_start_y + si * 18
                sl = self.font_tiny.render(label, True, (130, 130, 150) if is_unlocked else (60, 60, 60))
                self.screen.blit(sl, (bx + 6, sy))
                bar_max_w = card_w - 46
                pygame.draw.rect(self.screen, (40, 40, 40),
                                (bx + 34, sy + 3, bar_max_w, 7))
                fill = min(1.0, val / max_val)
                pygame.draw.rect(self.screen, scol,
                                (bx + 34, sy + 3, int(bar_max_w * fill), 7))

        # Stato sblocco
        unlock_score = SHIP_UNLOCK_SCORES[ship_idx] if ship_idx < len(SHIP_UNLOCK_SCORES) else 9999
        if is_unlocked:
            st = self.font_tiny.render("DISPONIBILE", True, GREEN)
        else:
            st = self.font_tiny.render(f"Sblocca: {unlock_score} pt", True, ORANGE)
        self.screen.blit(st, (bx + card_w // 2 - st.get_width() // 2, by + 220))

        if not is_unlocked:
            hs = self.save.get("high_score", 0)
            pct = min(1.0, hs / max(1, unlock_score))
            bar_w = card_w - 16
            bar_x = bx + 8
            bar_y = by + 240
            pygame.draw.rect(self.screen, (40, 40, 40), (bar_x, bar_y, bar_w, 6))
            pygame.draw.rect(self.screen, ORANGE, (bar_x, bar_y, int(bar_w * pct), 6))
            prog_txt = self.font_tiny.render(f"{hs}/{unlock_score}", True, (120, 120, 120))
            self.screen.blit(prog_txt, (bx + card_w // 2 - prog_txt.get_width() // 2, bar_y + 9))

        if is_sel and is_unlocked:
            sel = self.font_tiny.render("SELEZIONATA", True, YELLOW)
            self.screen.blit(
                sel, (bx + card_w // 2 - sel.get_width() // 2, by + bh - 22))

    def handle_ship_select_input(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if event.key in (pygame.K_LEFT, pygame.K_a):
            self.selected_ship = (self.selected_ship - 1) % NUM_PLAYER_SHIPS
            self.sounds["select"].play()
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.selected_ship = (self.selected_ship + 1) % NUM_PLAYER_SHIPS
            self.sounds["select"].play()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if (self.selected_ship < len(self.save["unlocked_ships"])
                    and self.save["unlocked_ships"][self.selected_ship]):
                self.sounds["confirm"].play()
                self._prev_selected_ship = self.selected_ship
                self.state = "menu"
            else:
                self.sounds["game_over"].play()
        elif event.key == pygame.K_ESCAPE:
            self.selected_ship = self._prev_selected_ship
            self.state = "menu"
            self.sounds["select"].play()

    # -- PAUSA --

    def draw_pause_overlay(self) -> None:
        overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        title = self.font_large.render("PAUSA", True, CYAN)
        self.screen.blit(
            title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 170))

        pause_items = ["RIPRENDI", "TORNA AL MENU"]
        for i, txt in enumerate(pause_items):
            is_sel = (i == self._pause_selection)
            col = YELLOW if is_sel else WHITE
            pre = "> " if is_sel else "  "
            s = self.font_medium.render(f"{pre}{txt}", True, col)
            self.screen.blit(
                s, (SCREEN_WIDTH // 2 - s.get_width() // 2, 260 + i * 50))

        secs = self.game_time // 60
        stat = self.font_small.render(
            f"Punti: {self.score}  |  Tempo: {_fmt_time(secs)}  |  "
            f"Livello {self._diff_level + 1}",
            True, YELLOW)
        self.screen.blit(
            stat, (SCREEN_WIDTH // 2 - stat.get_width() // 2, 400))

        # Controlli
        ctrl_lines = [
            "WASD/Frecce = Muovi  |  SPAZIO = Spara",
            "B = Bomba  |  F = Speciale  |  ESC/P = Pausa",
        ]
        for i, line in enumerate(ctrl_lines):
            ct = self.font_tiny.render(line, True, (120, 120, 150))
            self.screen.blit(
                ct, (SCREEN_WIDTH // 2 - ct.get_width() // 2, 440 + i * 22))

    # -- WARNING OVERLAY --

    def _warn_overlay(self, timer: int, dur: int, subtitle: str,
                      color: tuple, extra: str | None = None) -> None:
        flash = int(abs(math.sin(timer * 0.1)) * 80)
        overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        if color == RED:
            c = (flash, 0, 0, 100)
        else:
            c = (flash, int(flash * 0.6), 0, 120)
        overlay.fill(c)
        self.screen.blit(overlay, (0, 0))

        blink = 12 if color == RED else 10
        if (timer // blink) % 2 == 0:
            wt = self.font_large.render("!! ATTENZIONE !!", True, color)
            self.screen.blit(
                wt, (SCREEN_WIDTH // 2 - wt.get_width() // 2,
                     SCREEN_HEIGHT // 2 - 60))

        sub = self.font_medium.render(subtitle, True, color)
        self.screen.blit(
            sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2,
                  SCREEN_HEIGHT // 2 + 10))
        if extra:
            ex = self.font_small.render(extra, True, WHITE)
            self.screen.blit(
                ex, (SCREEN_WIDTH // 2 - ex.get_width() // 2,
                     SCREEN_HEIGHT // 2 + 50))

        prog = timer / dur
        bw, bh = 300, 8
        bx  = SCREEN_WIDTH // 2 - bw // 2
        by2 = SCREEN_HEIGHT // 2 + (85 if extra else 60)
        pygame.draw.rect(self.screen, (60, 60, 60), (bx, by2, bw, bh))
        pygame.draw.rect(self.screen, color, (bx, by2, int(bw * prog), bh))

    # -- DRAW GIOCO --

    def draw_game(self) -> None:
        self.screen.fill(BLACK)

        # Applica offset screen shake
        shake_surf = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        shake_surf.fill(BLACK)
        self.stars.draw(shake_surf)

        for laser in self.player_lasers:
            laser.draw(shake_surf)
        for laser in self.enemy_lasers:
            laser.draw(shake_surf)
        if self.boss_active and self.boss:
            self.boss.draw(shake_surf)
        for group in self.formation_groups:
            group.draw(shake_surf)
        for carrier in self.carriers:
            carrier.draw(shake_surf)
        for pu in self.falling_powerups:
            pu.draw(shake_surf)
        for ast in self.asteroids:
            ast.draw(shake_surf)
        self.player.draw(shake_surf)
        for expl in self.explosions:
            expl.draw(shake_surf)

        # Damage numbers flottanti
        for dn in self._damage_numbers:
            alpha = min(255, dn["timer"] * 6)
            txt = self.font_small.render(dn["text"], True, dn["color"])
            txt.set_alpha(alpha)
            shake_surf.blit(txt, (int(dn["x"]) - txt.get_width() // 2,
                                   int(dn["y"])))

        self.screen.blit(shake_surf,
                         (self._shake_offset_x, self._shake_offset_y))

        # Effetti speciali overlay
        if self._emp_flash > 0:
            emp_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = int(self._emp_flash * 6)
            emp_overlay.fill((0, 200, 255, min(alpha, 80)))
            self.screen.blit(emp_overlay, (0, 0))

        if self._bomb_flash > 0:
            bomb_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            alpha = int(self._bomb_flash * 8)
            bomb_overlay.fill((255, 255, 255, min(alpha, 120)))
            self.screen.blit(bomb_overlay, (0, 0))

        if self.boss_warning:
            self._warn_overlay(
                self.boss_warning_timer, self.boss_warning_dur,
                "BOSS IN ARRIVO", RED)
        if self.rain_warning:
            self._warn_overlay(
                self.rain_w_timer, self.rain_w_dur,
                "PIOGGIA DI ASTEROIDI", ORANGE, "Sopravvivi!")

        if self.boss_active and self.boss and self.boss.alive:
            self.boss.draw_health_bar(self.screen)

        self._draw_hud()

        # Grace period countdown
        if self._grace_active:
            self._draw_grace_countdown()

        if self._paused:
            self.draw_pause_overlay()

    def _draw_hud(self) -> None:
        hud_y = 38 if (self.boss_active and self.boss
                       and self.boss.alive) else 10

        # Punteggio
        sc = self.font_hud.render(f"Punti: {self.score}", True, WHITE)
        self.screen.blit(sc, (16, hud_y + 4))

        # Vite
        self._draw_lives(hud_y)

        # Tempo
        secs = self.game_time // 60
        tt = self.font_small.render(
            f"Tempo: {_fmt_time(secs)}", True, (180, 180, 200))
        self.screen.blit(tt, (SCREEN_WIDTH - 145, hud_y + 6))

        # Livello
        dlvl = self.font_tiny.render(
            f"Livello {self._diff_level + 1}", True, (120, 200, 120))
        self.screen.blit(dlvl, (SCREEN_WIDTH - 80, hud_y + 30))

        # Stato attuale (pioggia, boss, nemici)
        if self.rain_active or self.rain_draining:
            col = ORANGE if (self.game_time // 20) % 2 == 0 else YELLOW
            label = ("PIOGGIA DI ASTEROIDI" if self.rain_active
                     else "ASTEROIDI IN VOLO...")
            ri = self.font_tiny.render(f"* {label}", True, col)
            self.screen.blit(
                ri, (SCREEN_WIDTH // 2 - ri.get_width() // 2, hud_y + 30))
        elif self.boss_active:
            bi = self.font_tiny.render(
                f"BOSS FIGHT!  (sconfitti: {self.boss_defeated_count})",
                True, RED)
            self.screen.blit(bi, (SCREEN_WIDTH - 300, hud_y + 30))
        else:
            alive = self._total_alive()
            fg = self.font_tiny.render(
                f"Nemici: {alive}  |  Gruppi: {len(self.formation_groups)}",
                True, (180, 100, 100))
            self.screen.blit(fg, (SCREEN_WIDTH - 240, hud_y + 30))

        # Barra cooldown sparo
        ticks = pygame.time.get_ticks()
        cooldown = self.player.shot_cooldown
        if self.player.overdrive_active:
            cooldown = cooldown // 2
        cd = max(0, cooldown - (ticks - self.player.last_shot_time))
        if cd > 0:
            pct = cd / cooldown
            pygame.draw.rect(
                self.screen, (60, 60, 60), (16, hud_y + 38, 60, 5))
            pygame.draw.rect(
                self.screen, CYAN, (16, hud_y + 38, int(60 * (1 - pct)), 5))

        # Hint controlli in basso
        hints = ["ESC = Pausa"]
        if self.player.bombs > 0:
            hints.append(f"B = Bomba ({self.player.bombs})")
        if self.player.special in ("emp", "overdrive"):
            key_hint = "F = Speciale"
            if self.player.special == "emp" and self.player.emp_ready:
                key_hint = "F = EMP (pronto!)"
            elif self.player.special == "overdrive" and not self.player.overdrive_active and self.player.overdrive_cooldown <= 0:
                key_hint = "F = Overdrive (pronto!)"
            hints.append(key_hint)

        ph = self.font_tiny.render("  |  ".join(hints), True, (80, 80, 105))
        self.screen.blit(
            ph, (SCREEN_WIDTH // 2 - ph.get_width() // 2,
                 SCREEN_HEIGHT - 18))

        self._draw_pu_hud(hud_y)
        self._draw_combo_hud(hud_y)

    def _draw_pu_hud(self, hud_y: int) -> None:
        active: list[tuple[str, tuple, float, float]] = []
        if self.player.shield_active:
            active.append((
                "SCUDO", CYAN,
                self.player.shield_timer / 60,
                self.player.shield_timer / self.player.shield_duration))
        if self.player.speed_boost_active:
            active.append((
                "VELOCITA'", YELLOW,
                self.player.speed_boost_timer / 60,
                self.player.speed_boost_timer / self.player.speed_boost_duration))
        if self.player.triple_shot_active:
            active.append((
                "ARMA x3", ORANGE,
                self.player.triple_shot_timer / 60,
                self.player.triple_shot_timer / self.player.triple_shot_duration))
        if self.player.overdrive_active:
            active.append((
                "OVERDRIVE", GOLD,
                self.player.overdrive_timer / 60,
                self.player.overdrive_timer / self.player.overdrive_duration))
        if not active:
            return

        py = hud_y + 50
        for name, col, secs_left, pct in active:
            lbl = self.font_tiny.render(f"{name} {secs_left:.1f}s", True, col)
            self.screen.blit(lbl, (14, py))
            pygame.draw.rect(
                self.screen, (40, 40, 40), (10, py + 16, 120, 3))
            pygame.draw.rect(
                self.screen, col, (10, py + 16, int(120 * pct), 3))
            py += 20

    def _draw_combo_hud(self, hud_y: int) -> None:
        if self._combo_count >= 3 and self._combo_display > 0:
            alpha = min(255, self._combo_display * 5)
            combo_text = f"COMBO x{self._combo_count}"
            if self._combo_mult > 0:
                combo_text += f"  (+{int(self._combo_mult * 100)}%)"
            col = ORANGE if self._combo_count >= 10 else YELLOW
            if self._combo_count >= 15:
                col = RED
            ct = self.font_medium.render(combo_text, True, col)
            ct.set_alpha(alpha)
            self.screen.blit(
                ct, (SCREEN_WIDTH // 2 - ct.get_width() // 2, hud_y + 50))

        kt = self.font_tiny.render(
            f"Uccisioni: {self._total_kills}", True, (120, 120, 150))
        self.screen.blit(kt, (16, SCREEN_HEIGHT - 34))

    def _draw_grace_countdown(self) -> None:
        overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        seconds_left = (self._grace_timer // 60) + 1
        count_text = str(seconds_left) if seconds_left > 0 else "VIA!"

        pulse = 1.0 + 0.2 * abs(math.sin(self._grace_timer * 0.15))
        font_size = int(90 * pulse)
        big_font = pygame.font.Font(None, font_size)
        ct = big_font.render(count_text, True, CYAN)
        self.screen.blit(
            ct, (SCREEN_WIDTH // 2 - ct.get_width() // 2,
                 SCREEN_HEIGHT // 2 - ct.get_height() // 2 - 30))

        hint = self.font_medium.render("Preparati!", True, WHITE)
        self.screen.blit(
            hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2,
                   SCREEN_HEIGHT // 2 + 50))

        # Mostra controlli
        ctrl = self.font_small.render(
            "WASD = Muovi  |  SPAZIO = Spara  |  B = Bomba  |  F = Speciale",
            True, (150, 150, 180))
        self.screen.blit(
            ctrl, (SCREEN_WIDTH // 2 - ctrl.get_width() // 2,
                   SCREEN_HEIGHT // 2 + 90))

    def _draw_lives(self, hud_y: int) -> None:
        sz, sp = 18, 24
        sx, sy = 200, hud_y + 8
        for i in range(Player.MAX_LIVES):
            col = RED if i < self.player.lives else (60, 60, 60)
            self._heart(self.screen, sx + i * sp, sy, sz, col)

    @staticmethod
    def _heart(surf: pygame.Surface, x: int, y: int, sz: int,
               col: tuple) -> None:
        r = sz // 4
        pygame.draw.circle(surf, col, (x + r, y + r), r)
        pygame.draw.circle(surf, col, (x + sz // 2 + r, y + r), r)
        pygame.draw.polygon(
            surf, col, [(x, y + r), (x + sz, y + r), (x + sz // 2, y + sz)])

    # -- INPUT IN-GAME --

    def handle_game_input(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return

        if self._paused:
            if event.key in (pygame.K_UP, pygame.K_w):
                self._pause_selection = (self._pause_selection - 1) % 2
                self.sounds["select"].play()
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                self._pause_selection = (self._pause_selection + 1) % 2
                self.sounds["select"].play()
            elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.sounds["confirm"].play()
                if self._pause_selection == 0:
                    self._resume_from_pause()
                elif self._pause_selection == 1:
                    self._quit_to_menu_from_pause()
            elif event.key in (pygame.K_ESCAPE, pygame.K_p):
                self._resume_from_pause()
        else:
            if event.key in (pygame.K_ESCAPE, pygame.K_p):
                self._toggle_pause()
            elif event.key == pygame.K_b:
                self._use_bomb()
            elif event.key == pygame.K_f:
                if self.player.special == "emp":
                    self._use_emp()
                elif self.player.special == "overdrive":
                    self._use_overdrive()

    # -- GAME OVER --

    def draw_game_over(self) -> None:
        self.screen.fill(BLACK)
        self.stars.draw(self.screen)
        overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        go = self.font_title.render("GAME OVER", True, RED)
        self.screen.blit(go, (SCREEN_WIDTH // 2 - go.get_width() // 2, 80))

        sc = self.font_large.render(
            f"Punteggio: {self.score}", True, WHITE)
        self.screen.blit(sc, (SCREEN_WIDTH // 2 - sc.get_width() // 2, 165))

        is_new = (self.score >= self.save["high_score"] and self.score > 0)
        rp  = "NUOVO RECORD!  " if is_new else "Record: "
        rec = self.font_medium.render(
            f"{rp}{self.save['high_score']}",
            True, YELLOW if is_new else (180, 180, 200))
        self.screen.blit(rec, (SCREEN_WIDTH // 2 - rec.get_width() // 2, 220))

        secs = self.game_time // 60
        tt = self.font_small.render(
            f"Sopravvissuto: {_fmt_time(secs)}  |  Livello {self._diff_level + 1}"
            f"  |  Uccisioni: {self._total_kills}  |  Boss: {self.boss_defeated_count}",
            True, (180, 180, 200))
        self.screen.blit(tt, (SCREEN_WIDTH // 2 - tt.get_width() // 2, 260))

        if self._combo_best >= 3:
            cb = self.font_small.render(
                f"Miglior Combo: x{self._combo_best}", True, ORANGE)
            self.screen.blit(
                cb, (SCREEN_WIDTH // 2 - cb.get_width() // 2, 288))

        y_offset = 320
        if self._newly_unlocked:
            for idx in self._newly_unlocked:
                name = SHIP_NAMES[idx] if idx < len(SHIP_NAMES) else f"Nave {idx}"
                ul = self.font_medium.render(
                    f"NAVE {name.upper()} SBLOCCATA!", True, MAGENTA)
                self.screen.blit(
                    ul, (SCREEN_WIDTH // 2 - ul.get_width() // 2, y_offset))
                y_offset += 32

        r1 = self.font_small.render("INVIO = Rigioca", True, GREEN)
        r2 = self.font_small.render("ESC = Menu principale", True, (150, 150, 170))
        self.screen.blit(r1, (SCREEN_WIDTH // 2 - r1.get_width() // 2, y_offset + 15))
        self.screen.blit(r2, (SCREEN_WIDTH // 2 - r2.get_width() // 2, y_offset + 42))

        if self.save["best_scores"]:
            top_y = y_offset + 80
            top = self.font_small.render("Migliori punteggi:", True, YELLOW)
            self.screen.blit(
                top, (SCREEN_WIDTH // 2 - top.get_width() // 2, top_y))
            for i, s in enumerate(self.save["best_scores"][:5]):
                st = self.font_tiny.render(
                    f"{i + 1}. {s} punti", True, (180, 180, 200))
                self.screen.blit(
                    st, (SCREEN_WIDTH // 2 - st.get_width() // 2,
                         top_y + 25 + i * 20))

    def handle_game_over_input(self, event: pygame.event.Event) -> None:
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_RETURN, pygame.K_SPACE):
            self.sounds["confirm"].play()
            self.reset_game()
            self.state = "playing"
            self._start_music()
        elif event.key == pygame.K_ESCAPE:
            self.sounds["select"].play()
            self.state = "menu"

    # ======================================================================
    # GAME LOOP
    # ======================================================================

    def run(self) -> None:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if self.state == "menu":
                    self.handle_menu_input(event)
                elif self.state == "ship_select":
                    self.handle_ship_select_input(event)
                elif self.state == "playing":
                    self.handle_game_input(event)
                elif self.state == "game_over":
                    self.handle_game_over_input(event)
                elif self.state == "credits":
                    self.handle_credits_input(event)

            self.stars.update()

            if self.state == "playing":
                self.update_game()

            if self.state == "menu":
                self.draw_menu()
            elif self.state == "ship_select":
                self.draw_ship_select()
            elif self.state == "playing":
                self.draw_game()
            elif self.state == "game_over":
                self.draw_game_over()
            elif self.state == "credits":
                self.draw_credits()

            pygame.display.flip()
            self.clock.tick(FPS)
