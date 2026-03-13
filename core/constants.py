"""
Costanti globali del gioco.

Contiene tutte le costanti condivise: dimensioni schermo, colori,
dimensioni sprite, tipi di power-up e impostazioni generali.
"""

# ============================================================================
# SCHERMO E RENDERING
# ============================================================================
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
FPS = 60

# ============================================================================
# COLORI
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
# DIMENSIONI SPRITE
# ============================================================================
ENEMY_SIZE       = 50
ASTEROID_SIZE    = 60
CARRIER_SIZE     = 55
POWERUP_ITEM_SIZE = 35
EXPLOSION_SIZE   = 64

# ============================================================================
# NAVICELLE -- 10 selezionabili (9 standard + 1 VIP con doppio laser)
# ============================================================================
NUM_SHIPS = 10
VIP_SHIP_INDEX = 9  # L'ultima nave e' la VIP con doppio laser

SHIP_NAMES = [
    "Falcon",     # 0
    "Viper",      # 1
    "Phoenix",    # 2
    "Stinger",    # 3
    "Raptor",     # 4
    "Thunder",    # 5
    "Phantom",    # 6
    "Blaze",      # 7
    "Nova",       # 8
    "OMEGA VIP",  # 9 -- VIP doppio laser
]

SHIP_DESCS = [
    "Classica -- affidabile",
    "Doppia ala -- agile",
    "Cannone rinforzato",
    "Veloce -- stile vespa",
    "Precisione mortale",
    "Potenza bruta",
    "Invisibile -- stealth",
    "Scatto infuocato",
    "Equilibrio perfetto",
    "DOPPIO LASER -- VIP",
]

SHIP_COLORS = [
    CYAN, GREEN, MAGENTA, YELLOW, BLUE,
    ORANGE, (180, 100, 255), RED, (100, 255, 180),
    (255, 215, 0),  # Gold per VIP
]

# ============================================================================
# TIPI DI POWER-UP
# ============================================================================
POWERUP_TYPES = ["vita", "scudo", "velocita", "arma"]

# Colori associati ai power-up (usati nell'HUD e negli effetti visivi)
POWERUP_COLORS = {
    "vita":     GREEN,
    "scudo":    CYAN,
    "velocita": YELLOW,
    "arma":     ORANGE,
}

# ============================================================================
# LIVELLI ARMA (PRD: 7 livelli)
# ============================================================================
WEAPON_LEVELS = {
    1: "Single",
    2: "Double",
    3: "Triple 15",
    4: "5-way Spread",
    5: "Laser Beam",
    6: "Homing",
    7: "MAX Combo",
}

# ============================================================================
# DIFFICOLTA' PROGRESSIVA
# ============================================================================
# Ogni DIFFICULTY_INTERVAL secondi di gioco la difficolta' aumenta di un livello.
# La velocita' dei nemici viene moltiplicata per DIFFICULTY_SPEED_SCALE per livello.
DIFFICULTY_INTERVAL = 30        # secondi
DIFFICULTY_SPEED_SCALE = 1.12   # +12% velocita' nemici per livello
DIFFICULTY_MAX_LEVEL = 8        # livello massimo (cap)

# ============================================================================
# DROP RATE POWER-UP PER TIPO NEMICO (PRD)
# ============================================================================
DROP_RATES = {
    "scout":   {"arma": 0.10, "scudo": 0.05, "velocita": 0.08, "vita": 0.02},
    "fighter": {"arma": 0.18, "scudo": 0.12, "velocita": 0.10, "vita": 0.05},
    "bomber":  {"arma": 0.25, "scudo": 0.20, "velocita": 0.15, "vita": 0.15},
    "elite":   {"arma": 0.25, "scudo": 0.20, "velocita": 0.15, "vita": 0.15},
}

# ============================================================================
# BOSS
# ============================================================================
NUM_BOSS_VARIANTS = 4  # boss.gif + boss_1.png + boss_2.png + boss_3.png
