"""Space Shooter -- Infinite Survival  |  game.py v6 (gameVariant PRD)
Autori: Ceccariglia Emanuele & Andrea Cestelli -- ITSUmbria 2026

Game loop principale, gestione stati, spawn, collisioni, HUD e pause.
Aggiornato con: 10 navicelle, 4 boss varianti, 7 livelli arma,
formazioni PRD (Grid, V, Swarm, Double-V, Dive), drop rate per tipo nemico.
"""
import math, random, sys
import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    BLACK, WHITE, RED, GREEN, YELLOW, CYAN, MAGENTA, ORANGE,
    DARK_GRAY, POWERUP_ITEM_SIZE,
    DIFFICULTY_INTERVAL, DIFFICULTY_SPEED_SCALE, DIFFICULTY_MAX_LEVEL,
    NUM_SHIPS, VIP_SHIP_INDEX, SHIP_NAMES, SHIP_DESCS, SHIP_COLORS,
    NUM_BOSS_VARIANTS,
)
from core.assets import Assets
from core.sounds import create_sounds, generate_background_music
from core.save_manager import load_save_data, save_data

from entities.player import Player
from entities.boss import Boss
from entities.laser import Laser
from entities.explosion import Explosion
from entities.powerup import PowerUpCarrier, FallingPowerUp
from entities.asteroid import Asteroid, clear_registry
from entities.formations import pick_formation, build_spawn_positions
from entities.formation_group import FormationGroup

from world.starfield import StarField

# ---------------------------------------------------------------------------
_MIN_GROUP_V_GAP = 140  # pixel

# Sblocco navicelle per punteggio
_SHIP_UNLOCK_SCORES = [0, 0, 30, 50, 80, 120, 170, 230, 300, 500]


class Game:
    """Classe principale del gioco: gestisce game loop, stati e rendering."""

    # ======================================================================
    # INIT
    # ======================================================================

    def __init__(self):
        """Inizializza schermo, asset, suoni, font e stato iniziale."""
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space InvaderX - gameVariant")
        self.clock = pygame.time.Clock()

        # Carica sprite e risorse grafiche
        Assets.load()

        # Genera effetti sonori e musica procedurale
        self.sounds   = create_sounds()
        self.bg_music = generate_background_music(duration_ms=8000, volume=0.12)
        self.stars    = StarField()
        self.save     = load_save_data()

        # Font per testo UI
        self.font_large  = pygame.font.Font(None, 64)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small  = pygame.font.Font(None, 28)
        self.font_tiny   = pygame.font.Font(None, 22)

        # Stato corrente della macchina a stati
        self.state          = "menu"
        self.selected_ship  = 0
        self.menu_selection = 0
        self._music_channel = None
        self._credits_scroll = float(SCREEN_HEIGHT)

        # Pausa: selezione voce nel menu di pausa (0 = Riprendi, 1 = Menu)
        self._pause_selection = 0

        # Ship select: scroll per pagina
        self._ship_sel_page = 0

        # Powerup popup messages
        self._pu_popups = []  # list of (text, color, timer)

        self.reset_game()

    # ======================================================================
    # MUSICA
    # ======================================================================

    def _start_music(self):
        if self._music_channel is None or not self._music_channel.get_busy():
            self._music_channel = self.bg_music.play(loops=-1)

    def _stop_music(self):
        if self._music_channel:
            self._music_channel.stop()

    # ======================================================================
    # RESET
    # ======================================================================

    def reset_game(self):
        """Resetta completamente lo stato di gioco per una nuova partita."""
        clear_registry()

        self.player            = Player(self.selected_ship)
        self.formation_groups: list[FormationGroup] = []
        self.player_lasers:    list[Laser]     = []
        self.enemy_lasers:     list[Laser]     = []
        self.explosions:       list[Explosion]  = []
        self.score = 0
        self.game_time = 0

        # Timer e intervallo spawn formazioni nemiche
        self.spawn_timer    = 0
        self.spawn_interval = random.randint(120, 300)

        # Boss
        self.boss = None
        self.boss_active       = False
        self.boss_warning      = False
        self.boss_warning_timer = 0
        self.boss_warning_dur  = 180
        self.boss_defeated_count = 0
        self.next_boss_time    = random.randint(35 * 60, 65 * 60)
        self.boss_cooldown     = 0

        # Carrier power-up
        self.carriers:         list[PowerUpCarrier] = []
        self.falling_powerups: list[FallingPowerUp] = []
        self.carrier_timer    = 0
        self.carrier_interval = random.randint(12 * 60, 28 * 60)

        # Asteroidi singoli
        self.asteroids:        list[Asteroid] = []
        self.asteroid_timer    = 0
        self.asteroid_interval = random.randint(10 * 60, 22 * 60)

        # ---- Pioggia di asteroidi ----
        self.rain_active    = False
        self.rain_warning   = False
        self.rain_w_timer   = 0
        self.rain_w_dur     = 180
        self.rain_timer     = 0
        self.rain_dur       = 0
        self.rain_spawn_t   = 0
        self.rain_spawn_i   = 35
        self.next_rain      = random.randint(50 * 60, 100 * 60)
        self.rain_cooldown  = 0
        self.rain_max       = 0
        self.rain_draining  = False

        # Difficolta' progressiva
        self._diff_level  = 0
        self._next_diff   = DIFFICULTY_INTERVAL * 60

        # Pausa
        self._paused          = False
        self._pause_selection = 0

        # Wave counter (PRD)
        self._wave_num = 1
        self._formations_spawned = 0

        # Powerup popups
        self._pu_popups = []

    # ======================================================================
    # DIFFICOLTA'
    # ======================================================================

    def _speed_mult(self) -> float:
        return DIFFICULTY_SPEED_SCALE ** self._diff_level

    def _update_diff(self):
        if self._diff_level >= DIFFICULTY_MAX_LEVEL:
            return
        if self.game_time >= self._next_diff:
            self._diff_level += 1
            self._wave_num = min(9, self._diff_level + 1)
            self._next_diff += DIFFICULTY_INTERVAL * 60

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

    def _spawn_formation(self):
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
        data = build_spawn_positions(slots, self.formation_groups)
        group = FormationGroup(data, self._speed_mult(), name, self._diff_level)
        self.formation_groups.append(group)
        self._formations_spawned += 1

    def _spawn_carriers(self):
        self.carrier_timer += 1
        if self.carrier_timer >= self.carrier_interval:
            self.carrier_timer = 0
            self.carrier_interval = random.randint(12 * 60, 28 * 60)
            if len(self.carriers) < 2:
                self.carriers.append(PowerUpCarrier())

    def _spawn_asteroids(self):
        if self.rain_active or self.rain_warning or self.rain_draining:
            return
        self.asteroid_timer += 1
        if self.asteroid_timer >= self.asteroid_interval:
            self.asteroid_timer = 0
            self.asteroid_interval = random.randint(10 * 60, 22 * 60)
            if len(self.asteroids) < 2:
                self.asteroids.append(Asteroid())
                self.sounds["asteroid_warning"].play()

    # ======================================================================
    # EVENTI SPECIALI: BOSS
    # ======================================================================

    def _check_boss(self):
        if self.boss_active or self.boss_warning:
            return
        if self.rain_active or self.rain_warning or self.rain_draining:
            return
        if self.boss_cooldown > 0:
            self.boss_cooldown -= 1
            return
        if self.game_time >= self.next_boss_time:
            self.boss_warning = True
            self.boss_warning_timer = 0
            self.sounds["boss_warning"].play()

    def _do_spawn_boss(self):
        """Spawna il boss dopo il warning -- sceglie variante progressiva."""
        # Variante: ciclica tra le 4 varianti
        variant = self.boss_defeated_count % NUM_BOSS_VARIANTS
        self.boss = Boss(variant=variant)
        self.boss_active = True
        self.boss_warning = False

        # Scala HP, velocita' e intervallo sparo
        bonus = self.boss_defeated_count * 10
        self.boss.max_hp = 60 + bonus
        self.boss.hp     = self.boss.max_hp
        self.boss.h_speed = 2.0 + self.boss_defeated_count * 0.3
        self.boss.shoot_interval = max(22, 55 - self.boss_defeated_count * 4)

        # Boss piu' grandi per varianti non-gif
        if variant > 0:
            self.boss.width = 180
            self.boss.height = 140

        self.formation_groups.clear()
        self.enemy_lasers.clear()

    def _on_boss_defeated(self):
        cx = self.boss.x + self.boss.width // 2
        cy = self.boss.y + self.boss.height // 2
        self.explosions.append(Explosion(cx, cy, size=128))
        for _ in range(5):
            self.explosions.append(Explosion(
                self.boss.x + random.randint(0, self.boss.width),
                self.boss.y + random.randint(0, self.boss.height)))
        self.sounds["boss_defeated"].play()

        self.score += 20 + self.boss_defeated_count * 5
        self.boss_defeated_count += 1
        self.boss_active = False
        self.boss = None

        self.boss_cooldown = random.randint(18 * 60, 38 * 60)
        self.next_boss_time = self.game_time + random.randint(30 * 60, 60 * 60)
        self.enemy_lasers.clear()

    # ======================================================================
    # EVENTI SPECIALI: PIOGGIA DI ASTEROIDI
    # ======================================================================

    def _check_rain(self):
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

    def _start_rain(self):
        self.rain_active  = True
        self.rain_warning = False
        self.rain_draining = False

        base_dur = 8 * 60 + self._diff_level * 60
        self.rain_dur = min(base_dur, 16 * 60)
        self.rain_timer = 0
        self.rain_spawn_t = 0
        self.rain_spawn_i = max(22, 45 - self._diff_level * 3)
        self.rain_max = 4 + self._diff_level

        self.formation_groups.clear()
        self.enemy_lasers.clear()
        for a in self.asteroids:
            a.deactivate()
        self.asteroids.clear()
        clear_registry()

    def _end_rain(self):
        self.rain_active = False
        self.rain_draining = True

    def _finish_rain_drain(self):
        self.rain_draining = False
        self.rain_cooldown = random.randint(45 * 60, 90 * 60)
        self.next_rain = self.game_time + random.randint(50 * 60, 100 * 60)
        clear_registry()

    # ======================================================================
    # UPDATE GAMEPLAY
    # ======================================================================

    def update_game(self):
        if self._paused:
            return

        self.game_time += 1
        self._update_diff()
        keys = pygame.key.get_pressed()

        # Update popups
        self._pu_popups = [(t, c, tmr - 1) for t, c, tmr in self._pu_popups if tmr > 0]

        if self.boss_warning:
            self._upd_boss_warning(keys)
            return
        if self.rain_warning:
            self._upd_rain_warning(keys)
            return
        if self.rain_active:
            self._upd_rain(keys)
            return
        if self.rain_draining:
            self._upd_rain_drain(keys)
            return
        self._upd_normal(keys)

    def _upd_boss_warning(self, keys):
        self.boss_warning_timer += 1
        if self.boss_warning_timer >= self.boss_warning_dur:
            self._do_spawn_boss()
        self.player.update(keys)
        self._upd_explosions()
        self._upd_asteroids()

    def _upd_rain_warning(self, keys):
        self.rain_w_timer += 1
        if self.rain_w_timer >= self.rain_w_dur:
            self._start_rain()
        self.player.update(keys)
        self._upd_explosions()

    def _upd_rain(self, keys):
        self.rain_timer += 1
        if self.rain_timer >= self.rain_dur:
            self._end_rain()
        else:
            self.rain_spawn_t += 1
            if (self.rain_spawn_t >= self.rain_spawn_i
                    and len(self.asteroids) < self.rain_max):
                self.rain_spawn_t = 0
                self.asteroids.append(Asteroid())

        self.player.update(keys)
        self._shoot(keys)
        self._upd_all_entities()

        pr = self.player.get_rect()
        self._chk_asteroid_player(pr)
        self._chk_pu_player(pr)
        self._cleanup()
        if not self.player.alive:
            self._game_over()

    def _upd_rain_drain(self, keys):
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

    def _upd_normal(self, keys):
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

        # Update formazioni nemiche
        hit_bottom = False
        for g in self.formation_groups:
            fell = g.update()
            if fell:
                hit_bottom = True
            for laser in g.pending_lasers:
                self.enemy_lasers.append(laser)
                self.sounds["enemy_laser"].play()
            # Raccogli power-up droppati dai nemici uccisi
            for pu in g.pending_powerups:
                self.falling_powerups.append(pu)

        if hit_bottom:
            dead = self.player.take_damage()
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

    # ---- Utilita' di update ----

    def _shoot(self, keys):
        if keys[pygame.K_SPACE]:
            lasers = self.player.shoot(pygame.time.get_ticks())
            if lasers:
                self.player_lasers.extend(lasers)
                self.sounds["laser"].play()

    def _upd_all_entities(self):
        for l in self.player_lasers:
            l.update()
        for l in self.enemy_lasers:
            l.update()
        for e in self.explosions:
            e.update()
        for c in self.carriers:
            c.update()
        for p in self.falling_powerups:
            p.update()
        for a in self.asteroids:
            a.update()

    def _upd_explosions(self):
        for e in self.explosions:
            e.update()
        self.explosions = [e for e in self.explosions if e.active]

    def _upd_asteroids(self):
        for a in self.asteroids:
            a.update()
        self.asteroids = [a for a in self.asteroids if a.active]

    def _cleanup(self):
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

    def _check_all(self):
        pr = self.player.get_rect()
        self._chk_pl_vs_boss()
        self._chk_pl_vs_carrier()
        self._chk_pl_vs_formations()
        self._chk_el_vs_player(pr)
        self._chk_boss_vs_player(pr)
        self._chk_formation_vs_player(pr)
        self._chk_asteroid_player(pr)
        self._chk_pu_player(pr)

    def _chk_pl_vs_boss(self):
        if not (self.boss_active and self.boss and self.boss.alive):
            return
        for l in self.player_lasers:
            if not l.active or not self.boss:
                break
            if l.get_rect().colliderect(self.boss.get_rect()):
                l.active = False
                self.sounds["boss_hit"].play()
                self.explosions.append(Explosion(l.x + 2, l.y))
                if self.boss.take_damage(1):
                    self._on_boss_defeated()
                    break

    def _chk_pl_vs_carrier(self):
        for l in self.player_lasers:
            if not l.active:
                continue
            for c in self.carriers:
                if not c.alive:
                    continue
                if l.get_rect().colliderect(c.get_rect()):
                    l.active = False
                    if c.take_damage(1):
                        self.explosions.append(Explosion(
                            c.x + c.width // 2,
                            c.y + c.height // 2))
                        self.sounds["carrier_destroyed"].play()
                        self.falling_powerups.append(FallingPowerUp(
                            c.x + c.width // 2 - POWERUP_ITEM_SIZE // 2,
                            c.y + c.height // 2 - POWERUP_ITEM_SIZE // 2,
                            c.powerup_type))
                    else:
                        self.sounds["carrier_hit"].play()
                    break

    def _chk_pl_vs_formations(self):
        """Collisione: laser del giocatore -> nemici nelle formazioni.

        PRD: alla morte di un nemico, la formazione calcola il drop power-up.
        """
        for l in self.player_lasers:
            if not l.active:
                continue
            hit = False
            for g in self.formation_groups:
                for rect, enemy in g.get_alive_rects():
                    if l.get_rect().colliderect(rect):
                        l.active = False
                        dead = enemy.take_damage(1)
                        if dead:
                            self.score += g.score_per_kill
                            self.explosions.append(Explosion(
                                enemy.x + enemy.width // 2,
                                enemy.y + enemy.height // 2))
                            self.sounds["explosion"].play()
                            # PRD: power-up drop basato su tipo nemico
                            g.on_enemy_killed(enemy)
                            for pu in g.pending_powerups:
                                self.falling_powerups.append(pu)
                            g.pending_powerups.clear()
                        else:
                            self.sounds["boss_hit"].play()
                        hit = True
                        break
                if hit:
                    break

    def _chk_el_vs_player(self, pr):
        for l in self.enemy_lasers:
            if not l.active:
                continue
            if l.get_rect().colliderect(pr):
                l.active = False
                if self.player.shield_active:
                    self.sounds["shield_active"].play()
                elif not self.player.invincible:
                    dead = self.player.take_damage()
                    if dead:
                        self._player_death_expl()
                    else:
                        self.sounds["player_hit"].play()

    def _chk_boss_vs_player(self, pr):
        if not (self.boss_active and self.boss and self.boss.alive):
            return
        if self.boss.get_rect().colliderect(pr):
            if self.player.shield_active:
                pass
            elif not self.player.invincible:
                self.player.lives = 0
                self.player.alive = False
                self._player_death_expl()

    def _chk_formation_vs_player(self, pr):
        for g in self.formation_groups:
            for rect, enemy in g.get_alive_rects():
                if rect.colliderect(pr):
                    enemy.alive = False
                    self.explosions.append(Explosion(
                        enemy.x + enemy.width // 2,
                        enemy.y + enemy.height // 2))
                    if self.player.shield_active:
                        self.sounds["shield_active"].play()
                    elif not self.player.invincible:
                        dead = self.player.take_damage()
                        if dead:
                            self._player_death_expl()
                        else:
                            self.sounds["player_hit"].play()

    def _chk_asteroid_player(self, pr):
        for a in self.asteroids:
            if not a.active:
                continue
            if a.get_rect().colliderect(pr):
                self.player.shield_active = False
                self.player.shield_timer = 0
                self.player.invincible = False
                self.player.lives = 0
                self.player.alive = False
                self.explosions.append(Explosion(
                    self.player.x + self.player.width // 2,
                    self.player.y + self.player.height // 2,
                    size=128))
                self.sounds["game_over"].play()
                return

    def _chk_pu_player(self, pr):
        for p in self.falling_powerups:
            if not p.active:
                continue
            if p.get_rect().colliderect(pr):
                p.active = False
                self.player.apply_powerup(p.powerup_type)
                self.sounds["powerup_collect"].play()
                if p.powerup_type == "scudo":
                    self.sounds["shield_active"].play()
                # PRD: popup 1.5s
                name_map = {"vita": "+VITA", "scudo": "+SHIELD", "velocita": "+SPEED", "arma": "+WEAPON"}
                from core.constants import POWERUP_COLORS
                self._pu_popups.append((
                    name_map.get(p.powerup_type, "+???"),
                    POWERUP_COLORS.get(p.powerup_type, WHITE),
                    90))  # 1.5s at 60fps

    def _player_death_expl(self):
        self.explosions.append(Explosion(
            self.player.x + self.player.width // 2,
            self.player.y + self.player.height // 2))
        self.sounds["game_over"].play()

    # ======================================================================
    # GAME OVER
    # ======================================================================

    def _game_over(self):
        self._stop_music()

        if self.score > self.save["high_score"]:
            self.save["high_score"] = self.score

        # Sblocca navi basandosi sul punteggio
        for i, threshold in enumerate(_SHIP_UNLOCK_SCORES):
            if i < NUM_SHIPS and self.score >= threshold:
                if not self.save["unlocked_ships"][i]:
                    self.save["unlocked_ships"][i] = True
                    self.sounds["unlock"].play()

        self.save["best_scores"].append(self.score)
        self.save["best_scores"].sort(reverse=True)
        self.save["best_scores"] = self.save["best_scores"][:10]
        save_data(self.save)

        self.state = "game_over"

    # ======================================================================
    # PAUSA (ESC o P)
    # ======================================================================

    def _toggle_pause(self):
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

    def _resume_from_pause(self):
        self._paused = False
        self._pause_selection = 0
        self.sounds["resume"].play()
        if self._music_channel:
            self._music_channel.unpause()

    def _quit_to_menu_from_pause(self):
        self._paused = False
        self._pause_selection = 0
        self._stop_music()
        self.state = "menu"
        self.sounds["select"].play()

    # ======================================================================
    #  DRAW
    # ======================================================================

    # ---- MENU PRINCIPALE ----

    def draw_menu(self):
        self.screen.fill(DARK_GRAY)
        self.stars.draw(self.screen)

        t1 = self.font_large.render("SPACE INVADERX", True, CYAN)
        t2 = self.font_medium.render("gameVariant", True, WHITE)
        self.screen.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 70))
        self.screen.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 140))

        # Anteprima nave selezionata
        scaled = pygame.transform.scale(
            Assets.player_ships[self.selected_ship], (60, 60))
        self.screen.blit(scaled, (SCREEN_WIDTH // 2 - 30, 185))

        items = ["GIOCA", "NAVICELLE", "CREDITI", "ESCI"]
        for i, item in enumerate(items):
            col = YELLOW if i == self.menu_selection else WHITE
            pre = "> " if i == self.menu_selection else "  "
            t = self.font_medium.render(f"{pre}{item}", True, col)
            self.screen.blit(t, (SCREEN_WIDTH // 2 - t.get_width() // 2, 275 + i * 48))

        hint = self.font_tiny.render(
            "W/S naviga  |  INVIO/SPAZIO conferma", True, (100, 100, 130))
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 500))

        hs = self.font_small.render(
            f"Record: {self.save['high_score']} punti", True, YELLOW)
        self.screen.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 530))

        cr = self.font_tiny.render(
            "Ceccariglia Emanuele & Andrea Cestelli -- ITSUmbria 2026",
            True, (90, 90, 110))
        self.screen.blit(cr, (SCREEN_WIDTH // 2 - cr.get_width() // 2, 565))

    def handle_menu_input(self, event):
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
                self.state = "ship_select"
            elif self.menu_selection == 2:
                self._credits_scroll = float(SCREEN_HEIGHT)
                self.state = "credits"
            elif self.menu_selection == 3:
                pygame.quit()
                sys.exit()

    # ---- CREDITI ----

    def draw_credits(self):
        self.screen.fill(BLACK)
        self.stars.draw(self.screen)
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 120))
        self.screen.blit(ov, (0, 0))

        lines = [
            ("SPACE INVADERX", self.font_large, CYAN),
            ("gameVariant", self.font_medium, WHITE),
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
            ("Python 3 / Pygame-CE / Pillow", self.font_small, WHITE),
            ("", self.font_small, WHITE),
            ("Ispirato a Star Defender 4", self.font_small, ORANGE),
            ("", self.font_small, WHITE),
            ("Premi ESC per tornare al menu", self.font_small, (150, 150, 180)),
        ]
        y = self._credits_scroll
        for text, font, color in lines:
            s = font.render(text, True, color)
            if -50 < y < SCREEN_HEIGHT + 10:
                self.screen.blit(s, (SCREEN_WIDTH // 2 - s.get_width() // 2, int(y)))
            y += font.size(text)[1] + 6
        self._credits_scroll -= 1.0
        if y < 0:
            self._credits_scroll = float(SCREEN_HEIGHT)

    def handle_credits_input(self, event):
        if event.type == pygame.KEYDOWN:
            self.state = "menu"
            self.sounds["select"].play()

    # ---- SELEZIONE NAVE (10 navi in griglia 5x2) ----

    def draw_ship_select(self):
        """Disegna la schermata di selezione navicella -- griglia 5x2 per 10 navi."""
        self.screen.fill(DARK_GRAY)
        self.stars.draw(self.screen)
        title = self.font_large.render("NAVICELLE", True, CYAN)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 10))

        # Griglia 5 colonne x 2 righe
        cols, rows = 5, 2
        card_w, card_h = 140, 230
        gap_x, gap_y = 12, 12
        grid_w = cols * card_w + (cols - 1) * gap_x
        start_x = (SCREEN_WIDTH - grid_w) // 2
        start_y = 70

        for idx in range(NUM_SHIPS):
            row = idx // cols
            col = idx % cols
            bx = start_x + col * (card_w + gap_x)
            by = start_y + row * (card_h + gap_y)
            self._ship_card_grid(idx, bx, by, card_w, card_h)

        instr = self.font_small.render(
            "< A/D/W/S scegli | INVIO conferma | ESC indietro >",
            True, (150, 150, 170))
        self.screen.blit(instr, (SCREEN_WIDTH // 2 - instr.get_width() // 2, 560))

    def _ship_card_grid(self, index, bx, by, bw, bh):
        """Disegna una card di navicella nella griglia."""
        is_sel = (index == self.selected_ship)
        is_unlocked = self.save["unlocked_ships"][index]
        is_vip = (index == VIP_SHIP_INDEX)

        # Sfondo card
        if is_vip:
            bg = (40, 35, 10) if is_unlocked else (25, 20, 10)
        else:
            bg = (30, 30, 50) if is_unlocked else (20, 15, 15)
        border = YELLOW if is_sel else ((255, 215, 0) if is_vip else (80, 80, 100))

        pygame.draw.rect(self.screen, bg, (bx, by, bw, bh))
        pygame.draw.rect(self.screen, border, (bx, by, bw, bh), 2 if not is_sel else 3)

        # Etichetta VIP
        if is_vip:
            vip_tag = self.font_tiny.render("VIP", True, (255, 215, 0))
            self.screen.blit(vip_tag, (bx + bw - 30, by + 3))

        # Nome
        name = SHIP_NAMES[index]
        nc = SHIP_COLORS[index] if is_unlocked else (100, 100, 100)
        ns = self.font_tiny.render(name, True, nc)
        self.screen.blit(ns, (bx + bw // 2 - ns.get_width() // 2, by + 5))

        # Sprite nave
        ship_size = 52
        scaled = pygame.transform.scale(Assets.player_ships[index], (ship_size, ship_size))
        if not is_unlocked:
            scaled.set_alpha(100)
        self.screen.blit(scaled, (bx + bw // 2 - ship_size // 2, by + 28))

        # Descrizione
        desc = SHIP_DESCS[index]
        dc = WHITE if is_unlocked else (80, 80, 80)
        # Wrap if needed
        words = desc.split()
        line1 = ""
        line2 = ""
        for w in words:
            test = line1 + " " + w if line1 else w
            if self.font_tiny.size(test)[0] < bw - 8:
                line1 = test
            else:
                line2 += (" " + w if line2 else w)
        ds1 = self.font_tiny.render(line1, True, dc)
        self.screen.blit(ds1, (bx + bw // 2 - ds1.get_width() // 2, by + 90))
        if line2:
            ds2 = self.font_tiny.render(line2, True, dc)
            self.screen.blit(ds2, (bx + bw // 2 - ds2.get_width() // 2, by + 108))

        # Stato sblocco
        unlock_score = _SHIP_UNLOCK_SCORES[index] if index < len(_SHIP_UNLOCK_SCORES) else 999
        if is_unlocked:
            st = self.font_tiny.render("DISPONIBILE", True, GREEN)
        else:
            st = self.font_tiny.render(f">{unlock_score}pt", True, ORANGE)
        self.screen.blit(st, (bx + bw // 2 - st.get_width() // 2, by + 135))

        # VIP doppio laser
        if is_vip and is_unlocked:
            dl = self.font_tiny.render("2x LASER", True, (255, 215, 0))
            self.screen.blit(dl, (bx + bw // 2 - dl.get_width() // 2, by + 155))

        # Indicatore selezione
        if is_sel and is_unlocked:
            sel = self.font_tiny.render("SELEZIONATA", True, YELLOW)
            self.screen.blit(sel, (bx + bw // 2 - sel.get_width() // 2, by + bh - 22))

    def handle_ship_select_input(self, event):
        if event.type != pygame.KEYDOWN:
            return
        cols = 5
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self.selected_ship = (self.selected_ship - 1) % NUM_SHIPS
            self.sounds["select"].play()
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.selected_ship = (self.selected_ship + 1) % NUM_SHIPS
            self.sounds["select"].play()
        elif event.key in (pygame.K_UP, pygame.K_w):
            new = self.selected_ship - cols
            if new >= 0:
                self.selected_ship = new
            self.sounds["select"].play()
        elif event.key in (pygame.K_DOWN, pygame.K_s):
            new = self.selected_ship + cols
            if new < NUM_SHIPS:
                self.selected_ship = new
            self.sounds["select"].play()
        elif event.key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.save["unlocked_ships"][self.selected_ship]:
                self.sounds["confirm"].play()
                self.state = "menu"
            else:
                self.sounds["game_over"].play()
        elif event.key == pygame.K_ESCAPE:
            self.state = "menu"
            self.sounds["select"].play()

    # ---- PAUSA OVERLAY ----

    def draw_pause_overlay(self):
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 180))
        self.screen.blit(ov, (0, 0))

        title = self.font_large.render("PAUSA", True, CYAN)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 170))

        pause_items = ["RIPRENDI", "TORNA AL MENU"]
        for i, txt in enumerate(pause_items):
            is_sel = (i == self._pause_selection)
            col = YELLOW if is_sel else WHITE
            pre = "> " if is_sel else "  "
            s = self.font_medium.render(f"{pre}{txt}", True, col)
            self.screen.blit(s, (SCREEN_WIDTH // 2 - s.get_width() // 2, 270 + i * 50))

        secs = self.game_time // 60
        stat = self.font_small.render(
            f"Punti: {self.score}   |   Tempo: {secs}s   |   Lv.{self._diff_level + 1}",
            True, YELLOW)
        self.screen.blit(stat, (SCREEN_WIDTH // 2 - stat.get_width() // 2, 410))

        hint = self.font_tiny.render(
            "W/S naviga  |  INVIO conferma  |  ESC/P riprendi",
            True, (100, 100, 130))
        self.screen.blit(hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 460))

    # ---- WARNING OVERLAY ----

    def _warn_overlay(self, timer, dur, subtitle, color, extra=None):
        flash = int(abs(math.sin(timer * 0.1)) * 80)
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        if color == RED:
            c = (flash, 0, 0, 100)
        else:
            c = (flash, int(flash * 0.6), 0, 120)
        ov.fill(c)
        self.screen.blit(ov, (0, 0))

        blink = 12 if color == RED else 10
        if (timer // blink) % 2 == 0:
            wt = self.font_large.render("!! WARNING !!", True, color)
            self.screen.blit(wt, (SCREEN_WIDTH // 2 - wt.get_width() // 2,
                                  SCREEN_HEIGHT // 2 - 60))

        sub = self.font_medium.render(subtitle, True, color)
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2,
                               SCREEN_HEIGHT // 2 + 10))
        if extra:
            ex = self.font_small.render(extra, True, WHITE)
            self.screen.blit(ex, (SCREEN_WIDTH // 2 - ex.get_width() // 2,
                                  SCREEN_HEIGHT // 2 + 50))

        prog = timer / dur
        bw, bh = 300, 8
        bx = SCREEN_WIDTH // 2 - bw // 2
        by2 = SCREEN_HEIGHT // 2 + (85 if extra else 60)
        pygame.draw.rect(self.screen, (60, 60, 60), (bx, by2, bw, bh))
        pygame.draw.rect(self.screen, color, (bx, by2, int(bw * prog), bh))

    # ---- DRAW GIOCO ----

    def draw_game(self):
        self.screen.fill(BLACK)
        self.stars.draw(self.screen)

        for l in self.player_lasers:
            l.draw(self.screen)
        for l in self.enemy_lasers:
            l.draw(self.screen)
        if self.boss_active and self.boss:
            self.boss.draw(self.screen)
        for g in self.formation_groups:
            g.draw(self.screen)
        for c in self.carriers:
            c.draw(self.screen)
        for p in self.falling_powerups:
            p.draw(self.screen)
        for a in self.asteroids:
            a.draw(self.screen)
        self.player.draw(self.screen)
        for e in self.explosions:
            e.draw(self.screen)

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

        # Powerup popup messages
        self._draw_pu_popups()

        if self._paused:
            self.draw_pause_overlay()

    def _draw_pu_popups(self):
        """Disegna i popup dei power-up raccolti (PRD: flash 1.5s)."""
        py = SCREEN_HEIGHT // 2 - 30
        for text, color, timer in self._pu_popups:
            alpha = min(255, timer * 4)
            s = self.font_medium.render(text, True, color)
            s.set_alpha(alpha)
            self.screen.blit(s, (SCREEN_WIDTH // 2 - s.get_width() // 2, py))
            py -= 35

    def _draw_hud(self):
        """Disegna l'HUD in-game (punteggio, vite, tempo, livello, power-up, weapon bar)."""
        hud_y = 38 if (self.boss_active and self.boss and self.boss.alive) else 10

        # Sfondo punteggio
        bg = pygame.Surface((200, 40), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        self.screen.blit(bg, (10, hud_y))

        sc = self.font_medium.render(f"Punti: {self.score}", True, WHITE)
        self.screen.blit(sc, (20, hud_y + 8))
        self._draw_lives(hud_y)

        # Tempo
        secs = self.game_time // 60
        tt = self.font_small.render(f"Tempo: {secs}s", True, (180, 180, 200))
        self.screen.blit(tt, (SCREEN_WIDTH - 150, hud_y + 8))

        # Livello + Wave (PRD)
        dlvl = self.font_tiny.render(
            f"Lv.{self._diff_level + 1}  Wave {self._wave_num}", True, (120, 200, 120))
        self.screen.blit(dlvl, (SCREEN_WIDTH - 120, hud_y + 35))

        # Nome formazione attuale
        if self.formation_groups:
            fn = self.formation_groups[-1].formation_name
            fi = self.font_tiny.render(fn, True, (180, 180, 200))
            self.screen.blit(fi, (SCREEN_WIDTH // 2 - fi.get_width() // 2, hud_y))

        # Indicatore fase speciale
        if self.rain_active or self.rain_draining:
            col = ORANGE if (self.game_time // 20) % 2 == 0 else YELLOW
            label = "PIOGGIA DI ASTEROIDI" if self.rain_active else "ASTEROIDI IN VOLO..."
            ri = self.font_tiny.render(f"* {label}", True, col)
            self.screen.blit(ri, (SCREEN_WIDTH // 2 - ri.get_width() // 2, hud_y + 18))
        elif self.boss_active:
            bi = self.font_tiny.render(
                f"BOSS FIGHT!  (sconfitti: {self.boss_defeated_count})",
                True, ORANGE)
            self.screen.blit(bi, (SCREEN_WIDTH - 320, hud_y + 18))

        # Weapon level bar (PRD: 7 segmenti arancione-verde)
        self._draw_weapon_bar(hud_y)

        # Cooldown sparo
        ticks = pygame.time.get_ticks()
        cd = max(0, self.player.shot_cooldown - (ticks - self.player.last_shot_time))
        if cd > 0:
            pct = cd / self.player.shot_cooldown
            pygame.draw.rect(self.screen, (60, 60, 60), (20, hud_y + 45, 60, 6))
            pygame.draw.rect(self.screen, CYAN, (20, hud_y + 45, int(60 * (1 - pct)), 6))

        # Hint pausa
        ph = self.font_tiny.render("ESC/P = Pausa", True, (70, 70, 95))
        self.screen.blit(ph, (SCREEN_WIDTH // 2 - ph.get_width() // 2, SCREEN_HEIGHT - 18))

        self._draw_pu_hud(hud_y)

    def _draw_weapon_bar(self, hud_y):
        """Disegna la barra livello arma a 7 segmenti (PRD: arancione->verde)."""
        max_lv = self.player.max_weapon_level
        cur_lv = self.player.weapon_level
        bar_x = 225
        bar_y = hud_y + 32
        seg_w = 14
        seg_h = 8
        gap = 2

        label = self.font_tiny.render(f"WPN Lv{cur_lv}", True, ORANGE)
        self.screen.blit(label, (bar_x, bar_y - 12))

        for i in range(max_lv):
            x = bar_x + i * (seg_w + gap)
            if i < cur_lv:
                # Colore gradiente arancione -> verde
                t = i / max(1, max_lv - 1)
                r = int(255 * (1 - t))
                g = int(200 + 55 * t)
                col = (r, g, 0)
            else:
                col = (40, 40, 55)
            pygame.draw.rect(self.screen, col, (x, bar_y, seg_w, seg_h))

    def _draw_pu_hud(self, hud_y):
        """Disegna le barre dei power-up attivi nell'HUD (PRD: blue shield, green speed)."""
        active = []
        if self.player.shield_active:
            active.append((
                "SCUDO", CYAN,
                self.player.shield_timer / 60,
                self.player.shield_timer / self.player.shield_duration))
        if self.player.speed_boost_active:
            active.append((
                "VELOCITA", GREEN,  # PRD: green
                self.player.speed_boost_timer / 60,
                self.player.speed_boost_timer / self.player.speed_boost_duration))
        if self.player.triple_shot_active:
            active.append((
                f"ARMA Lv{self.player.weapon_level}", ORANGE,
                self.player.triple_shot_timer / 60,
                self.player.triple_shot_timer / self.player.triple_shot_duration))
        if not active:
            return

        py = SCREEN_HEIGHT - 40
        for name, col, sl, pct in active:
            bg = pygame.Surface((130, 18), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 150))
            self.screen.blit(bg, (10, py))
            lbl = self.font_tiny.render(f"{name} {sl:.1f}s", True, col)
            self.screen.blit(lbl, (14, py + 1))
            pygame.draw.rect(self.screen, (40, 40, 40), (10, py + 16, 130, 3))
            pygame.draw.rect(self.screen, col, (10, py + 16, int(130 * pct), 3))
            py -= 22

    def _draw_lives(self, hud_y):
        """Disegna i cuori delle vite del giocatore (PRD: max 4)."""
        sz, sp = 18, 24
        sx, sy = 225, hud_y + 12
        for i in range(Player.MAX_LIVES):
            col = RED if i < self.player.lives else (60, 60, 60)
            self._heart(self.screen, sx + i * sp, sy, sz, col)

    @staticmethod
    def _heart(surf, x, y, sz, col):
        r = sz // 4
        pygame.draw.circle(surf, col, (x + r, y + r), r)
        pygame.draw.circle(surf, col, (x + sz // 2 + r, y + r), r)
        pygame.draw.polygon(surf, col, [(x, y + r), (x + sz, y + r), (x + sz // 2, y + sz)])

    # ---- INPUT IN-GAME ----

    def handle_game_input(self, event):
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

    # ---- GAME OVER ----

    def draw_game_over(self):
        self.screen.fill(BLACK)
        self.stars.draw(self.screen)
        ov = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        self.screen.blit(ov, (0, 0))

        go = self.font_large.render("GAME OVER", True, RED)
        self.screen.blit(go, (SCREEN_WIDTH // 2 - go.get_width() // 2, 90))

        sc = self.font_medium.render(f"Punteggio: {self.score}", True, WHITE)
        self.screen.blit(sc, (SCREEN_WIDTH // 2 - sc.get_width() // 2, 170))

        is_new = (self.score >= self.save["high_score"] and self.score > 0)
        rp = "NUOVO RECORD!  " if is_new else "Record: "
        rec = self.font_medium.render(
            f"{rp}{self.save['high_score']}",
            True, YELLOW if is_new else (180, 180, 200))
        self.screen.blit(rec, (SCREEN_WIDTH // 2 - rec.get_width() // 2, 215))

        secs = self.game_time // 60
        tt = self.font_small.render(
            f"Sopravvissuto: {secs}s  |  Lv.{self._diff_level + 1}  |  Wave {self._wave_num}",
            True, (180, 180, 200))
        self.screen.blit(tt, (SCREEN_WIDTH // 2 - tt.get_width() // 2, 255))

        # Check unlock notifications
        unlocked_names = []
        for i, threshold in enumerate(_SHIP_UNLOCK_SCORES):
            if i < NUM_SHIPS and self.score >= threshold and self.save["unlocked_ships"][i]:
                # Only show newly unlockable ships
                pass  # The save manager already handled it
        if self.score >= 500 and self.save["unlocked_ships"][VIP_SHIP_INDEX]:
            ul = self.font_medium.render("NAVE OMEGA VIP SBLOCCATA!", True, (255, 215, 0))
            self.screen.blit(ul, (SCREEN_WIDTH // 2 - ul.get_width() // 2, 290))

        r1 = self.font_small.render("INVIO/SPAZIO -- Rigioca", True, GREEN)
        r2 = self.font_small.render("ESC -- Menu", True, (150, 150, 170))
        self.screen.blit(r1, (SCREEN_WIDTH // 2 - r1.get_width() // 2, 340))
        self.screen.blit(r2, (SCREEN_WIDTH // 2 - r2.get_width() // 2, 375))

        if self.save["best_scores"]:
            top = self.font_small.render("Top Punteggi:", True, YELLOW)
            self.screen.blit(top, (SCREEN_WIDTH // 2 - top.get_width() // 2, 420))
            for i, s in enumerate(self.save["best_scores"][:5]):
                st = self.font_tiny.render(f"{i + 1}. {s} pt", True, (180, 180, 200))
                self.screen.blit(st, (SCREEN_WIDTH // 2 - st.get_width() // 2, 445 + i * 20))

    def handle_game_over_input(self, event):
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

    def run(self):
        """Loop principale del gioco - processa eventi, aggiorna e disegna."""
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
