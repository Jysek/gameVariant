"""
Costanti globali del gioco.

Contiene tutte le costanti condivise tra i moduli: dimensioni schermo,
colori, dimensioni sprite, tipi di power-up e parametri di difficolta'.
"""

# ============================================================================
# SCHERMO E RENDERING
# ============================================================================
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# ============================================================================
# COLORI (R, G, B)
# ============================================================================
BLACK      = (0, 0, 0)
WHITE      = (255, 255, 255)
RED        = (255, 50, 50)
GREEN      = (50, 255, 50)
BLUE       = (50, 100, 255)
YELLOW     = (255, 255, 50)
CYAN       = (0, 255, 255)
MAGENTA    = (255, 0, 255)
ORANGE     = (255, 165, 0)
DARK_GRAY  = (30, 30, 40)
PANEL_BG   = (20, 20, 35)
STAR_WHITE = (200, 200, 220)

# ============================================================================
# DIMENSIONI SPRITE (pixel)
# ============================================================================
PLAYER_W         = 60
PLAYER_H         = 60
ENEMY_W          = 60
ENEMY_H          = 60
ASTEROID_SIZE    = 60
CARRIER_SIZE     = 55
POWERUP_ITEM_SIZE = 35
EXPLOSION_SIZE   = 64

# Alias retrocompatibile usato internamente nelle formazioni
ENEMY_SIZE = ENEMY_W

# ============================================================================
# NAVICELLE GIOCATORE
# ============================================================================
# 10 navi dal spritesheet navicelle.gif (3 righe x 4 colonne, 2 scartate).
# Ogni nave puo' essere sbloccata raggiungendo un certo punteggio.
NUM_PLAYER_SHIPS = 10

SHIP_NAMES = [
    "Viper",      "Phoenix",    "Striker",   "Nova",
    "Pulsar",     "Nebula",     "Comet",     "Eclipse",
    "Tempest",    "Zenith",
]

SHIP_DESCRIPTIONS = [
    "Agile -- bilanciata",
    "Doppio cannone -- VIP",
    "Pesante -- muro di fuoco",
    "Versatile -- precisa",
    "Evasiva -- rapida",
    "Devastante -- potente",
    "Rapida -- traccia luminosa",
    "Furtiva -- ombra spaziale",
    "Furiosa -- tempesta di laser",
    "Suprema -- distruttrice finale",
]

# Colori associati ad ogni nave (usati per laser e HUD)
SHIP_COLORS = [
    GREEN, MAGENTA, ORANGE, BLUE, (200, 100, 255), RED,
    (255, 200, 50), (100, 255, 200), (255, 100, 100), WHITE,
]

# Punteggi minimi per sbloccare ogni nave (0 = sbloccata di default)
SHIP_UNLOCK_SCORES = [0, 150, 500, 750, 1000, 1500, 2000, 3000, 4500, 6000]

# ============================================================================
# STATISTICHE PER NAVE (rendono ogni navicella unica)
# ============================================================================
# Formato: {speed, fire_rate, damage}
#   speed:     moltiplicatore velocita' base (1.0 = normale)
#   fire_rate: moltiplicatore cooldown sparo (< 1.0 = piu' veloce)
#   damage:    danno per colpo (1 = normale, 2 = doppio)
#
# Le navi con indice % 3 == 2 usano il pattern doppio cannone.
SHIP_STATS = [
    {"speed": 1.0,  "fire_rate": 1.0,  "damage": 1},  # Viper
    {"speed": 0.9,  "fire_rate": 1.1,  "damage": 1},  # Phoenix
    {"speed": 0.8,  "fire_rate": 1.3,  "damage": 2},  # Striker
    {"speed": 1.0,  "fire_rate": 1.0,  "damage": 1},  # Nova
    {"speed": 1.3,  "fire_rate": 0.8,  "damage": 1},  # Pulsar
    {"speed": 0.85, "fire_rate": 1.2,  "damage": 2},  # Nebula
    {"speed": 1.4,  "fire_rate": 0.7,  "damage": 1},  # Comet
    {"speed": 1.1,  "fire_rate": 0.9,  "damage": 1},  # Eclipse
    {"speed": 1.0,  "fire_rate": 0.65, "damage": 1},  # Tempest
    {"speed": 1.15, "fire_rate": 0.8,  "damage": 2},  # Zenith
]

# ============================================================================
# TIPI DI POWER-UP
# ============================================================================
POWERUP_TYPES = ["vita", "scudo", "velocita", "arma"]

POWERUP_COLORS = {
    "vita":     GREEN,
    "scudo":    CYAN,
    "velocita": YELLOW,
    "arma":     ORANGE,
}

# ============================================================================
# BOSS VARIANTI
# ============================================================================
NUM_BOSS_VARIANTS = 5  # boss.gif, boss_1.gif, boss_2.gif, boss_3.gif, boss_4.gif

# ============================================================================
# DIFFICOLTA' PROGRESSIVA
# ============================================================================
DIFFICULTY_INTERVAL    = 30
DIFFICULTY_SPEED_SCALE = 1.12
DIFFICULTY_MAX_LEVEL   = 8

# ============================================================================
# COMBO SYSTEM
# ============================================================================
COMBO_TIMEOUT_FRAMES = 120
COMBO_MULT_THRESHOLDS = [3, 6, 10, 15, 25]
COMBO_SCORE_BONUS     = [0.5, 1.0, 1.5, 2.0, 3.0]

# ============================================================================
# SCREEN SHAKE
# ============================================================================
SHAKE_INTENSITY_LIGHT  = 3
SHAKE_INTENSITY_MEDIUM = 6
SHAKE_INTENSITY_HEAVY  = 10

# ============================================================================
# GRACE PERIOD
# ============================================================================
GRACE_PERIOD_FRAMES = 120
