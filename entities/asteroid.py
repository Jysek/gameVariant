"""
Asteroid -- sprite con scia pixel-art.

Gli asteroidi cadono dall'alto verso il basso con rotazione e scia di
particelle luminose. Le particelle usano BLEND_ADD per un effetto fuoco.
Un registro globale `_active_x` previene la sovrapposizione orizzontale
tra asteroidi attivi.
"""
import random
import math
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ASTEROID_SIZE
from core.assets import Assets

# --------------------------------------------------------------------------
# Registro globale posizioni X degli asteroidi attivi.
# Serve per evitare che due asteroidi spawnino troppo vicini orizzontalmente.
# --------------------------------------------------------------------------
_active_x: list = []
_MIN_GAP = 90   # distanza minima orizzontale tra asteroidi (px)


def _safe_x(w: int) -> float:
    """Calcola una posizione X sicura per un nuovo asteroide.

    Tenta prima un posizionamento casuale che rispetti la distanza minima
    da tutti gli asteroidi attivi. Se fallisce dopo 30 tentativi, usa un
    approccio a colonne: divide lo schermo in 6 colonne e sceglie quella
    meno popolata.

    Args:
        w: Larghezza dell'asteroide in pixel.

    Returns:
        Posizione X come float.
    """
    for _ in range(30):
        x = random.randint(20, SCREEN_WIDTH - w - 20)
        if all(abs(x - ox) >= _MIN_GAP for ox in _active_x):
            return float(x)

    # Fallback: suddivisione in colonne
    cols = 6
    cw = (SCREEN_WIDTH - 40) // cols
    counts = [0] * cols
    for ox in _active_x:
        c = int((ox - 20) / cw)
        if 0 <= c < cols:
            counts[c] += 1
    best = counts.index(min(counts))
    return float(20 + best * cw + random.randint(0, max(0, cw - w)))


def clear_registry():
    """Pulisce il registro globale degli asteroidi attivi."""
    _active_x.clear()


# Parametri spritesheet scia
_N_FRAMES = 12
_FW = 32


class _Particle:
    """Singola particella della scia luminosa di un asteroide.

    Le particelle risalgono leggermente (simulando fumo caldo),
    avanzano nei frame dello spritesheet e si spengono gradualmente.
    """
    __slots__ = ('x', 'y', 'vx', 'vy', 'frame', 'alpha', 'sz', 'alive')

    def __init__(self, cx, cy):
        """Crea una particella vicino al centro dell'asteroide.

        Args:
            cx, cy: Centro dell'asteroide (pixel).
        """
        self.x     = cx + random.uniform(-10, 10)
        self.y     = cy + random.uniform(-6, 6)
        self.vx    = random.uniform(-0.3, 0.3)
        self.vy    = random.uniform(-1.0, -0.15)   # risale -- fumo caldo
        self.frame = float(random.randint(0, 2))    # parte da frame giovane
        self.alpha = random.randint(200, 255)
        self.sz    = random.uniform(0.5, 1.2)
        self.alive = True

    def update(self):
        """Aggiorna posizione, frame e opacita' della particella."""
        self.x += self.vx
        self.y += self.vy
        self.frame += 0.4
        self.alpha -= 16
        self.sz = max(0, self.sz - 0.02)
        if self.alpha <= 0 or self.sz < 0.05 or self.frame >= _N_FRAMES:
            self.alive = False

    def draw(self, surf, frames):
        """Disegna la particella usando il frame appropriato dello spritesheet.

        Args:
            surf: Surface di destinazione.
            frames: Lista dei frame dello spritesheet della scia.
        """
        fi = min(int(self.frame), _N_FRAMES - 1)
        src = frames[fi]
        sz = max(2, int(_FW * self.sz))
        scaled = pygame.transform.scale(src, (sz, sz))
        scaled.set_alpha(max(0, min(255, int(self.alpha))))
        surf.blit(
            scaled,
            (int(self.x - sz // 2), int(self.y - sz // 2)),
            special_flags=pygame.BLEND_ADD,
        )


class Asteroid:
    """Asteroide che cade dall'alto con rotazione e scia luminosa.

    Gli asteroidi sono indistruttibili (i laser non li colpiscono).
    Collisione con il giocatore = morte istantanea (salvo scudo).
    """

    MIN_SPEED = 1.8
    MAX_SPEED = 3.2

    def __init__(self):
        """Crea un nuovo asteroide sopra lo schermo in una posizione X sicura."""
        self.width  = ASTEROID_SIZE
        self.height = ASTEROID_SIZE
        self.x = _safe_x(self.width)
        self.y = float(-self.height - random.randint(0, 40))
        self.active = True

        # Registra la posizione X nel registro globale
        _active_x.append(self.x)

        self.fall_speed = random.uniform(self.MIN_SPEED, self.MAX_SPEED)
        self.angle     = 0.0
        self.rot_speed = random.choice([-3, -2, -1, 1, 2, 3])
        self.trail: list[_Particle] = []

    def update(self):
        """Aggiorna posizione, rotazione e scia dell'asteroide."""
        if not self.active:
            return

        self.y += self.fall_speed
        self.angle = (self.angle + self.rot_speed) % 360

        # Genera particelle per la scia
        cx = self.x + self.width // 2
        cy = self.y + self.height // 2
        for _ in range(random.randint(4, 6)):
            self.trail.append(_Particle(cx, cy))

        # Aggiorna e pulisci particelle
        for p in self.trail:
            p.update()
        self.trail = [p for p in self.trail if p.alive]

        # Disattiva se uscito dal basso dello schermo
        if self.y > SCREEN_HEIGHT + 60:
            self.active = False
            self._dereg()

    def _dereg(self):
        """Rimuove la posizione X dal registro globale."""
        try:
            _active_x.remove(self.x)
        except ValueError:
            pass

    def deactivate(self):
        """Disattiva esplicitamente l'asteroide e lo rimuove dal registro."""
        if self.active:
            self.active = False
            self._dereg()

    def draw(self, surf):
        """Disegna l'asteroide con la sua scia luminosa e rotazione.

        Args:
            surf: Surface di destinazione.
        """
        if not self.active:
            return

        # Disegna prima la scia (dietro l'asteroide)
        if Assets.trail_frames:
            for p in self.trail:
                p.draw(surf, Assets.trail_frames)

        # Disegna l'asteroide ruotato
        rot = pygame.transform.rotate(Assets.asteroid_sprite, self.angle)
        r = rot.get_rect(center=(
            int(self.x + self.width // 2),
            int(self.y + self.height // 2),
        ))
        surf.blit(rot, r)

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox dell'asteroide.

        La hitbox e' ridotta rispetto allo sprite per evitare collisioni
        'ingiuste' con le estremita' trasparenti della texture ruotata.
        Shrink: 8px per lato.
        """
        shrink = 8
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width - shrink * 2,
            self.height - shrink * 2,
        )
