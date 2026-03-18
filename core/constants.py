"""
Costanti globali del gioco.

Contiene tutte le costanti condivise tra i moduli: dimensioni schermo,
colori, dimensioni sprite, tipi di power-up e parametri di difficolta'.

Nota: le costanti sono organizzate per categoria per facilitare la
manutenzione e la ricerca.
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
ENEMY_W          = 60      # larghezza nemico base (UFO e' piu' largo che alto)
ENEMY_H          = 44      # altezza nemico base
ASTEROID_SIZE    = 60
CARRIER_SIZE     = 55
POWERUP_ITEM_SIZE = 35
EXPLOSION_SIZE   = 64

# Alias retrocompatibile usato internamente nelle formazioni
ENEMY_SIZE = ENEMY_W

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
# DIFFICOLTA' PROGRESSIVA
# ============================================================================
# Ogni DIFFICULTY_INTERVAL secondi di gioco la difficolta' aumenta di un livello.
# La velocita' dei nemici viene moltiplicata per DIFFICULTY_SPEED_SCALE per livello.
DIFFICULTY_INTERVAL    = 30        # secondi tra un livello e l'altro
DIFFICULTY_SPEED_SCALE = 1.12      # +12% velocita' nemici per livello
DIFFICULTY_MAX_LEVEL   = 8         # livello massimo (cap)
