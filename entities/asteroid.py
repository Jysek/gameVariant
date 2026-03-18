"""
Asteroid -- sprite con scia pixel-art e percorso sicuro garantito.

Gli asteroidi cadono dall'alto verso il basso con rotazione e scia di
particelle luminose.  Le particelle usano ``BLEND_ADD`` per un effetto
fuoco/calore.

Un registro globale ``_active_x`` previene la sovrapposizione orizzontale
tra asteroidi attivi.  Durante la pioggia, il sistema garantisce che
esista **sempre** almeno un corridoio di larghezza ``SAFE_CORRIDOR_W``
pixel libero da asteroidi, cosi' il giocatore ha sempre un percorso
percorribile.
"""

import random
import math
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ASTEROID_SIZE
from core.assets import Assets

# ---------------------------------------------------------------------------
# Registro globale posizioni X degli asteroidi attivi.
# ---------------------------------------------------------------------------
_active_x: list[float] = []
_MIN_GAP = 90   # distanza minima orizzontale tra asteroidi (px)

# Larghezza minima del corridoio sicuro garantito durante la pioggia
SAFE_CORRIDOR_W = 100

# Parametri spritesheet scia
_N_FRAMES = 12
_FW = 32


def _safe_x(w: int) -> float:
    """Calcola una posizione X sicura per un nuovo asteroide.

    Tenta un posizionamento casuale che rispetti la distanza minima da
    tutti gli asteroidi attivi **e** che non ostruisca completamente
    l'ultimo corridoio sicuro.  Se fallisce dopo 30 tentativi, usa un
    approccio a colonne scegliendo quella meno popolata.

    Args:
        w: Larghezza dell'asteroide in pixel.

    Returns:
        Posizione X come float, oppure ``-1`` se il posizionamento
        bloccherebbe il corridoio sicuro (il chiamante deve scartare
        lo spawn).
    """
    corridor = _find_largest_gap()

    for _ in range(30):
        x = random.randint(20, SCREEN_WIDTH - w - 20)

        # Rispetta distanza minima dagli asteroidi attivi
        if not all(abs(x - ox) >= _MIN_GAP for ox in _active_x):
            continue

        # Verifica che il corridoio sicuro non venga chiuso
        if _would_block_corridor(x, w, corridor):
            continue

        return float(x)

    # Fallback: suddivisione in colonne
    cols = 6
    cw = (SCREEN_WIDTH - 40) // cols
    counts = [0] * cols
    for ox in _active_x:
        c = int((ox - 20) / cw)
        if 0 <= c < cols:
            counts[c] += 1

    # Ordina le colonne per numero di asteroidi (meno popolate prima)
    sorted_cols = sorted(range(cols), key=lambda i: counts[i])

    for best in sorted_cols:
        x = float(20 + best * cw + random.randint(0, max(0, cw - w)))
        if not _would_block_corridor(x, w, corridor):
            return x

    # Se qualsiasi posizione bloccherebbe il corridoio, rinuncia allo spawn
    return -1.0


def _find_largest_gap() -> tuple[float, float]:
    """Trova il gap orizzontale piu' ampio tra gli asteroidi attivi.

    Returns:
        Tupla ``(gap_start, gap_end)`` del corridoio piu' largo.
        Se non ci sono asteroidi, restituisce l'intero schermo.
    """
    if not _active_x:
        return (0.0, float(SCREEN_WIDTH))

    # Crea intervalli occupati (con margine asteroide)
    half_w = ASTEROID_SIZE / 2
    intervals = sorted((x - half_w, x + ASTEROID_SIZE + half_w) for x in _active_x)

    # Unisci intervalli sovrapposti
    merged: list[tuple[float, float]] = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Trova il gap piu' ampio
    best_gap = (0.0, merged[0][0])  # gap iniziale
    for i in range(len(merged) - 1):
        gap_start = merged[i][1]
        gap_end   = merged[i + 1][0]
        if (gap_end - gap_start) > (best_gap[1] - best_gap[0]):
            best_gap = (gap_start, gap_end)

    # Gap finale
    final_start = merged[-1][1]
    final_end   = float(SCREEN_WIDTH)
    if (final_end - final_start) > (best_gap[1] - best_gap[0]):
        best_gap = (final_start, final_end)

    return best_gap


def _would_block_corridor(x: float, w: int,
                          corridor: tuple[float, float]) -> bool:
    """Verifica se piazzare un asteroide a ``x`` chiuderebbe il corridoio.

    Un corridoio e' considerato 'bloccato' se la sua larghezza residua
    scenderebbe sotto ``SAFE_CORRIDOR_W``.

    Args:
        x:        Posizione X candidata per il nuovo asteroide.
        w:        Larghezza asteroide.
        corridor: Tupla ``(start, end)`` del corridoio corrente.

    Returns:
        ``True`` se lo spawn bloccherebbe il corridoio sicuro.
    """
    gap_w = corridor[1] - corridor[0]
    if gap_w <= SAFE_CORRIDOR_W:
        # Il corridoio e' gia' stretto: non peggiorare
        return True

    half = ASTEROID_SIZE / 2
    ast_left  = x - half
    ast_right = x + w + half

    # L'asteroide si sovrappone al corridoio?
    if ast_right <= corridor[0] or ast_left >= corridor[1]:
        return False  # fuori dal corridoio: ok

    # Stima conservativa: il corridoio piu' largo rimasto
    left_gap  = max(0, ast_left - corridor[0])
    right_gap = max(0, corridor[1] - ast_right)
    best_remaining = max(left_gap, right_gap)

    return best_remaining < SAFE_CORRIDOR_W


def clear_registry() -> None:
    """Pulisce il registro globale degli asteroidi attivi."""
    _active_x.clear()


class _Particle:
    """Singola particella della scia luminosa di un asteroide.

    Le particelle risalgono leggermente (simulando fumo caldo), avanzano
    nei frame dello spritesheet e si spengono gradualmente.
    """
    __slots__ = ('x', 'y', 'vx', 'vy', 'frame', 'alpha', 'sz', 'alive')

    def __init__(self, cx: float, cy: float):
        """Crea una particella vicino al centro dell'asteroide.

        Args:
            cx: Centro X dell'asteroide (pixel).
            cy: Centro Y dell'asteroide (pixel).
        """
        self.x     = cx + random.uniform(-10, 10)
        self.y     = cy + random.uniform(-6, 6)
        self.vx    = random.uniform(-0.3, 0.3)
        self.vy    = random.uniform(-1.0, -0.15)   # risale (fumo caldo)
        self.frame = float(random.randint(0, 2))
        self.alpha = random.randint(200, 255)
        self.sz    = random.uniform(0.5, 1.2)
        self.alive = True

    def update(self) -> None:
        """Aggiorna posizione, frame e opacita' della particella."""
        self.x += self.vx
        self.y += self.vy
        self.frame += 0.4
        self.alpha -= 16
        self.sz = max(0, self.sz - 0.02)
        if self.alpha <= 0 or self.sz < 0.05 or self.frame >= _N_FRAMES:
            self.alive = False

    def draw(self, surf: pygame.Surface, frames: list[pygame.Surface]) -> None:
        """Disegna la particella usando il frame dello spritesheet.

        Args:
            surf:   Surface di destinazione.
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
    Collisione con il giocatore = morte istantanea (ignora scudo).

    Attributi di classe:
        MIN_SPEED: Velocita' minima di caduta.
        MAX_SPEED: Velocita' massima di caduta (cap sicurezza).
    """

    MIN_SPEED = 1.8
    MAX_SPEED = 3.2

    def __init__(self):
        """Crea un nuovo asteroide sopra lo schermo in una posizione X sicura.

        Se il sistema di corridoio sicuro impedisce lo spawn (restituisce
        ``x == -1``), l'asteroide viene creato ma immediatamente disattivato.
        """
        self.width  = ASTEROID_SIZE
        self.height = ASTEROID_SIZE
        x = _safe_x(self.width)
        if x < 0:
            # Corridoio sicuro bloccato: l'asteroide non viene spawnato
            self.x = 0.0
            self.y = -999.0
            self.active = False
            self.fall_speed = 0.0
            self.angle = 0.0
            self.rot_speed = 0
            self.trail: list[_Particle] = []
            return

        self.x = x
        self.y = float(-self.height - random.randint(0, 40))
        self.active = True
        _active_x.append(self.x)

        self.fall_speed = random.uniform(self.MIN_SPEED, self.MAX_SPEED)
        self.angle     = 0.0
        self.rot_speed = random.choice([-3, -2, -1, 1, 2, 3])
        self.trail: list[_Particle] = []

    def update(self) -> None:
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

        # Aggiorna e pulisci particelle morte
        for p in self.trail:
            p.update()
        self.trail = [p for p in self.trail if p.alive]

        # Disattiva se uscito dal basso dello schermo
        if self.y > SCREEN_HEIGHT + 60:
            self.active = False
            self._dereg()

    def _dereg(self) -> None:
        """Rimuove la posizione X dal registro globale."""
        try:
            _active_x.remove(self.x)
        except ValueError:
            pass

    def deactivate(self) -> None:
        """Disattiva esplicitamente l'asteroide e lo rimuove dal registro."""
        if self.active:
            self.active = False
            self._dereg()

    def draw(self, surf: pygame.Surface) -> None:
        """Disegna l'asteroide con scia luminosa e rotazione.

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
        rect = rot.get_rect(center=(
            int(self.x + self.width // 2),
            int(self.y + self.height // 2),
        ))
        surf.blit(rot, rect)

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox dell'asteroide (ridotta per fairness).

        Shrink: 8 px per lato.
        """
        shrink = 8
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width - shrink * 2,
            self.height - shrink * 2,
        )
