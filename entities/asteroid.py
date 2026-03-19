"""
Asteroide -- sprite con scia pixel-art e corridoio sicuro garantito.

Gli asteroidi cadono dall'alto verso il basso con rotazione e una
scia particellare luminosa. Le particelle usano BLEND_ADD per un
effetto fuoco/calore.

Un registro globale ``_active_x`` previene la sovrapposizione
orizzontale tra asteroidi attivi. Durante la pioggia di meteore, il
sistema garantisce almeno un corridoio di ``SAFE_CORRIDOR_W`` pixel
libero da asteroidi, così il giocatore ha sempre un percorso praticabile.
"""

import random
import math
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, ASTEROID_SIZE
from core.assets import Assets

# ---------------------------------------------------------------------------
# Registro globale delle posizioni X degli asteroidi attivi.
# ---------------------------------------------------------------------------
_active_x: list[float] = []
_MIN_GAP = 90  # distanza orizzontale minima tra asteroidi (px)

# Larghezza minima del corridoio sicuro garantito durante la pioggia
SAFE_CORRIDOR_W = 100

# Parametri spritestrip scia
_N_FRAMES = 12
_FW = 32


def _safe_x(w: int) -> float:
    """Calcola una posizione X sicura per un nuovo asteroide.

    Prova piazzamento casuale che rispetti la distanza minima da tutti
    gli asteroidi attivi E non blocchi completamente l'ultimo corridoio
    sicuro. Ripiego su piazzamento basato su colonne dopo 30 tentativi
    falliti.

    Args:
        w: Larghezza asteroide in pixel.

    Returns:
        Posizione X come float, o -1 se lo spawn bloccherebbe il corridoio.
    """
    corridor = _find_largest_gap()

    for _ in range(30):
        x = random.randint(20, SCREEN_WIDTH - w - 20)

        if not all(abs(x - ox) >= _MIN_GAP for ox in _active_x):
            continue

        if _would_block_corridor(x, w, corridor):
            continue

        return float(x)

    # Fallback: piazzamento basato su colonne
    cols = 6
    cw = (SCREEN_WIDTH - 40) // cols
    counts = [0] * cols
    for ox in _active_x:
        c = int((ox - 20) / cw)
        if 0 <= c < cols:
            counts[c] += 1

    sorted_cols = sorted(range(cols), key=lambda i: counts[i])

    for best in sorted_cols:
        x = float(20 + best * cw + random.randint(0, max(0, cw - w)))
        if not _would_block_corridor(x, w, corridor):
            return x

    return -1.0


def _find_largest_gap() -> tuple[float, float]:
    """Trova il gap orizzontale più largo tra gli asteroidi attivi.

    Returns:
        Tupla (gap_start, gap_end) del corridoio più largo.
        Restituisce l'intera larghezza schermo se non ci sono asteroidi attivi.
    """
    if not _active_x:
        return (0.0, float(SCREEN_WIDTH))

    half_w = ASTEROID_SIZE / 2
    intervals = sorted(
        (x - half_w, x + ASTEROID_SIZE + half_w) for x in _active_x)

    # Unisci intervalli sovrapposti
    merged: list[tuple[float, float]] = [intervals[0]]
    for start, end in intervals[1:]:
        if start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Trova il gap più largo
    best_gap = (0.0, merged[0][0])
    for i in range(len(merged) - 1):
        gap_start = merged[i][1]
        gap_end   = merged[i + 1][0]
        if (gap_end - gap_start) > (best_gap[1] - best_gap[0]):
            best_gap = (gap_start, gap_end)

    final_start = merged[-1][1]
    final_end   = float(SCREEN_WIDTH)
    if (final_end - final_start) > (best_gap[1] - best_gap[0]):
        best_gap = (final_start, final_end)

    return best_gap


def _would_block_corridor(
    x: float, w: int, corridor: tuple[float, float]
) -> bool:
    """Controlla se piazzare un asteroide a ``x`` bloccherebbe il corridoio.

    Args:
        x:        Posizione X candidata per il nuovo asteroide.
        w:        Larghezza asteroide.
        corridor: (start, end) corrente del gap più largo.

    Returns:
        True se lo spawn qui restringerebbe il corridoio sotto SAFE_CORRIDOR_W.
    """
    gap_w = corridor[1] - corridor[0]
    if gap_w <= SAFE_CORRIDOR_W:
        return True

    half = ASTEROID_SIZE / 2
    ast_left  = x - half
    ast_right = x + w + half

    if ast_right <= corridor[0] or ast_left >= corridor[1]:
        return False

    left_gap  = max(0, ast_left - corridor[0])
    right_gap = max(0, corridor[1] - ast_right)
    best_remaining = max(left_gap, right_gap)

    return best_remaining < SAFE_CORRIDOR_W


def clear_registry() -> None:
    """Pulisce il registro globale delle posizioni asteroidi."""
    _active_x.clear()


class _Particle:
    """Singola particella scia luminosa per un asteroide.

    Le particelle vanno leggermente verso l'alto (simulando fumo caldo),
    avanzano attraverso i frame dello spritesheet e svaniscono gradualmente.
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
        self.vy    = random.uniform(-1.0, -0.15)
        self.frame = float(random.randint(0, 2))
        self.alpha = random.randint(200, 255)
        self.sz    = random.uniform(0.5, 1.2)
        self.alive = True

    def update(self) -> None:
        """Aggiorna posizione, progressione frame e opacità."""
        self.x += self.vx
        self.y += self.vy
        self.frame += 0.4
        self.alpha -= 16
        self.sz = max(0, self.sz - 0.02)
        if self.alpha <= 0 or self.sz < 0.05 or self.frame >= _N_FRAMES:
            self.alive = False

    def draw(self, surf: pygame.Surface,
             frames: list[pygame.Surface]) -> None:
        """Disegna la particella usando il frame dello spritesheet scia.

        Crea una copia del frame con alpha per-pixel per evitare
        artefatti rettangolari quando si usa set_alpha() su Surface
        condivise tra piu particelle.

        Args:
            surf:   Surface di destinazione.
            frames: Lista frame spritesheet scia.
        """
        fi = min(int(self.frame), _N_FRAMES - 1)
        src = frames[fi]
        alpha_val = max(0, min(255, int(self.alpha)))
        if alpha_val < 20:
            return  # Salta particelle quasi invisibili
        sz = max(2, int(_FW * self.sz))
        # Scala solo se la dimensione differisce significativamente dalla sorgente
        if abs(sz - _FW) > 2:
            scaled = pygame.transform.scale(src, (sz, sz))
        else:
            scaled = src
            sz = _FW
        # Crea copia con alpha per-pixel per evitare rettangoli
        # causati da set_alpha() su Surface condivise
        tmp = pygame.Surface((sz, sz), pygame.SRCALPHA)
        tmp.blit(scaled, (0, 0))
        if alpha_val < 255:
            arr = pygame.surfarray.pixels_alpha(tmp)
            arr[:] = (arr.astype(int) * alpha_val // 255).clip(0, 255)
            del arr
        surf.blit(
            tmp,
            (int(self.x - sz // 2), int(self.y - sz // 2)),
            special_flags=pygame.BLEND_ADD,
        )


class Asteroid:
    """Asteroide in caduta con rotazione e scia luminosa.

    Gli asteroidi sono indistruttibili (i laser non li colpiscono).
    Collisione con il giocatore = morte istantanea (ignora lo scudo).

    Attributi di classe:
        MIN_SPEED: Velocità minima di caduta.
        MAX_SPEED: Velocità massima di caduta (limite sicurezza).
    """

    MIN_SPEED = 1.8
    MAX_SPEED = 3.2

    def __init__(self):
        """Crea un nuovo asteroide sopra lo schermo in una posizione X sicura.

        Se il sistema corridoio sicuro impedisce lo spawn (restituisce x == -1),
        l'asteroide viene creato ma immediatamente disattivato.
        """
        self.width  = ASTEROID_SIZE
        self.height = ASTEROID_SIZE
        x = _safe_x(self.width)
        if x < 0:
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
        """Aggiorna posizione, rotazione e particelle scia."""
        if not self.active:
            return

        self.y += self.fall_speed
        self.angle = (self.angle + self.rot_speed) % 360

        # Genera particelle scia (conteggio ridotto per prestazioni)
        cx = self.x + self.width // 2
        cy = self.y + self.height // 2
        for _ in range(random.randint(2, 4)):
            self.trail.append(_Particle(cx, cy))

        # Aggiorna e elimina particelle morte in-place
        alive_count = 0
        for p in self.trail:
            p.update()
            if p.alive:
                self.trail[alive_count] = p
                alive_count += 1
        del self.trail[alive_count:]

        # Disattiva quando fuori dal fondo dello schermo
        if self.y > SCREEN_HEIGHT + 60:
            self.active = False
            self._dereg()

    def _dereg(self) -> None:
        """Rimuove la X di questo asteroide dal registro globale."""
        try:
            _active_x.remove(self.x)
        except ValueError:
            pass

    def deactivate(self) -> None:
        """Disattiva e de-registra esplicitamente questo asteroide."""
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

        # Disegna la scia dietro l'asteroide
        if Assets.trail_frames:
            for p in self.trail:
                p.draw(surf, Assets.trail_frames)

        # Disegna lo sprite asteroide ruotato
        rot = pygame.transform.rotate(Assets.asteroid_sprite, self.angle)
        rect = rot.get_rect(center=(
            int(self.x + self.width // 2),
            int(self.y + self.height // 2),
        ))
        surf.blit(rot, rect)

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox (ridotta di 8px per lato per equità)."""
        shrink = 8
        return pygame.Rect(
            self.x + shrink,
            self.y + shrink,
            self.width - shrink * 2,
            self.height - shrink * 2,
        )
