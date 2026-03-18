"""Space Shooter -- Infinite Survival  |  game.py v6

Autori: Ceccariglia Emanuele & Andrea Cestelli -- ITSUmbria 2026

Game loop principale, gestione stati, spawn, collisioni, HUD e pausa.

Changelog v6 rispetto a v5:
- Nemici base usano ``alien.png`` con dimensione ``ENEMY_W x ENEMY_H``.
- 15+ formazioni con sistema anti-ripetizione.
- Hitbox flash bianco rimosso dai nemici; sostituito con shake (come il boss).
- Pioggia asteroidi: corridoio sicuro garantito.
- Fix: ``_chk_pl_vs_boss()`` -- ``break`` nel ciclo laser corretto in ``continue``.
- Fix: ``_upd_boss_warning`` aggiorna anche le formazioni attive.
- Fix: reset_game() pulisce anche lo storico formazioni.
- Refactoring generale e commenti professionali.
"""

import math
import random
import sys

import pygame

from core.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS,
    BLACK, WHITE, RED, GREEN, YELLOW, CYAN, MAGENTA, ORANGE,
    DARK_GRAY, POWERUP_ITEM_SIZE,
    DIFFICULTY_INTERVAL, DIFFICULTY_SPEED_SCALE, DIFFICULTY_MAX_LEVEL,
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
from entities.formations import (
    pick_formation, build_spawn_positions, reset_formation_history,
)
from entities.formation_group import FormationGroup

from world.starfield import StarField

# ---------------------------------------------------------------------------
# Costante anti-overlap verticale tra gruppi di formazione.
# Un nuovo gruppo non puo' spawnare finche' il bordo superiore del gruppo
# piu' vicino non e' sceso di almeno questo valore in pixel.
# ---------------------------------------------------------------------------
_MIN_GROUP_V_GAP = 140  # pixel


class Game:
    """Classe principale del gioco: gestisce game loop, stati e rendering.

    La macchina a stati gestisce le seguenti fasi:
    ``menu`` -> ``ship_select`` / ``credits`` / ``playing`` -> ``game_over``
    """

    # ======================================================================
    # INIT
    # ======================================================================

    def __init__(self):
        """Inizializza schermo, asset, suoni, font e stato iniziale."""
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter - Infinite Survival")
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
        self.state: str            = "menu"
        self.selected_ship: int    = 0
        self.menu_selection: int   = 0
        self._music_channel        = None
        self._credits_scroll: float = float(SCREEN_HEIGHT)

        # Pausa: selezione voce nel menu di pausa (0 = Riprendi, 1 = Menu)
        self._pause_selection: int = 0

        self.reset_game()

    # ======================================================================
    # MUSICA
    # ======================================================================

    def _start_music(self) -> None:
        """Avvia la musica di sottofondo in loop (se non gia' in riproduzione)."""
        if self._music_channel is None or not self._music_channel.get_busy():
            self._music_channel = self.bg_music.play(loops=-1)

    def _stop_music(self) -> None:
        """Ferma la musica di sottofondo."""
        if self._music_channel:
            self._music_channel.stop()

    # ======================================================================
    # RESET
    # ======================================================================

    def reset_game(self) -> None:
        """Resetta completamente lo stato di gioco per una nuova partita.

        Pulisce tutte le liste di entita', resetta timer e contatori,
        e resetta lo storico formazioni per evitare bias.
        """
        clear_registry()
        reset_formation_history()

        self.player = Player(self.selected_ship)

        # Liste entita'
        self.formation_groups: list[FormationGroup] = []
        self.player_lasers:    list[Laser]          = []
        self.enemy_lasers:     list[Laser]          = []
        self.explosions:       list[Explosion]       = []
        self.carriers:         list[PowerUpCarrier]  = []
        self.falling_powerups: list[FallingPowerUp]  = []
        self.asteroids:        list[Asteroid]        = []

        self.score     = 0
        self.game_time = 0

        # Timer e intervallo spawn formazioni nemiche
        self.spawn_timer    = 0
        self.spawn_interval = random.randint(120, 300)

        # Boss
        self.boss: Boss | None     = None
        self.boss_active: bool     = False
        self.boss_warning: bool    = False
        self.boss_warning_timer    = 0
        self.boss_warning_dur      = 180       # 3 secondi di avviso
        self.boss_defeated_count   = 0
        self.next_boss_time        = random.randint(35 * 60, 65 * 60)
        self.boss_cooldown         = 0

        # Carrier power-up
        self.carrier_timer    = 0
        self.carrier_interval = random.randint(12 * 60, 28 * 60)

        # Asteroidi singoli
        self.asteroid_timer    = 0
        self.asteroid_interval = random.randint(10 * 60, 22 * 60)

        # -- Pioggia di asteroidi --
        self.rain_active: bool   = False
        self.rain_warning: bool  = False
        self.rain_w_timer        = 0
        self.rain_w_dur          = 180       # 3 secondi di avviso
        self.rain_timer          = 0
        self.rain_dur            = 0         # calcolata in _start_rain
        self.rain_spawn_t        = 0
        self.rain_spawn_i        = 35        # intervallo spawn singolo asteroide
        self.next_rain           = random.randint(50 * 60, 100 * 60)
        self.rain_cooldown       = 0
        self.rain_max            = 0         # max asteroidi contemporanei
        self.rain_draining: bool = False

        # Difficolta' progressiva
        self._diff_level = 0
        self._next_diff  = DIFFICULTY_INTERVAL * 60

        # Pausa
        self._paused: bool     = False
        self._pause_selection  = 0

    # ======================================================================
    # DIFFICOLTA'
    # ======================================================================

    def _speed_mult(self) -> float:
        """Restituisce il moltiplicatore di velocita' per il livello corrente."""
        return DIFFICULTY_SPEED_SCALE ** self._diff_level

    def _update_diff(self) -> None:
        """Avanza il livello di difficolta' se il tempo lo permette."""
        if self._diff_level >= DIFFICULTY_MAX_LEVEL:
            return
        if self.game_time >= self._next_diff:
            self._diff_level += 1
            self._next_diff += DIFFICULTY_INTERVAL * 60

    # ======================================================================
    # ANTI-OVERLAP TRA GRUPPI
    # ======================================================================

    def _can_spawn_group(self) -> bool:
        """Verifica che nessun gruppo esistente sia ancora troppo in alto.

        Un nuovo gruppo spawna sopra lo schermo (y negativa).  Per evitare
        sovrapposizioni, si aspetta che tutti i gruppi gia' presenti abbiano
        il bordo superiore almeno a ``_MIN_GROUP_V_GAP`` pixel.
        """
        if not self.formation_groups:
            return True
        if len(self.formation_groups) >= 3:
            return False
        for g in self.formation_groups:
            if not g.is_empty and g.top_edge < _MIN_GROUP_V_GAP:
                return False
        return True

    def _total_alive(self) -> int:
        """Conta il totale di nemici vivi in tutti i gruppi attivi."""
        return sum(len(g.alive_enemies) for g in self.formation_groups)

    # ======================================================================
    # SPAWN
    # ======================================================================

    def _spawn_formation(self) -> None:
        """Tenta di spawnare una nuova formazione nemica.

        Condizioni di blocco:
        - Boss attivo o in arrivo.
        - Pioggia attiva o in arrivo.
        - Troppi nemici gia' vivi (cap dinamico per livello).
        - Un gruppo precedente non e' sceso abbastanza.
        """
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

        # Reset timer e calcola prossimo intervallo
        self.spawn_timer = 0
        base_min = max(80, 220 - self._diff_level * 18)
        base_max = max(base_min + 40, 440 - self._diff_level * 35)
        self.spawn_interval = random.randint(base_min, base_max)

        # Scegli e costruisci la formazione
        name, slots = pick_formation(self._diff_level)
        data  = build_spawn_positions(slots, self.formation_groups)
        group = FormationGroup(data, self._speed_mult(), name, self._diff_level)
        self.formation_groups.append(group)

    def _spawn_carriers(self) -> None:
        """Gestisce lo spawn periodico dei carrier power-up."""
        self.carrier_timer += 1
        if self.carrier_timer >= self.carrier_interval:
            self.carrier_timer = 0
            self.carrier_interval = random.randint(12 * 60, 28 * 60)
            if len(self.carriers) < 2:
                self.carriers.append(PowerUpCarrier())

    def _spawn_asteroids(self) -> None:
        """Gestisce lo spawn periodico di asteroidi singoli (fuori dalla pioggia)."""
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
        """Controlla se e' il momento di far apparire il boss."""
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

    def _do_spawn_boss(self) -> None:
        """Spawna il boss dopo il warning e scala le sue statistiche."""
        self.boss = Boss()
        self.boss_active  = True
        self.boss_warning = False

        bonus = self.boss_defeated_count * 10
        self.boss.max_hp = 60 + bonus
        self.boss.hp     = self.boss.max_hp
        self.boss.h_speed = 2.0 + self.boss_defeated_count * 0.3
        self.boss.shoot_interval = max(22, 55 - self.boss_defeated_count * 4)

        # Pulisci il campo per la boss fight
        self.formation_groups.clear()
        self.enemy_lasers.clear()

    def _on_boss_defeated(self) -> None:
        """Gestisce la sconfitta del boss: esplosioni, punteggio, cooldown."""
        cx = self.boss.x + self.boss.width // 2
        cy = self.boss.y + self.boss.height // 2

        # Esplosione grande + esplosioni minori casuali
        self.explosions.append(Explosion(cx, cy, size=128))
        for _ in range(5):
            self.explosions.append(Explosion(
                self.boss.x + random.randint(0, self.boss.width),
                self.boss.y + random.randint(0, self.boss.height)))
        self.sounds["boss_defeated"].play()

        # Punteggio bonus progressivo
        self.score += 20 + self.boss_defeated_count * 5
        self.boss_defeated_count += 1
        self.boss_active = False
        self.boss = None

        # Cooldown e prossimo boss
        self.boss_cooldown  = random.randint(18 * 60, 38 * 60)
        self.next_boss_time = self.game_time + random.randint(30 * 60, 60 * 60)
        self.enemy_lasers.clear()

    # ======================================================================
    # EVENTI SPECIALI: PIOGGIA DI ASTEROIDI
    # ======================================================================

    def _check_rain(self) -> None:
        """Controlla se e' il momento di attivare la pioggia di asteroidi."""
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
        """Avvia la fase attiva della pioggia di asteroidi.

        I parametri di durata, intervallo e cap vengono calcolati in base
        al livello di difficolta' corrente.
        """
        self.rain_active   = True
        self.rain_warning  = False
        self.rain_draining = False

        base_dur = 8 * 60 + self._diff_level * 60
        self.rain_dur     = min(base_dur, 16 * 60)
        self.rain_timer   = 0
        self.rain_spawn_t = 0
        self.rain_spawn_i = max(22, 45 - self._diff_level * 3)
        self.rain_max     = 4 + self._diff_level

        # Pulisci il campo
        self.formation_groups.clear()
        self.enemy_lasers.clear()
        for a in self.asteroids:
            a.deactivate()
        self.asteroids.clear()
        clear_registry()

    def _end_rain(self) -> None:
        """Termina la fase di spawn della pioggia.

        NON rimuove gli asteroidi in volo: attiva la fase 'draining'
        in cui completano la caduta naturalmente.
        """
        self.rain_active   = False
        self.rain_draining = True

    def _finish_rain_drain(self) -> None:
        """Chiamata quando tutti gli asteroidi della pioggia sono usciti."""
        self.rain_draining = False
        self.rain_cooldown = random.randint(45 * 60, 90 * 60)
        self.next_rain     = self.game_time + random.randint(50 * 60, 100 * 60)
        clear_registry()

    # ======================================================================
    # UPDATE GAMEPLAY
    # ======================================================================

    def update_game(self) -> None:
        """Aggiorna lo stato di gioco di un frame (chiamata ogni tick)."""
        if self._paused:
            return

        self.game_time += 1
        self._update_diff()
        keys = pygame.key.get_pressed()

        # Smista l'aggiornamento in base alla fase corrente
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

    # -- Sotto-fasi di update --

    def _upd_boss_warning(self, keys) -> None:
        """Update durante il warning del boss (3 secondi di lampeggio).

        Il giocatore puo' comunque muoversi e le formazioni gia' presenti
        continuano a scendere.
        """
        self.boss_warning_timer += 1
        if self.boss_warning_timer >= self.boss_warning_dur:
            self._do_spawn_boss()
        self.player.update(keys)

        # Le formazioni attive continuano il loro ciclo durante il warning
        for g in self.formation_groups:
            g.update()

        self._upd_explosions()
        self._upd_asteroids()

    def _upd_rain_warning(self, keys) -> None:
        """Update durante il warning della pioggia (3 secondi di lampeggio)."""
        self.rain_w_timer += 1
        if self.rain_w_timer >= self.rain_w_dur:
            self._start_rain()
        self.player.update(keys)
        self._upd_explosions()

    def _upd_rain(self, keys) -> None:
        """Update durante la pioggia attiva: spawna asteroidi e aggiorna."""
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
        """Update dopo la pioggia: asteroidi in volo completano la caduta."""
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
        """Update durante il gioco normale (nemici, boss, pioggia)."""
        self.player.update(keys)
        self._shoot(keys)

        # Controlla eventi speciali
        self._check_boss()
        self._check_rain()

        # Spawn
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

        # Se un nemico tocca il fondo, il giocatore perde una vita
        if hit_bottom:
            dead = self.player.take_damage()
            if dead:
                self._player_death_expl()
            else:
                self.sounds["player_hit"].play()
            # Rimuovi i gruppi che hanno raggiunto il fondo
            self.formation_groups = [
                g for g in self.formation_groups
                if g.bottom_edge < SCREEN_HEIGHT
            ]

        # Update tutte le entita'
        self._upd_all_entities()
        self._check_all()
        self._cleanup()

        if not self.player.alive:
            self._game_over()

    # -- Utilita' di update --

    def _shoot(self, keys) -> None:
        """Gestisce lo sparo del giocatore (tasto SPAZIO)."""
        if keys[pygame.K_SPACE]:
            lasers = self.player.shoot(pygame.time.get_ticks())
            if lasers:
                self.player_lasers.extend(lasers)
                self.sounds["laser"].play()

    def _upd_all_entities(self) -> None:
        """Aggiorna tutte le entita' attive."""
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
        """Aggiorna e rimuove le esplosioni terminate."""
        for expl in self.explosions:
            expl.update()
        self.explosions = [e for e in self.explosions if e.active]

    def _upd_asteroids(self) -> None:
        """Aggiorna e rimuove asteroidi inattivi."""
        for ast in self.asteroids:
            ast.update()
        self.asteroids = [a for a in self.asteroids if a.active]

    def _cleanup(self) -> None:
        """Rimuove tutte le entita' inattive dalle rispettive liste."""
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
        """Esegue tutti i controlli di collisione per il frame corrente."""
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
        """Collisione: laser del giocatore -> boss.

        Fix v6: il ciclo ora usa ``continue`` correttamente quando il boss
        viene sconfitto a meta' iterazione.
        """
        if not (self.boss_active and self.boss and self.boss.alive):
            return
        for laser in self.player_lasers:
            if not laser.active:
                continue
            # Il boss potrebbe essere stato sconfitto dal laser precedente
            if self.boss is None or not self.boss.alive:
                break
            if laser.get_rect().colliderect(self.boss.get_rect()):
                laser.active = False
                self.sounds["boss_hit"].play()
                self.explosions.append(Explosion(laser.x + 2, laser.y))
                if self.boss.take_damage(1):
                    self._on_boss_defeated()
                    break

    def _chk_pl_vs_carrier(self) -> None:
        """Collisione: laser del giocatore -> carrier power-up."""
        for laser in self.player_lasers:
            if not laser.active:
                continue
            for carrier in self.carriers:
                if not carrier.alive:
                    continue
                if laser.get_rect().colliderect(carrier.get_rect()):
                    laser.active = False
                    if carrier.take_damage(1):
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
                    break

    def _chk_pl_vs_formations(self) -> None:
        """Collisione: laser del giocatore -> nemici nelle formazioni."""
        for laser in self.player_lasers:
            if not laser.active:
                continue
            hit = False
            for group in self.formation_groups:
                for rect, enemy in group.get_alive_rects():
                    if laser.get_rect().colliderect(rect):
                        laser.active = False
                        dead = enemy.take_damage(1)
                        if dead:
                            self.score += group.score_per_kill
                            self.explosions.append(Explosion(
                                enemy.x + enemy.width // 2,
                                enemy.y + enemy.height // 2))
                            self.sounds["explosion"].play()
                        else:
                            # Nemico colpito ma non morto (multi-HP)
                            self.sounds["boss_hit"].play()
                        hit = True
                        break
                if hit:
                    break

    def _chk_el_vs_player(self, pr: pygame.Rect) -> None:
        """Collisione: laser nemici -> giocatore.

        Se lo scudo e' attivo il laser viene distrutto ma lo scudo
        resta intatto (immunita' completa per tutta la durata).
        """
        for laser in self.enemy_lasers:
            if not laser.active:
                continue
            if laser.get_rect().colliderect(pr):
                laser.active = False
                if self.player.shield_active:
                    self.sounds["shield_active"].play()
                elif not self.player.invincible:
                    dead = self.player.take_damage()
                    if dead:
                        self._player_death_expl()
                    else:
                        self.sounds["player_hit"].play()

    def _chk_boss_vs_player(self, pr: pygame.Rect) -> None:
        """Collisione: corpo del boss -> giocatore.

        Se lo scudo e' attivo il contatto viene ignorato.
        Altrimenti e' morte istantanea.
        """
        if not (self.boss_active and self.boss and self.boss.alive):
            return
        if self.boss.get_rect().colliderect(pr):
            if self.player.shield_active:
                pass  # scudo: immune
            elif not self.player.invincible:
                self.player.lives = 0
                self.player.alive = False
                self._player_death_expl()

    def _chk_formation_vs_player(self, pr: pygame.Rect) -> None:
        """Collisione: corpo nemico -> giocatore.

        Se lo scudo e' attivo il nemico viene distrutto ma il giocatore
        e lo scudo restano intatti.
        """
        for group in self.formation_groups:
            for rect, enemy in group.get_alive_rects():
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

    def _chk_asteroid_player(self, pr: pygame.Rect) -> None:
        """Collisione: asteroide -> giocatore.

        L'asteroide distrugge la navicella SEMPRE, anche se lo scudo
        e' attivo o il giocatore e' invincibile.  Game over immediato.
        """
        for ast in self.asteroids:
            if not ast.active:
                continue
            if ast.get_rect().colliderect(pr):
                self.player.shield_active = False
                self.player.shield_timer  = 0
                self.player.invincible    = False
                self.player.lives = 0
                self.player.alive = False
                self.explosions.append(Explosion(
                    self.player.x + self.player.width // 2,
                    self.player.y + self.player.height // 2,
                    size=128))
                self.sounds["game_over"].play()
                return

    def _chk_pu_player(self, pr: pygame.Rect) -> None:
        """Collisione: power-up cadente -> giocatore (raccolta)."""
        for pu in self.falling_powerups:
            if not pu.active:
                continue
            if pu.get_rect().colliderect(pr):
                pu.active = False
                self.player.apply_powerup(pu.powerup_type)
                self.sounds["powerup_collect"].play()
                if pu.powerup_type == "scudo":
                    self.sounds["shield_active"].play()

    def _player_death_expl(self) -> None:
        """Crea l'esplosione e suona il game over alla morte del giocatore."""
        self.explosions.append(Explosion(
            self.player.x + self.player.width // 2,
            self.player.y + self.player.height // 2))
        self.sounds["game_over"].play()

    # ======================================================================
    # GAME OVER
    # ======================================================================

    def _game_over(self) -> None:
        """Gestisce la fine della partita: salva punteggio e cambia stato."""
        self._stop_music()

        if self.score > self.save["high_score"]:
            self.save["high_score"] = self.score
        if self.score >= 50 and not self.save["unlocked_ships"][2]:
            self.save["unlocked_ships"][2] = True
            self.sounds["unlock"].play()

        self.save["best_scores"].append(self.score)
        self.save["best_scores"].sort(reverse=True)
        self.save["best_scores"] = self.save["best_scores"][:10]
        save_data(self.save)

        self.state = "game_over"

    # ======================================================================
    # PAUSA
    # ======================================================================

    def _toggle_pause(self) -> None:
        """Attiva/disattiva la pausa.  Resetta la selezione del menu."""
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
        """Riprende il gioco dalla pausa."""
        self._paused = False
        self._pause_selection = 0
        self.sounds["resume"].play()
        if self._music_channel:
            self._music_channel.unpause()

    def _quit_to_menu_from_pause(self) -> None:
        """Esce al menu principale dalla pausa."""
        self._paused = False
        self._pause_selection = 0
        self._stop_music()
        self.state = "menu"
        self.sounds["select"].play()

    # ======================================================================
    # DRAW
    # ======================================================================

    # -- MENU PRINCIPALE --

    def draw_menu(self) -> None:
        """Disegna la schermata del menu principale."""
        self.screen.fill(DARK_GRAY)
        self.stars.draw(self.screen)

        t1 = self.font_large.render("SPACE SHOOTER", True, CYAN)
        t2 = self.font_medium.render("Infinite Survival", True, WHITE)
        self.screen.blit(t1, (SCREEN_WIDTH // 2 - t1.get_width() // 2, 70))
        self.screen.blit(t2, (SCREEN_WIDTH // 2 - t2.get_width() // 2, 140))

        # Anteprima nave selezionata
        scaled = pygame.transform.scale(
            Assets.player_ships[self.selected_ship], (60, 60))
        self.screen.blit(scaled, (SCREEN_WIDTH // 2 - 30, 190))

        items = ["GIOCA", "NAVICELLE", "CREDITI", "ESCI"]
        for i, item in enumerate(items):
            col = YELLOW if i == self.menu_selection else WHITE
            pre = "> " if i == self.menu_selection else "  "
            txt = self.font_medium.render(f"{pre}{item}", True, col)
            self.screen.blit(
                txt, (SCREEN_WIDTH // 2 - txt.get_width() // 2, 290 + i * 48))

        hint = self.font_tiny.render(
            "W/S naviga  |  INVIO/SPAZIO conferma", True, (100, 100, 130))
        self.screen.blit(
            hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 500))

        hs = self.font_small.render(
            f"Record: {self.save['high_score']} punti", True, YELLOW)
        self.screen.blit(hs, (SCREEN_WIDTH // 2 - hs.get_width() // 2, 530))

        cr = self.font_tiny.render(
            "Ceccariglia Emanuele & Andrea Cestelli -- ITSUmbria 2026",
            True, (90, 90, 110))
        self.screen.blit(cr, (SCREEN_WIDTH // 2 - cr.get_width() // 2, 565))

    def handle_menu_input(self, event: pygame.event.Event) -> None:
        """Gestisce l'input da tastiera nel menu principale."""
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

    # -- CREDITI --

    def draw_credits(self) -> None:
        """Disegna la schermata dei crediti con scrolling verticale."""
        self.screen.fill(BLACK)
        self.stars.draw(self.screen)
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 120))
        self.screen.blit(overlay, (0, 0))

        lines = [
            ("SPACE SHOOTER", self.font_large, CYAN),
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
            ("Python 3 / Pygame-CE / Pillow", self.font_small, WHITE),
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
        """Gestisce l'input nella schermata crediti."""
        if event.type == pygame.KEYDOWN:
            self.state = "menu"
            self.sounds["select"].play()

    # -- SELEZIONE NAVE --

    def draw_ship_select(self) -> None:
        """Disegna la schermata di selezione navicella."""
        self.screen.fill(DARK_GRAY)
        self.stars.draw(self.screen)
        title = self.font_large.render("NAVICELLE", True, CYAN)
        self.screen.blit(
            title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 30))

        names   = ["Falcon", "Viper", "Phoenix"]
        descs   = ["Classica -- affidabile",
                    "Doppia ala -- agile",
                    "Doppio cannone -- VIP"]
        colors  = [CYAN, GREEN, MAGENTA]
        unlocks = [0, 0, 50]
        for i in range(3):
            self._ship_card(i, names[i], descs[i], colors[i], unlocks[i])

        instr = self.font_small.render(
            "< A/D scegli | INVIO conferma | ESC indietro >",
            True, (150, 150, 170))
        self.screen.blit(
            instr, (SCREEN_WIDTH // 2 - instr.get_width() // 2, 530))

    def _ship_card(self, index: int, name: str, desc: str,
                   color: tuple, unlock_score: int) -> None:
        """Disegna la card di una singola navicella nella selezione."""
        bx = 50 + index * 245
        by, bw, bh = 120, 225, 380
        is_sel      = (index == self.selected_ship)
        is_unlocked = self.save["unlocked_ships"][index]

        border = YELLOW if is_sel else (80, 80, 100)
        bg     = (30, 30, 50) if is_unlocked else (20, 15, 15)
        pygame.draw.rect(self.screen, bg, (bx, by, bw, bh))
        pygame.draw.rect(self.screen, border, (bx, by, bw, bh), 2)

        nc = color if is_unlocked else (100, 100, 100)
        ns = self.font_medium.render(name, True, nc)
        self.screen.blit(ns, (bx + bw // 2 - ns.get_width() // 2, by + 15))

        scaled = pygame.transform.scale(Assets.player_ships[index], (60, 60))
        if not is_unlocked:
            scaled.set_alpha(100)
        self.screen.blit(scaled, (bx + bw // 2 - 30, by + 70))

        dc = WHITE if is_unlocked else (80, 80, 80)
        ds = self.font_small.render(desc, True, dc)
        self.screen.blit(ds, (bx + bw // 2 - ds.get_width() // 2, by + 170))

        st = self.font_small.render(
            "DISPONIBILE" if is_unlocked else f"Sblocca >{unlock_score}pt",
            True, GREEN if is_unlocked else ORANGE)
        self.screen.blit(st, (bx + bw // 2 - st.get_width() // 2, by + 240))

        if is_sel and is_unlocked:
            sel = self.font_small.render("SELEZIONATA", True, YELLOW)
            self.screen.blit(
                sel, (bx + bw // 2 - sel.get_width() // 2, by + 350))

    def handle_ship_select_input(self, event: pygame.event.Event) -> None:
        """Gestisce l'input nella schermata selezione nave."""
        if event.type != pygame.KEYDOWN:
            return
        if event.key in (pygame.K_LEFT, pygame.K_a):
            self.selected_ship = (self.selected_ship - 1) % 3
            self.sounds["select"].play()
        elif event.key in (pygame.K_RIGHT, pygame.K_d):
            self.selected_ship = (self.selected_ship + 1) % 3
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

    # -- PAUSA OVERLAY --

    def draw_pause_overlay(self) -> None:
        """Disegna l'overlay della pausa con menu selezionabile."""
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
                s, (SCREEN_WIDTH // 2 - s.get_width() // 2, 270 + i * 50))

        secs = self.game_time // 60
        stat = self.font_small.render(
            f"Punti: {self.score}   |   Tempo: {secs}s   |   "
            f"Lv.{self._diff_level + 1}",
            True, YELLOW)
        self.screen.blit(
            stat, (SCREEN_WIDTH // 2 - stat.get_width() // 2, 410))

        hint = self.font_tiny.render(
            "W/S naviga  |  INVIO conferma  |  ESC/P riprendi",
            True, (100, 100, 130))
        self.screen.blit(
            hint, (SCREEN_WIDTH // 2 - hint.get_width() // 2, 460))

    # -- WARNING OVERLAY --

    def _warn_overlay(self, timer: int, dur: int, subtitle: str,
                      color: tuple, extra: str | None = None) -> None:
        """Disegna l'overlay di avviso lampeggiante (boss o pioggia)."""
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
            wt = self.font_large.render("!! WARNING !!", True, color)
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

        # Barra di progresso warning
        prog = timer / dur
        bw, bh = 300, 8
        bx  = SCREEN_WIDTH // 2 - bw // 2
        by2 = SCREEN_HEIGHT // 2 + (85 if extra else 60)
        pygame.draw.rect(self.screen, (60, 60, 60), (bx, by2, bw, bh))
        pygame.draw.rect(self.screen, color, (bx, by2, int(bw * prog), bh))

    # -- DRAW GIOCO --

    def draw_game(self) -> None:
        """Disegna il frame di gioco completo."""
        self.screen.fill(BLACK)
        self.stars.draw(self.screen)

        # Entita'
        for laser in self.player_lasers:
            laser.draw(self.screen)
        for laser in self.enemy_lasers:
            laser.draw(self.screen)
        if self.boss_active and self.boss:
            self.boss.draw(self.screen)
        for group in self.formation_groups:
            group.draw(self.screen)
        for carrier in self.carriers:
            carrier.draw(self.screen)
        for pu in self.falling_powerups:
            pu.draw(self.screen)
        for ast in self.asteroids:
            ast.draw(self.screen)
        self.player.draw(self.screen)
        for expl in self.explosions:
            expl.draw(self.screen)

        # Overlay warning
        if self.boss_warning:
            self._warn_overlay(
                self.boss_warning_timer, self.boss_warning_dur,
                "BOSS IN ARRIVO", RED)
        if self.rain_warning:
            self._warn_overlay(
                self.rain_w_timer, self.rain_w_dur,
                "PIOGGIA DI ASTEROIDI", ORANGE, "Sopravvivi!")

        # Barra vita boss
        if self.boss_active and self.boss and self.boss.alive:
            self.boss.draw_health_bar(self.screen)

        # HUD
        self._draw_hud()

        # Overlay pausa (sopra tutto)
        if self._paused:
            self.draw_pause_overlay()

    def _draw_hud(self) -> None:
        """Disegna l'HUD in-game (punteggio, vite, tempo, livello, power-up)."""
        hud_y = 38 if (self.boss_active and self.boss
                       and self.boss.alive) else 10

        # Sfondo punteggio
        bg = pygame.Surface((200, 40), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 150))
        self.screen.blit(bg, (10, hud_y))

        sc = self.font_medium.render(f"Punti: {self.score}", True, WHITE)
        self.screen.blit(sc, (20, hud_y + 8))
        self._draw_lives(hud_y)

        # Tempo
        secs = self.game_time // 60
        tt = self.font_small.render(
            f"Tempo: {secs}s", True, (180, 180, 200))
        self.screen.blit(tt, (SCREEN_WIDTH - 150, hud_y + 8))

        # Livello
        dlvl = self.font_tiny.render(
            f"Lv.{self._diff_level + 1}", True, (120, 200, 120))
        self.screen.blit(dlvl, (SCREEN_WIDTH - 55, hud_y + 35))

        # Indicatore fase speciale
        if self.rain_active or self.rain_draining:
            col = ORANGE if (self.game_time // 20) % 2 == 0 else YELLOW
            label = ("PIOGGIA DI ASTEROIDI" if self.rain_active
                     else "ASTEROIDI IN VOLO...")
            ri = self.font_tiny.render(f"* {label}", True, col)
            self.screen.blit(
                ri, (SCREEN_WIDTH // 2 - ri.get_width() // 2, hud_y + 35))
        elif self.boss_active:
            bi = self.font_tiny.render(
                f"BOSS FIGHT!  (sconfitti: {self.boss_defeated_count})",
                True, ORANGE)
            self.screen.blit(bi, (SCREEN_WIDTH - 320, hud_y + 35))
        else:
            alive = self._total_alive()
            fg = self.font_tiny.render(
                f"Nemici: {alive}  |  Gruppi: {len(self.formation_groups)}",
                True, RED)
            self.screen.blit(fg, (SCREEN_WIDTH - 260, hud_y + 35))

        # Cooldown sparo
        ticks = pygame.time.get_ticks()
        cd = max(
            0,
            self.player.shot_cooldown - (ticks - self.player.last_shot_time))
        if cd > 0:
            pct = cd / self.player.shot_cooldown
            pygame.draw.rect(
                self.screen, (60, 60, 60), (20, hud_y + 45, 60, 6))
            pygame.draw.rect(
                self.screen, CYAN, (20, hud_y + 45, int(60 * (1 - pct)), 6))

        # Hint pausa
        ph = self.font_tiny.render("ESC/P = Pausa", True, (70, 70, 95))
        self.screen.blit(
            ph, (SCREEN_WIDTH // 2 - ph.get_width() // 2,
                 SCREEN_HEIGHT - 18))

        self._draw_pu_hud(hud_y)

    def _draw_pu_hud(self, hud_y: int) -> None:
        """Disegna le barre dei power-up attivi nell'HUD."""
        active: list[tuple[str, tuple, float, float]] = []
        if self.player.shield_active:
            active.append((
                "SCUDO", CYAN,
                self.player.shield_timer / 60,
                self.player.shield_timer / self.player.shield_duration))
        if self.player.speed_boost_active:
            active.append((
                "VELOCITA", YELLOW,
                self.player.speed_boost_timer / 60,
                self.player.speed_boost_timer / self.player.speed_boost_duration))
        if self.player.triple_shot_active:
            active.append((
                "ARMA x3", ORANGE,
                self.player.triple_shot_timer / 60,
                self.player.triple_shot_timer / self.player.triple_shot_duration))
        if not active:
            return

        py = hud_y + 58
        for name, col, secs_left, pct in active:
            bg = pygame.Surface((130, 18), pygame.SRCALPHA)
            bg.fill((0, 0, 0, 150))
            self.screen.blit(bg, (10, py))
            lbl = self.font_tiny.render(f"{name} {secs_left:.1f}s", True, col)
            self.screen.blit(lbl, (14, py + 1))
            pygame.draw.rect(
                self.screen, (40, 40, 40), (10, py + 16, 130, 3))
            pygame.draw.rect(
                self.screen, col, (10, py + 16, int(130 * pct), 3))
            py += 22

    def _draw_lives(self, hud_y: int) -> None:
        """Disegna i cuori delle vite del giocatore."""
        sz, sp = 18, 24
        sx, sy = 225, hud_y + 12
        for i in range(Player.MAX_LIVES):
            col = RED if i < self.player.lives else (60, 60, 60)
            self._heart(self.screen, sx + i * sp, sy, sz, col)

    @staticmethod
    def _heart(surf: pygame.Surface, x: int, y: int, sz: int,
               col: tuple) -> None:
        """Disegna un cuoricino alla posizione data."""
        r = sz // 4
        pygame.draw.circle(surf, col, (x + r, y + r), r)
        pygame.draw.circle(surf, col, (x + sz // 2 + r, y + r), r)
        pygame.draw.polygon(
            surf, col, [(x, y + r), (x + sz, y + r), (x + sz // 2, y + sz)])

    # -- INPUT IN-GAME --

    def handle_game_input(self, event: pygame.event.Event) -> None:
        """Gestisce l'input durante il gioco.

        ESC e P attivano la pausa.  Quando in pausa, W/S navigano il
        menu di pausa, INVIO/SPAZIO confermano, ESC/P riprendono.
        """
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

    # -- GAME OVER --

    def draw_game_over(self) -> None:
        """Disegna la schermata di game over con punteggio e statistiche."""
        self.screen.fill(BLACK)
        self.stars.draw(self.screen)
        overlay = pygame.Surface(
            (SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        self.screen.blit(overlay, (0, 0))

        go = self.font_large.render("GAME OVER", True, RED)
        self.screen.blit(go, (SCREEN_WIDTH // 2 - go.get_width() // 2, 110))

        sc = self.font_medium.render(
            f"Punteggio: {self.score}", True, WHITE)
        self.screen.blit(sc, (SCREEN_WIDTH // 2 - sc.get_width() // 2, 200))

        is_new = (self.score >= self.save["high_score"] and self.score > 0)
        rp  = "NUOVO RECORD!  " if is_new else "Record: "
        rec = self.font_medium.render(
            f"{rp}{self.save['high_score']}",
            True, YELLOW if is_new else (180, 180, 200))
        self.screen.blit(rec, (SCREEN_WIDTH // 2 - rec.get_width() // 2, 250))

        secs = self.game_time // 60
        tt = self.font_small.render(
            f"Sopravvissuto: {secs}s  |  Lv.{self._diff_level + 1}",
            True, (180, 180, 200))
        self.screen.blit(tt, (SCREEN_WIDTH // 2 - tt.get_width() // 2, 295))

        if self.score >= 50 and self.save["unlocked_ships"][2]:
            ul = self.font_medium.render(
                "NAVE PHOENIX SBLOCCATA!", True, MAGENTA)
            self.screen.blit(
                ul, (SCREEN_WIDTH // 2 - ul.get_width() // 2, 335))

        r1 = self.font_small.render("INVIO/SPAZIO -- Rigioca", True, GREEN)
        r2 = self.font_small.render("ESC -- Menu", True, (150, 150, 170))
        self.screen.blit(r1, (SCREEN_WIDTH // 2 - r1.get_width() // 2, 385))
        self.screen.blit(r2, (SCREEN_WIDTH // 2 - r2.get_width() // 2, 420))

        if self.save["best_scores"]:
            top = self.font_small.render("Top Punteggi:", True, YELLOW)
            self.screen.blit(
                top, (SCREEN_WIDTH // 2 - top.get_width() // 2, 465))
            for i, s in enumerate(self.save["best_scores"][:3]):
                st = self.font_tiny.render(
                    f"{i + 1}. {s} pt", True, (180, 180, 200))
                self.screen.blit(
                    st, (SCREEN_WIDTH // 2 - st.get_width() // 2,
                         490 + i * 20))

    def handle_game_over_input(self, event: pygame.event.Event) -> None:
        """Gestisce l'input nella schermata game over."""
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
        """Loop principale del gioco -- processa eventi, aggiorna e disegna."""
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
