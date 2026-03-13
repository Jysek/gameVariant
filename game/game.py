"""Space Shooter — Infinite Survival  |  game.py v4
Autori: Ceccariglia Emanuele & Andrea Cestelli — ITSUmbria 2026
"""
import math, random, sys
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
from entities.formations import pick_formation, build_spawn_positions
from entities.formation_group import FormationGroup

from world.starfield import StarField

# ── Anti-overlap inter-gruppo ─────────────────────────────────────────────
# Minima distanza verticale tra il top di un nuovo gruppo e il bottom
# del gruppo più vicino ancora sullo schermo.
_MIN_GROUP_V_GAP = 120   # pixel

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Space Shooter - Infinite Survival")
        self.clock = pygame.time.Clock()

        Assets.load()

        self.sounds   = create_sounds()
        self.bg_music = generate_background_music(duration_ms=8000, volume=0.12)
        self.stars    = StarField()
        self.save     = load_save_data()

        self.font_large  = pygame.font.Font(None, 64)
        self.font_medium = pygame.font.Font(None, 36)
        self.font_small  = pygame.font.Font(None, 28)
        self.font_tiny   = pygame.font.Font(None, 22)

        self.state          = "menu"
        self.selected_ship  = 0
        self.menu_selection = 0
        self._music_channel = None
        self._credits_scroll = float(SCREEN_HEIGHT)
        self.reset_game()

    # ── MUSICA ───────────────────────────────────────────────────────────
    def _start_music(self):
        if self._music_channel is None or not self._music_channel.get_busy():
            self._music_channel = self.bg_music.play(loops=-1)
    def _stop_music(self):
        if self._music_channel: self._music_channel.stop()

    # ── RESET ────────────────────────────────────────────────────────────
    def reset_game(self):
        clear_registry()
        self.player            = Player(self.selected_ship)
        self.formation_groups: list[FormationGroup] = []
        self.player_lasers: list[Laser]   = []
        self.enemy_lasers:  list[Laser]   = []
        self.explosions:    list[Explosion] = []
        self.score = 0; self.game_time = 0

        self.spawn_timer    = 0
        self.spawn_interval = random.randint(120, 300)

        self.boss = None; self.boss_active = False
        self.boss_warning = False; self.boss_warning_timer = 0
        self.boss_warning_dur = 180; self.boss_defeated_count = 0
        self.next_boss_time = random.randint(35*60, 65*60)
        self.boss_cooldown  = 0

        self.carriers:         list[PowerUpCarrier]  = []
        self.falling_powerups: list[FallingPowerUp]  = []
        self.carrier_timer    = 0
        self.carrier_interval = random.randint(12*60, 28*60)

        self.asteroids:         list[Asteroid] = []
        self.asteroid_timer    = 0
        self.asteroid_interval = random.randint(10*60, 22*60)

        # Pioggia asteroidi — BILANCIATA
        self.rain_active   = False; self.rain_warning = False
        self.rain_w_timer  = 0;     self.rain_w_dur   = 180
        self.rain_timer    = 0;     self.rain_dur     = 0
        self.rain_spawn_t  = 0;     self.rain_spawn_i = 35  # spawn ogni 35f (max ~1.7/s)
        self.next_rain     = random.randint(50*60, 100*60)
        self.rain_cooldown = 0
        self.rain_count    = 0   # quanti asteroidi spawnati in questa pioggia
        self.rain_max      = 0   # cap asteroidi per pioggia

        self._diff_level  = 0
        self._next_diff   = DIFFICULTY_INTERVAL * 60
        self._paused      = False

    # ── DIFFICOLTA' ──────────────────────────────────────────────────────
    def _speed_mult(self)->float:
        return DIFFICULTY_SPEED_SCALE**self._diff_level
    def _update_diff(self):
        if self._diff_level>=DIFFICULTY_MAX_LEVEL: return
        if self.game_time>=self._next_diff:
            self._diff_level+=1; self._next_diff+=DIFFICULTY_INTERVAL*60

    # ── ANTI-OVERLAP ─────────────────────────────────────────────────────
    def _can_spawn_group(self)->bool:
        """True se non ci sono gruppi troppo vicini al top dello schermo."""
        if not self.formation_groups: return True
        for g in self.formation_groups:
            if not g.is_empty and g.top_edge < _MIN_GROUP_V_GAP:
                return False
        return True

    def _total_alive(self)->int:
        return sum(len(g.alive_enemies) for g in self.formation_groups)

    # ── SPAWN ─────────────────────────────────────────────────────────────
    def _spawn_formation(self):
        if self.boss_active or self.boss_warning: return
        if self.rain_active or self.rain_warning: return
        max_alive = 6 + self._diff_level * 2   # cap ridotto: meno chaos
        if self._total_alive() >= max_alive: return
        if not self._can_spawn_group(): return

        self.spawn_timer+=1
        if self.spawn_timer < self.spawn_interval: return
        self.spawn_timer=0
        base_min=max(80, 220-self._diff_level*18)
        base_max=max(140,440-self._diff_level*35)
        self.spawn_interval=random.randint(base_min,base_max)

        name,slots=pick_formation(self._diff_level)
        data=build_spawn_positions(slots)
        g=FormationGroup(data,self._speed_mult(),name,self._diff_level)
        self.formation_groups.append(g)

    def _spawn_carriers(self):
        self.carrier_timer+=1
        if self.carrier_timer>=self.carrier_interval:
            self.carrier_timer=0
            self.carrier_interval=random.randint(12*60,28*60)
            if len(self.carriers)<2: self.carriers.append(PowerUpCarrier())

    def _spawn_asteroids(self):
        if self.rain_active or self.rain_warning: return
        self.asteroid_timer+=1
        if self.asteroid_timer>=self.asteroid_interval:
            self.asteroid_timer=0
            self.asteroid_interval=random.randint(10*60,22*60)
            if len(self.asteroids)<2:
                self.asteroids.append(Asteroid())
                self.sounds["asteroid_warning"].play()

    # ── EVENTI SPECIALI ──────────────────────────────────────────────────
    def _check_boss(self):
        if self.boss_active or self.boss_warning: return
        if self.rain_active or self.rain_warning: return
        if self.boss_cooldown>0: self.boss_cooldown-=1; return
        if self.game_time>=self.next_boss_time:
            self.boss_warning=True; self.boss_warning_timer=0
            self.sounds["boss_warning"].play()

    def _do_spawn_boss(self):
        self.boss=Boss(); self.boss_active=True; self.boss_warning=False
        bonus=self.boss_defeated_count*10
        self.boss.max_hp=60+bonus; self.boss.hp=self.boss.max_hp
        self.boss.h_speed=2.0+self.boss_defeated_count*0.3
        self.boss.shoot_interval=max(22,55-self.boss_defeated_count*4)
        self.formation_groups.clear(); self.enemy_lasers.clear()

    def _on_boss_defeated(self):
        cx=self.boss.x+self.boss.width//2; cy=self.boss.y+self.boss.height//2
        self.explosions.append(Explosion(cx,cy,size=128))
        for _ in range(5):
            self.explosions.append(Explosion(
                self.boss.x+random.randint(0,self.boss.width),
                self.boss.y+random.randint(0,self.boss.height)))
        self.sounds["boss_defeated"].play()
        self.score+=20+self.boss_defeated_count*5
        self.boss_defeated_count+=1; self.boss_active=False; self.boss=None
        self.boss_cooldown=random.randint(18*60,38*60)
        self.next_boss_time=self.game_time+random.randint(30*60,60*60)
        self.enemy_lasers.clear()

    def _check_rain(self):
        if self.rain_active or self.rain_warning: return
        if self.boss_active or self.boss_warning: return
        if self.rain_cooldown>0: self.rain_cooldown-=1; return
        if self.game_time>=self.next_rain:
            self.rain_warning=True; self.rain_w_timer=0
            self.sounds["asteroid_rain_warning"].play()

    def _start_rain(self):
        self.rain_active=True; self.rain_warning=False
        # Durata e cap asteroidi bilanciate per livello
        base_dur=8*60+self._diff_level*30  # 8-11s circa
        self.rain_dur=min(base_dur,14*60)
        self.rain_timer=0; self.rain_spawn_t=0
        # Intervallo spawn: più lento ai livelli bassi
        self.rain_spawn_i=max(22, 45-self._diff_level*3)
        # Cap: non più di N asteroidi contemporaneamente
        self.rain_max=3+self._diff_level
        self.rain_count=0
        self.formation_groups.clear(); self.enemy_lasers.clear()
        for a in self.asteroids: a.deactivate()
        self.asteroids.clear(); clear_registry()

    def _end_rain(self):
        self.rain_active=False
        self.rain_cooldown=random.randint(45*60,90*60)
        self.next_rain=self.game_time+random.randint(50*60,100*60)
        for a in self.asteroids: a.deactivate()
        self.asteroids.clear(); clear_registry()

    # ── UPDATE GAMEPLAY ──────────────────────────────────────────────────
    def update_game(self):
        if self._paused: return
        self.game_time+=1; self._update_diff()
        keys=pygame.key.get_pressed()

        if self.boss_warning:
            self._upd_boss_warning(keys); return
        if self.rain_warning:
            self._upd_rain_warning(keys); return
        if self.rain_active:
            self._upd_rain(keys); return
        self._upd_normal(keys)

    def _upd_boss_warning(self,keys):
        self.boss_warning_timer+=1
        if self.boss_warning_timer>=self.boss_warning_dur: self._do_spawn_boss()
        self.player.update(keys); self._upd_explosions(); self._upd_asteroids()

    def _upd_rain_warning(self,keys):
        self.rain_w_timer+=1
        if self.rain_w_timer>=self.rain_w_dur: self._start_rain()
        self.player.update(keys); self._upd_explosions()

    def _upd_rain(self,keys):
        self.rain_timer+=1
        if self.rain_timer>=self.rain_dur:
            self._end_rain()
        else:
            self.rain_spawn_t+=1
            # Spawn solo se sotto il cap
            if (self.rain_spawn_t>=self.rain_spawn_i and
                    len(self.asteroids)<self.rain_max):
                self.rain_spawn_t=0
                self.asteroids.append(Asteroid())
        self.player.update(keys)
        self._shoot(keys)
        self._upd_all_entities()
        pr=self.player.get_rect()
        self._chk_asteroid_player(pr)
        self._chk_pu_player(pr)
        self._cleanup()
        if not self.player.alive: self._game_over()

    def _upd_normal(self,keys):
        self.player.update(keys); self._shoot(keys)
        self._check_boss(); self._check_rain()
        self._spawn_formation(); self._spawn_carriers(); self._spawn_asteroids()

        if self.boss_active and self.boss and self.boss.alive:
            for bl in self.boss.update():
                self.enemy_lasers.append(bl)
                if random.random()<0.3: self.sounds["boss_laser"].play()

        hit_bottom=False
        for g in self.formation_groups:
            fell=g.update()
            if fell: hit_bottom=True
            for l in g.pending_lasers:
                self.enemy_lasers.append(l)
                self.sounds["enemy_laser"].play()

        if hit_bottom:
            dead=self.player.take_damage()
            if dead: self._player_death_expl()
            else: self.sounds["player_hit"].play()
            self.formation_groups=[g for g in self.formation_groups
                                   if g.bottom_edge<SCREEN_HEIGHT]

        self._upd_all_entities()
        self._check_all()
        self._cleanup()
        if not self.player.alive: self._game_over()

    def _shoot(self,keys):
        if keys[pygame.K_SPACE]:
            ls=self.player.shoot(pygame.time.get_ticks())
            if ls: self.player_lasers.extend(ls); self.sounds["laser"].play()

    def _upd_all_entities(self):
        for l in self.player_lasers: l.update()
        for l in self.enemy_lasers:  l.update()
        for e in self.explosions:    e.update()
        for c in self.carriers:      c.update()
        for p in self.falling_powerups: p.update()
        for a in self.asteroids:     a.update()

    def _upd_explosions(self):
        for e in self.explosions: e.update()
        self.explosions=[e for e in self.explosions if e.active]

    def _upd_asteroids(self):
        for a in self.asteroids: a.update()
        self.asteroids=[a for a in self.asteroids if a.active]

    def _cleanup(self):
        self.player_lasers   =[l for l in self.player_lasers   if l.active]
        self.enemy_lasers    =[l for l in self.enemy_lasers     if l.active]
        self.formation_groups=[g for g in self.formation_groups if not g.is_empty]
        self.explosions      =[e for e in self.explosions       if e.active]
        self.carriers        =[c for c in self.carriers         if c.alive]
        self.falling_powerups=[p for p in self.falling_powerups if p.active]
        self.asteroids       =[a for a in self.asteroids        if a.active]

    # ── COLLISIONI ───────────────────────────────────────────────────────
    def _check_all(self):
        pr=self.player.get_rect()
        self._chk_pl_vs_boss(); self._chk_pl_vs_carrier()
        self._chk_pl_vs_formations()
        self._chk_el_vs_player(pr); self._chk_boss_vs_player(pr)
        self._chk_formation_vs_player(pr)
        self._chk_asteroid_player(pr); self._chk_pu_player(pr)

    def _chk_pl_vs_boss(self):
        if not(self.boss_active and self.boss and self.boss.alive): return
        for l in self.player_lasers:
            if not l.active or not self.boss: break
            if l.get_rect().colliderect(self.boss.get_rect()):
                l.active=False; self.sounds["boss_hit"].play()
                self.explosions.append(Explosion(l.x+2,l.y))
                if self.boss.take_damage(1): self._on_boss_defeated(); break

    def _chk_pl_vs_carrier(self):
        for l in self.player_lasers:
            if not l.active: continue
            for c in self.carriers:
                if not c.alive: continue
                if l.get_rect().colliderect(c.get_rect()):
                    l.active=False
                    if c.take_damage(1):
                        self.explosions.append(Explosion(c.x+c.width//2,c.y+c.height//2))
                        self.sounds["carrier_destroyed"].play()
                        self.falling_powerups.append(FallingPowerUp(
                            c.x+c.width//2-POWERUP_ITEM_SIZE//2,
                            c.y+c.height//2-POWERUP_ITEM_SIZE//2,c.powerup_type))
                    else: self.sounds["carrier_hit"].play()
                    break

    def _chk_pl_vs_formations(self):
        for l in self.player_lasers:
            if not l.active: continue
            hit=False
            for g in self.formation_groups:
                for rect,enemy in g.get_alive_rects():
                    if l.get_rect().colliderect(rect):
                        l.active=False
                        dead=enemy.take_damage(1)
                        if dead:
                            self.score+=g.score_per_kill
                            self.explosions.append(Explosion(
                                enemy.x+enemy.width//2,enemy.y+enemy.height//2))
                            self.sounds["explosion"].play()
                        else:
                            # nemico colpito ma non morto (bomber/fighter multi-HP)
                            self.sounds["boss_hit"].play()
                        hit=True; break
                if hit: break

    def _chk_el_vs_player(self,pr):
        for l in self.enemy_lasers:
            if not l.active: continue
            if l.get_rect().colliderect(pr):
                l.active=False
                if self.player.shield_active: self.sounds["shield_break"].play()
                elif not self.player.invincible:
                    dead=self.player.take_damage()
                    if dead: self._player_death_expl()
                    else: self.sounds["player_hit"].play()

    def _chk_boss_vs_player(self,pr):
        if not(self.boss_active and self.boss and self.boss.alive): return
        if self.boss.get_rect().colliderect(pr):
            if self.player.shield_active: self.sounds["shield_break"].play()
            elif not self.player.invincible:
                self.player.lives=0; self.player.alive=False
                self._player_death_expl()

    def _chk_formation_vs_player(self,pr):
        for g in self.formation_groups:
            for rect,enemy in g.get_alive_rects():
                if rect.colliderect(pr):
                    enemy.alive=False
                    self.explosions.append(Explosion(enemy.x+enemy.width//2,enemy.y+enemy.height//2))
                    if self.player.shield_active: self.sounds["shield_break"].play()
                    elif not self.player.invincible:
                        dead=self.player.take_damage()
                        if dead: self._player_death_expl()
                        else: self.sounds["player_hit"].play()

    def _chk_asteroid_player(self,pr):
        for a in self.asteroids:
            if not a.active: continue
            if a.get_rect().colliderect(pr):
                if self.player.shield_active:
                    self.sounds["shield_break"].play()
                    a.deactivate(); return
                self.player.lives=0; self.player.alive=False
                self.explosions.append(Explosion(
                    self.player.x+self.player.width//2,
                    self.player.y+self.player.height//2,size=128))
                self.sounds["game_over"].play(); return

    def _chk_pu_player(self,pr):
        for p in self.falling_powerups:
            if not p.active: continue
            if p.get_rect().colliderect(pr):
                p.active=False; self.player.apply_powerup(p.powerup_type)
                self.sounds["powerup_collect"].play()
                if p.powerup_type=="scudo": self.sounds["shield_active"].play()

    def _player_death_expl(self):
        self.explosions.append(Explosion(
            self.player.x+self.player.width//2,
            self.player.y+self.player.height//2))
        self.sounds["game_over"].play()

    # ── GAME OVER ────────────────────────────────────────────────────────
    def _game_over(self):
        self._stop_music()
        if self.score>self.save["high_score"]: self.save["high_score"]=self.score
        if self.score>=50 and not self.save["unlocked_ships"][2]:
            self.save["unlocked_ships"][2]=True; self.sounds["unlock"].play()
        self.save["best_scores"].append(self.score)
        self.save["best_scores"].sort(reverse=True)
        self.save["best_scores"]=self.save["best_scores"][:10]
        save_data(self.save); self.state="game_over"

    # ── PAUSA ────────────────────────────────────────────────────────────
    def _toggle_pause(self):
        self._paused=not self._paused
        if self._paused:
            self.sounds["pause"].play()
            if self._music_channel: self._music_channel.pause()
        else:
            self.sounds["resume"].play()
            if self._music_channel: self._music_channel.unpause()

    # ═══════════════════════════════════════════════════════════════════
    # DRAW
    # ═══════════════════════════════════════════════════════════════════

    def draw_menu(self):
        self.screen.fill(DARK_GRAY); self.stars.draw(self.screen)
        t1=self.font_large.render("SPACE SHOOTER",True,CYAN)
        t2=self.font_medium.render("Infinite Survival",True,WHITE)
        self.screen.blit(t1,(SCREEN_WIDTH//2-t1.get_width()//2,70))
        self.screen.blit(t2,(SCREEN_WIDTH//2-t2.get_width()//2,140))
        scaled=pygame.transform.scale(Assets.player_ships[self.selected_ship],(60,60))
        self.screen.blit(scaled,(SCREEN_WIDTH//2-30,190))
        items=["GIOCA","NAVICELLE","CREDITI","ESCI"]
        for i,item in enumerate(items):
            col=YELLOW if i==self.menu_selection else WHITE
            pre="> " if i==self.menu_selection else "  "
            t=self.font_medium.render(f"{pre}{item}",True,col)
            self.screen.blit(t,(SCREEN_WIDTH//2-t.get_width()//2,290+i*48))
        hint=self.font_tiny.render("↑↓/WS naviga  |  INVIO/SPAZIO conferma",True,(100,100,130))
        self.screen.blit(hint,(SCREEN_WIDTH//2-hint.get_width()//2,500))
        hs=self.font_small.render(f"Record: {self.save['high_score']} punti",True,YELLOW)
        self.screen.blit(hs,(SCREEN_WIDTH//2-hs.get_width()//2,530))
        cr=self.font_tiny.render("Ceccariglia Emanuele & Andrea Cestelli — ITSUmbria 2026",True,(90,90,110))
        self.screen.blit(cr,(SCREEN_WIDTH//2-cr.get_width()//2,565))

    def handle_menu_input(self,event):
        if event.type!=pygame.KEYDOWN: return
        n=4
        if event.key in(pygame.K_UP,pygame.K_w):
            self.menu_selection=(self.menu_selection-1)%n; self.sounds["select"].play()
        elif event.key in(pygame.K_DOWN,pygame.K_s):
            self.menu_selection=(self.menu_selection+1)%n; self.sounds["select"].play()
        elif event.key in(pygame.K_RETURN,pygame.K_SPACE):
            self.sounds["confirm"].play()
            if   self.menu_selection==0: self.reset_game(); self.state="playing"; self._start_music()
            elif self.menu_selection==1: self.state="ship_select"
            elif self.menu_selection==2: self._credits_scroll=float(SCREEN_HEIGHT); self.state="credits"
            elif self.menu_selection==3: pygame.quit(); sys.exit()

    def draw_credits(self):
        self.screen.fill(BLACK); self.stars.draw(self.screen)
        ov=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,120))
        self.screen.blit(ov,(0,0))
        lines=[
            ("SPACE SHOOTER",self.font_large,CYAN),
            ("Infinite Survival",self.font_medium,WHITE),("",self.font_small,WHITE),
            ("━"*34,self.font_tiny,(80,80,120)),("",self.font_small,WHITE),
            ("SVILUPPATORI",self.font_medium,YELLOW),
            ("Ceccariglia Emanuele",self.font_small,WHITE),
            ("Andrea Cestelli",self.font_small,WHITE),("",self.font_small,WHITE),
            ("CORSO",self.font_medium,YELLOW),
            ("ITSUmbria 2026",self.font_small,WHITE),("",self.font_small,WHITE),
            ("TECNOLOGIE",self.font_medium,YELLOW),
            ("Python 3 / Pygame-CE / Pillow",self.font_small,WHITE),("",self.font_small,WHITE),
            ("Premi ESC per tornare al menu",self.font_small,(150,150,180)),
        ]
        y=self._credits_scroll
        for text,font,color in lines:
            s=font.render(text,True,color)
            if -50<y<SCREEN_HEIGHT+10: self.screen.blit(s,(SCREEN_WIDTH//2-s.get_width()//2,int(y)))
            y+=font.size(text)[1]+6
        self._credits_scroll-=1.0
        if y<0: self._credits_scroll=float(SCREEN_HEIGHT)

    def handle_credits_input(self,event):
        if event.type==pygame.KEYDOWN: self.state="menu"; self.sounds["select"].play()

    def draw_ship_select(self):
        self.screen.fill(DARK_GRAY); self.stars.draw(self.screen)
        title=self.font_large.render("NAVICELLE",True,CYAN)
        self.screen.blit(title,(SCREEN_WIDTH//2-title.get_width()//2,30))
        names=["Falcon","Viper","Phoenix"]
        descs=["Classica — affidabile","Doppia ala — agile","Doppio cannone — VIP"]
        colors=[CYAN,GREEN,MAGENTA]; unlocks=[0,0,50]
        for i in range(3): self._ship_card(i,names[i],descs[i],colors[i],unlocks[i])
        instr=self.font_small.render("< A/D scegli | INVIO conferma | ESC indietro >",True,(150,150,170))
        self.screen.blit(instr,(SCREEN_WIDTH//2-instr.get_width()//2,530))

    def _ship_card(self,index,name,desc,color,unlock_score):
        bx,by,bw,bh=50+index*245,120,225,380
        is_sel=index==self.selected_ship
        is_unlocked=self.save["unlocked_ships"][index]
        border=YELLOW if is_sel else(80,80,100)
        bg=(30,30,50) if is_unlocked else(20,15,15)
        pygame.draw.rect(self.screen,bg,(bx,by,bw,bh))
        pygame.draw.rect(self.screen,border,(bx,by,bw,bh),2)
        nc=color if is_unlocked else(100,100,100)
        ns=self.font_medium.render(name,True,nc)
        self.screen.blit(ns,(bx+bw//2-ns.get_width()//2,by+15))
        scaled=pygame.transform.scale(Assets.player_ships[index],(60,60))
        if not is_unlocked: scaled.set_alpha(100)
        self.screen.blit(scaled,(bx+bw//2-30,by+70))
        dc=WHITE if is_unlocked else(80,80,80)
        ds=self.font_small.render(desc,True,dc)
        self.screen.blit(ds,(bx+bw//2-ds.get_width()//2,by+170))
        st=self.font_small.render("DISPONIBILE" if is_unlocked else f"Sblocca >{unlock_score}pt",
                                   True,GREEN if is_unlocked else ORANGE)
        self.screen.blit(st,(bx+bw//2-st.get_width()//2,by+240))
        if is_sel and is_unlocked:
            sel=self.font_small.render("SELEZIONATA",True,YELLOW)
            self.screen.blit(sel,(bx+bw//2-sel.get_width()//2,by+350))

    def handle_ship_select_input(self,event):
        if event.type!=pygame.KEYDOWN: return
        if event.key in(pygame.K_LEFT,pygame.K_a):
            self.selected_ship=(self.selected_ship-1)%3; self.sounds["select"].play()
        elif event.key in(pygame.K_RIGHT,pygame.K_d):
            self.selected_ship=(self.selected_ship+1)%3; self.sounds["select"].play()
        elif event.key in(pygame.K_RETURN,pygame.K_SPACE):
            if self.save["unlocked_ships"][self.selected_ship]:
                self.sounds["confirm"].play(); self.state="menu"
            else: self.sounds["game_over"].play()
        elif event.key==pygame.K_ESCAPE: self.state="menu"; self.sounds["select"].play()

    def draw_pause_overlay(self):
        ov=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,160))
        self.screen.blit(ov,(0,0))
        title=self.font_large.render("PAUSA",True,CYAN)
        self.screen.blit(title,(SCREEN_WIDTH//2-title.get_width()//2,200))
        for i,(txt,col) in enumerate([("P — Riprendi",WHITE),("ESC — Menu",(180,180,200))]):
            s=self.font_medium.render(txt,True,col)
            self.screen.blit(s,(SCREEN_WIDTH//2-s.get_width()//2,300+i*50))
        secs=self.game_time//60
        stat=self.font_small.render(
            f"Punti: {self.score}   |   Tempo: {secs}s   |   Lv.{self._diff_level+1}",True,YELLOW)
        self.screen.blit(stat,(SCREEN_WIDTH//2-stat.get_width()//2,420))

    def _warn_overlay(self,timer,dur,subtitle,color,extra=None):
        flash=int(abs(math.sin(timer*0.1))*80)
        ov=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA)
        c=(flash,0,0,100) if color==RED else(flash,int(flash*0.6),0,120)
        ov.fill(c); self.screen.blit(ov,(0,0))
        blink=12 if color==RED else 10
        if(timer//blink)%2==0:
            wt=self.font_large.render("!! WARNING !!",True,color)
            self.screen.blit(wt,(SCREEN_WIDTH//2-wt.get_width()//2,SCREEN_HEIGHT//2-60))
        sub=self.font_medium.render(subtitle,True,color)
        self.screen.blit(sub,(SCREEN_WIDTH//2-sub.get_width()//2,SCREEN_HEIGHT//2+10))
        if extra:
            ex=self.font_small.render(extra,True,WHITE)
            self.screen.blit(ex,(SCREEN_WIDTH//2-ex.get_width()//2,SCREEN_HEIGHT//2+50))
        prog=timer/dur; bw,bh=300,8
        bx=SCREEN_WIDTH//2-bw//2; by2=SCREEN_HEIGHT//2+(85 if extra else 60)
        pygame.draw.rect(self.screen,(60,60,60),(bx,by2,bw,bh))
        pygame.draw.rect(self.screen,color,(bx,by2,int(bw*prog),bh))

    def draw_game(self):
        self.screen.fill(BLACK); self.stars.draw(self.screen)
        for l in self.player_lasers: l.draw(self.screen)
        for l in self.enemy_lasers:  l.draw(self.screen)
        if self.boss_active and self.boss: self.boss.draw(self.screen)
        for g in self.formation_groups: g.draw(self.screen)
        for c in self.carriers: c.draw(self.screen)
        for p in self.falling_powerups: p.draw(self.screen)
        for a in self.asteroids: a.draw(self.screen)
        self.player.draw(self.screen)
        for e in self.explosions: e.draw(self.screen)
        if self.boss_warning:
            self._warn_overlay(self.boss_warning_timer,self.boss_warning_dur,"BOSS IN ARRIVO",RED)
        if self.rain_warning:
            self._warn_overlay(self.rain_w_timer,self.rain_w_dur,"PIOGGIA DI ASTEROIDI",ORANGE,"Sopravvivi!")
        if self.boss_active and self.boss and self.boss.alive:
            self.boss.draw_health_bar(self.screen)
        self._draw_hud()
        if self._paused: self.draw_pause_overlay()

    def _draw_hud(self):
        hud_y=38 if(self.boss_active and self.boss and self.boss.alive) else 10
        bg=pygame.Surface((200,40),pygame.SRCALPHA); bg.fill((0,0,0,150))
        self.screen.blit(bg,(10,hud_y))
        sc=self.font_medium.render(f"Punti: {self.score}",True,WHITE)
        self.screen.blit(sc,(20,hud_y+8))
        self._draw_lives(hud_y)
        secs=self.game_time//60
        tt=self.font_small.render(f"Tempo: {secs}s",True,(180,180,200))
        self.screen.blit(tt,(SCREEN_WIDTH-150,hud_y+8))
        dlvl=self.font_tiny.render(f"Lv.{self._diff_level+1}",True,(120,200,120))
        self.screen.blit(dlvl,(SCREEN_WIDTH-55,hud_y+35))
        if self.rain_active:
            col=ORANGE if(self.rain_timer//20)%2==0 else YELLOW
            ri=self.font_tiny.render("☄ PIOGGIA DI ASTEROIDI",True,col)
            self.screen.blit(ri,(SCREEN_WIDTH//2-ri.get_width()//2,hud_y+35))
        elif self.boss_active:
            bi=self.font_tiny.render(f"BOSS FIGHT!  (sconfitti: {self.boss_defeated_count})",True,ORANGE)
            self.screen.blit(bi,(SCREEN_WIDTH-320,hud_y+35))
        else:
            alive=self._total_alive()
            fg=self.font_tiny.render(f"Nemici: {alive}  |  Gruppi: {len(self.formation_groups)}",True,RED)
            self.screen.blit(fg,(SCREEN_WIDTH-260,hud_y+35))
        ticks=pygame.time.get_ticks()
        cd=max(0,self.player.shot_cooldown-(ticks-self.player.last_shot_time))
        if cd>0:
            pct=cd/self.player.shot_cooldown
            pygame.draw.rect(self.screen,(60,60,60),(20,hud_y+45,60,6))
            pygame.draw.rect(self.screen,CYAN,(20,hud_y+45,int(60*(1-pct)),6))
        ph=self.font_tiny.render("P=Pausa",True,(70,70,95))
        self.screen.blit(ph,(SCREEN_WIDTH//2-ph.get_width()//2,SCREEN_HEIGHT-18))
        self._draw_pu_hud(hud_y)

    def _draw_pu_hud(self,hud_y):
        active=[]
        if self.player.shield_active:
            active.append(("SCUDO",CYAN,self.player.shield_timer/60,
                           self.player.shield_timer/self.player.shield_duration))
        if self.player.speed_boost_active:
            active.append(("VELOCITA",YELLOW,self.player.speed_boost_timer/60,
                           self.player.speed_boost_timer/self.player.speed_boost_duration))
        if self.player.triple_shot_active:
            active.append(("ARMA x3",ORANGE,self.player.triple_shot_timer/60,
                           self.player.triple_shot_timer/self.player.triple_shot_duration))
        if not active: return
        py=hud_y+58
        for name,col,sl,pct in active:
            bg=pygame.Surface((130,18),pygame.SRCALPHA); bg.fill((0,0,0,150))
            self.screen.blit(bg,(10,py))
            lbl=self.font_tiny.render(f"{name} {sl:.1f}s",True,col)
            self.screen.blit(lbl,(14,py+1))
            pygame.draw.rect(self.screen,(40,40,40),(10,py+16,130,3))
            pygame.draw.rect(self.screen,col,(10,py+16,int(130*pct),3))
            py+=22

    def _draw_lives(self,hud_y):
        sz,sp=18,24; sx,sy=225,hud_y+12
        for i in range(Player.MAX_LIVES):
            col=RED if i<self.player.lives else(60,60,60)
            self._heart(self.screen,sx+i*sp,sy,sz,col)

    @staticmethod
    def _heart(surf,x,y,sz,col):
        r=sz//4
        pygame.draw.circle(surf,col,(x+r,y+r),r)
        pygame.draw.circle(surf,col,(x+sz//2+r,y+r),r)
        pygame.draw.polygon(surf,col,[(x,y+r),(x+sz,y+r),(x+sz//2,y+sz)])

    def handle_game_input(self,event):
        if event.type!=pygame.KEYDOWN: return
        if event.key==pygame.K_p: self._toggle_pause()
        elif event.key==pygame.K_ESCAPE:
            self._paused=False; self._stop_music()
            self.state="menu"; self.sounds["select"].play()

    def draw_game_over(self):
        self.screen.fill(BLACK); self.stars.draw(self.screen)
        ov=pygame.Surface((SCREEN_WIDTH,SCREEN_HEIGHT),pygame.SRCALPHA); ov.fill((0,0,0,150))
        self.screen.blit(ov,(0,0))
        go=self.font_large.render("GAME OVER",True,RED)
        self.screen.blit(go,(SCREEN_WIDTH//2-go.get_width()//2,110))
        sc=self.font_medium.render(f"Punteggio: {self.score}",True,WHITE)
        self.screen.blit(sc,(SCREEN_WIDTH//2-sc.get_width()//2,200))
        is_new=self.score>=self.save["high_score"] and self.score>0
        rp="NUOVO RECORD!  " if is_new else "Record: "
        rec=self.font_medium.render(f"{rp}{self.save['high_score']}",True,YELLOW if is_new else(180,180,200))
        self.screen.blit(rec,(SCREEN_WIDTH//2-rec.get_width()//2,250))
        secs=self.game_time//60
        tt=self.font_small.render(f"Sopravvissuto: {secs}s  |  Lv.{self._diff_level+1}",True,(180,180,200))
        self.screen.blit(tt,(SCREEN_WIDTH//2-tt.get_width()//2,295))
        if self.score>=50 and self.save["unlocked_ships"][2]:
            ul=self.font_medium.render("NAVE PHOENIX SBLOCCATA!",True,MAGENTA)
            self.screen.blit(ul,(SCREEN_WIDTH//2-ul.get_width()//2,335))
        r1=self.font_small.render("INVIO/SPAZIO — Rigioca",True,GREEN)
        r2=self.font_small.render("ESC — Menu",True,(150,150,170))
        self.screen.blit(r1,(SCREEN_WIDTH//2-r1.get_width()//2,385))
        self.screen.blit(r2,(SCREEN_WIDTH//2-r2.get_width()//2,420))
        if self.save["best_scores"]:
            top=self.font_small.render("Top Punteggi:",True,YELLOW)
            self.screen.blit(top,(SCREEN_WIDTH//2-top.get_width()//2,465))
            for i,s in enumerate(self.save["best_scores"][:3]):
                st=self.font_tiny.render(f"{i+1}. {s} pt",True,(180,180,200))
                self.screen.blit(st,(SCREEN_WIDTH//2-st.get_width()//2,490+i*20))

    def handle_game_over_input(self,event):
        if event.type!=pygame.KEYDOWN: return
        if event.key in(pygame.K_RETURN,pygame.K_SPACE):
            self.sounds["confirm"].play(); self.reset_game(); self.state="playing"; self._start_music()
        elif event.key==pygame.K_ESCAPE:
            self.sounds["select"].play(); self.state="menu"

    # ── GAME LOOP ─────────────────────────────────────────────────────────
    def run(self):
        while True:
            for event in pygame.event.get():
                if event.type==pygame.QUIT: pygame.quit(); sys.exit()
                if   self.state=="menu":       self.handle_menu_input(event)
                elif self.state=="ship_select":self.handle_ship_select_input(event)
                elif self.state=="playing":    self.handle_game_input(event)
                elif self.state=="game_over":  self.handle_game_over_input(event)
                elif self.state=="credits":    self.handle_credits_input(event)
            self.stars.update()
            if self.state=="playing": self.update_game()
            if   self.state=="menu":       self.draw_menu()
            elif self.state=="ship_select":self.draw_ship_select()
            elif self.state=="playing":    self.draw_game()
            elif self.state=="game_over":  self.draw_game_over()
            elif self.state=="credits":    self.draw_credits()
            pygame.display.flip(); self.clock.tick(FPS)
