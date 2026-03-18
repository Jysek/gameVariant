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
GOLD       = (255, 215, 0)

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
# NAVICELLE GIOCATORE -- 5 navi giocabili
# ============================================================================
# 5 navi selezionate dal spritesheet navicelle.gif.
# Le ultime 2 (indici 3 e 4) hanno il doppio cannone.
NUM_PLAYER_SHIPS = 5

SHIP_NAMES = [
    "Viper",      # 0 - Agile, bilanciata
    "Phoenix",    # 1 - Resistente, lenta
    "Striker",    # 2 - Veloce, fragile
    "Nova",       # 3 - Doppio cannone, tattica
    "Zenith",     # 4 - Doppio cannone, distruttrice
]

SHIP_DESCRIPTIONS = [
    "Agile e bilanciata",
    "Corazzata e potente",
    "Veloce e letale",
    "Doppio cannone tattico",
    "Distruttrice suprema",
]

# Colori associati ad ogni nave (usati per laser e HUD)
SHIP_COLORS = [
    GREEN,                # Viper
    MAGENTA,              # Phoenix
    ORANGE,               # Striker
    CYAN,                 # Nova
    GOLD,                 # Zenith
]

# Punteggi minimi per sbloccare ogni nave (0 = sbloccata di default)
# Progressione: 0, 200, 500, 1000, 2000
SHIP_UNLOCK_SCORES = [0, 200, 500, 1000, 2000]

# Flag doppio cannone: True per le ultime 2 navi (Nova e Zenith)
SHIP_DOUBLE_CANNON = [False, False, False, True, True]

# ============================================================================
# STATISTICHE PER NAVE (rendono ogni navicella unica)
# ============================================================================
# Formato: {speed, fire_rate, damage, special}
#   speed:     moltiplicatore velocita' base (1.0 = normale)
#   fire_rate: moltiplicatore cooldown sparo (< 1.0 = spara piu' veloce)
#   damage:    danno per colpo (1 = normale, 2 = doppio)
#   special:   abilita' speciale unica della nave
SHIP_STATS = [
    # Viper: bilanciata, nessun eccesso, buona per imparare
    {"speed": 1.0,  "fire_rate": 1.0,  "damage": 1, "special": "none"},
    # Phoenix: lenta ma resistente, danno alto, rateo lento
    {"speed": 0.8,  "fire_rate": 1.3,  "damage": 2, "special": "regen"},
    # Striker: velocissima, spara veloce, danno base
    {"speed": 1.4,  "fire_rate": 0.6,  "damage": 1, "special": "piercing"},
    # Nova: doppio cannone, buona velocita', danno standard
    {"speed": 1.1,  "fire_rate": 0.85, "damage": 1, "special": "emp"},
    # Zenith: doppio cannone devastante, lenta, danno doppio
    {"speed": 0.9,  "fire_rate": 1.0,  "damage": 2, "special": "overdrive"},
]

# ============================================================================
# TIPI DI POWER-UP
# ============================================================================
POWERUP_TYPES = ["vita", "scudo", "velocita", "arma", "bomba"]

POWERUP_COLORS = {
    "vita":     GREEN,
    "scudo":    CYAN,
    "velocita": YELLOW,
    "arma":     ORANGE,
    "bomba":    MAGENTA,
}

# ============================================================================
# BOSS VARIANTI
# ============================================================================
NUM_BOSS_VARIANTS = 5  # boss.gif, boss_1.gif, boss_2.gif, boss_3.gif, boss_4.png

BOSS_NAMES = [
    "Titano",      # Classic
    "Furia",       # Burst
    "Ventaglio",   # Fan
    "Vortice",     # Spiral
    "Devastatore", # Shotgun
]

# ============================================================================
# TIPI DI NEMICO (statistiche)
# ============================================================================
ENEMY_TYPE_STATS = {
    "scout":   {"hp": 1, "score": 1,  "speed": 6, "color": "red"},
    "fighter": {"hp": 2, "score": 3,  "speed": 5, "color": "orange"},
    "bomber":  {"hp": 4, "score": 5,  "speed": 3, "color": "purple"},
    "elite":   {"hp": 3, "score": 8,  "speed": 5, "color": "cyan"},
}

# ============================================================================
# DIFFICOLTA' PROGRESSIVA
# ============================================================================
DIFFICULTY_INTERVAL    = 30
DIFFICULTY_SPEED_SCALE = 1.12
DIFFICULTY_MAX_LEVEL   = 10

# ============================================================================
# COMBO SYSTEM
# ============================================================================
COMBO_TIMEOUT_FRAMES = 150
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
GRACE_PERIOD_FRAMES = 180

# ============================================================================
# SLOW MOTION (nuovo)
# ============================================================================
SLOW_MO_DURATION = 90       # frame di slow motion dopo boss kill
SLOW_MO_FACTOR   = 0.4      # fattore velocita' durante slow-mo

# ============================================================================
# SCORE MULTIPLIER STREAK (nuovo)
# ============================================================================
STREAK_DECAY_FRAMES = 300   # frame prima che lo streak decada
