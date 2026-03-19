"""
Costanti globali del gioco.

Contiene tutte le costanti condivise tra i moduli: dimensioni schermo,
colori, dimensioni sprite, tipi power-up e parametri di difficoltà.
"""

# ============================================================================
# SCHERMO & RENDERING
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
PLAYER_W          = 60
PLAYER_H          = 60
ENEMY_W           = 60
ENEMY_H           = 60
ASTEROID_SIZE     = 60
CARRIER_SIZE      = 55
POWERUP_ITEM_SIZE = 35
EXPLOSION_SIZE    = 64

# Alias retrocompatibile usato internamente dalle formazioni
ENEMY_SIZE = ENEMY_W

# ============================================================================
# NAVICELLE GIOCATORE -- 5 navi giocabili
# ============================================================================
NUM_PLAYER_SHIPS = 5

SHIP_NAMES = [
    "Viper",      # 0 - Agile, bilanciata
    "Phoenix",    # 1 - Corazzata, lenta
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

# Colore associato a ciascuna nave (usato per laser e HUD)
SHIP_COLORS = [
    GREEN,    # Viper
    MAGENTA,  # Phoenix
    ORANGE,   # Striker
    CYAN,     # Nova
    GOLD,     # Zenith
]

# Punteggio minimo per sbloccare ciascuna nave (0 = sbloccata di default)
SHIP_UNLOCK_SCORES = [0, 200, 500, 1000, 2000]

# Flag doppio cannone: True per le ultime 2 navi (Nova e Zenith)
SHIP_DOUBLE_CANNON = [False, False, False, True, True]

# ============================================================================
# STATISTICHE NAVE (rende ciascuna nave unica)
# ============================================================================
# Formato: {speed, fire_rate, damage, special}
#   speed:     moltiplicatore velocità base (1.0 = normale)
#   fire_rate: moltiplicatore cooldown sparo (< 1.0 = spara più veloce)
#   damage:    danno per colpo (1 = normale, 2 = doppio)
#   special:   abilità speciale unica per questa nave
SHIP_STATS = [
    {"speed": 1.0, "fire_rate": 1.0, "damage": 1, "special": "none"},
    {"speed": 0.8, "fire_rate": 1.3, "damage": 2, "special": "regen"},
    {"speed": 1.4, "fire_rate": 0.6, "damage": 1, "special": "piercing"},
    {"speed": 1.1, "fire_rate": 0.85, "damage": 1, "special": "emp"},
    {"speed": 0.9, "fire_rate": 1.0, "damage": 2, "special": "overdrive"},
]

# ============================================================================
# TIPI POWER-UP
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
# VARIANTI BOSS (4 boss)
# ============================================================================
NUM_BOSS_VARIANTS = 4

BOSS_NAMES = [
    "Titano",      # Cannoni rotanti alternati
    "Furia",       # Attacchi a raffica
    "Ventaglio",   # Onde a ventaglio
    "Vortice",     # Pattern a spirale
]

# ============================================================================
# TIPI NEMICO (statistiche)
# ============================================================================
ENEMY_TYPE_STATS = {
    "scout":   {"hp": 1, "score": 1,  "speed": 6, "color": "red"},
    "fighter": {"hp": 2, "score": 3,  "speed": 5, "color": "orange"},
    "bomber":  {"hp": 4, "score": 5,  "speed": 3, "color": "purple"},
    "elite":   {"hp": 3, "score": 8,  "speed": 5, "color": "cyan"},
}

# ============================================================================
# INTERVALLI DI SPARO NEMICO (frame min, max)
# ============================================================================
ENEMY_SHOOT_INTERVALS = {
    "scout":   (70, 160),
    "fighter": (100, 200),
    "bomber":  (160, 320),
    "elite":   (80, 180),
}

# ============================================================================
# DIFFICOLTÀ PROGRESSIVA
# ============================================================================
DIFFICULTY_INTERVAL    = 30   # secondi tra ogni incremento di livello
DIFFICULTY_SPEED_SCALE = 1.12 # moltiplicatore velocità per livello
DIFFICULTY_MAX_LEVEL   = 10   # livello massimo di difficoltà

# ============================================================================
# SISTEMA COMBO
# ============================================================================
COMBO_TIMEOUT_FRAMES  = 150  # frame prima che il combo scada
COMBO_MULT_THRESHOLDS = [3, 6, 10, 15, 25]
COMBO_SCORE_BONUS     = [0.5, 1.0, 1.5, 2.0, 3.0]

# ============================================================================
# SCREEN SHAKE
# ============================================================================
SHAKE_INTENSITY_LIGHT  = 3
SHAKE_INTENSITY_MEDIUM = 6
SHAKE_INTENSITY_HEAVY  = 10

# ============================================================================
# PERIODO DI GRAZIA (inizio partita)
# ============================================================================
GRACE_PERIOD_FRAMES = 180  # 3 secondi a 60 FPS

# ============================================================================
# SLOW MOTION (dopo boss kill)
# ============================================================================
SLOW_MO_DURATION = 90   # frame di slow motion
SLOW_MO_FACTOR   = 0.4  # fattore velocità durante slow-mo

# ============================================================================
# STREAK MOLTIPLICATORE PUNTEGGIO
# ============================================================================
STREAK_DECAY_FRAMES = 300  # frame prima che la streak decada
