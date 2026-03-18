"""
Classi Laser e AngledLaser -- proiettili del gioco.

I laser possono essere sparati dal giocatore (verso l'alto) o dai nemici
(verso il basso). Gli sprite vengono pre-scalati in Assets.load() per
evitare il costoso pygame.transform.scale() ad ogni frame.

Supporta anche laser con velocita' orizzontale (``vx``) per i pattern
di sparo avanzati dei boss.
"""

import math
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, CYAN
from core.assets import Assets


class Laser:
    """Proiettile laser dritto (giocatore o nemico).

    Supporta velocita' opzionale sull'asse X per pattern diagonali.

    Args:
        x, y:     Posizione iniziale (angolo superiore sinistro).
        speed:    Velocita' verticale (negativa = su, positiva = giu').
        color:    Colore fallback se lo sprite non e' disponibile.
        is_enemy: True se appartiene a un nemico.
        sprite:   Surface pygame pre-caricata (opzionale).
        vx:       Velocita' orizzontale (0 = dritto). Per i boss.
    """

    WIDTH  = 20
    HEIGHT = 40

    def __init__(self, x, y, speed, color=CYAN, is_enemy=False,
                 sprite=None, vx: float = 0.0):
        self.x = x
        self.y = y
        self.speed = speed
        self.vx = vx
        self.color = color
        self.is_enemy = is_enemy
        self.active = True

        if sprite:
            self.image = sprite
        elif is_enemy:
            self.image = Assets.enemy_laser_sprite_scaled
        else:
            self.image = None

    def update(self) -> None:
        """Muove il laser nella sua direzione e lo disattiva se fuori schermo."""
        self.y += self.speed
        self.x += self.vx
        margin = 50
        if self.y < -margin or self.y > SCREEN_HEIGHT + margin:
            self.active = False
        if self.x < -margin or self.x > SCREEN_WIDTH + margin:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna il laser usando lo sprite pre-scalato (o fallback rettangolo)."""
        if self.image:
            surface.blit(self.image, (int(self.x), int(self.y)))
        else:
            pygame.draw.rect(
                surface, self.color,
                (int(self.x), int(self.y), self.WIDTH, self.HEIGHT))

    def get_rect(self) -> pygame.Rect:
        """Restituisce la hitbox del laser."""
        shrink_x = 4
        return pygame.Rect(
            self.x + shrink_x,
            self.y,
            self.WIDTH - shrink_x * 2,
            self.HEIGHT,
        )


class AngledLaser(Laser):
    """Laser angolato usato dal power-up arma (sparo triplo).

    Si muove lungo una traiettoria diagonale definita dall'angolo.

    Args:
        x, y:       Posizione iniziale.
        base_speed: Velocita' base del laser.
        angle_deg:  Angolo in gradi rispetto alla verticale.
        color:      Colore fallback.
        sprite:     Surface pre-caricata (opzionale).
    """

    def __init__(self, x, y, base_speed, angle_deg, color=CYAN, sprite=None):
        super().__init__(x, y, base_speed, color, is_enemy=False, sprite=sprite)
        rad = math.radians(angle_deg)
        self.vx = -base_speed * math.sin(rad)
        self.vy =  base_speed * math.cos(rad)
        self.angle_deg = angle_deg

    def update(self) -> None:
        """Muove il laser lungo la traiettoria angolata."""
        self.x += self.vx
        self.y += self.vy
        margin = 50
        if self.y < -margin or self.y > SCREEN_HEIGHT + margin:
            self.active = False
        if self.x < -margin or self.x > SCREEN_WIDTH + margin:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna il laser angolato."""
        if self.image:
            surface.blit(self.image, (int(self.x), int(self.y)))
        else:
            pygame.draw.rect(
                surface, self.color,
                (int(self.x), int(self.y), self.WIDTH, self.HEIGHT))
