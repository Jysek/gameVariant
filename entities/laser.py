"""
Classi Laser e AngledLaser - proiettili del gioco.

Miglioramenti rispetto alla versione originale:
- Gli sprite vengono pre-scalati in Assets.load() e riusati,
  eliminando il costoso pygame.transform.scale() ad ogni frame.
"""

import math
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, CYAN
from core.assets import Assets


class Laser:
    """Proiettile laser (giocatore o nemico).

    Args:
        x, y: Posizione iniziale (angolo superiore sinistro).
        speed: Velocità verticale (negativa = verso l'alto, positiva = verso il basso).
        color: Colore fallback se lo sprite non è disponibile.
        is_enemy: True se appartiene a un nemico.
        sprite: Surface pygame pre-caricata (opzionale).
    """

    # Dimensioni logiche di ogni laser (usate per la hitbox)
    WIDTH  = 20
    HEIGHT = 40

    def __init__(self, x, y, speed, color=CYAN, is_enemy=False, sprite=None):
        self.x = x
        self.y = y
        self.speed = speed
        self.color = color
        self.is_enemy = is_enemy
        # Usa lo sprite fornito, oppure quello nemico pre-scalato da Assets
        self.image = sprite if sprite else (Assets.enemy_laser_sprite_scaled if is_enemy else None)
        self.active = True

    def update(self) -> None:
        """Muove il laser nella sua direzione e lo disattiva se fuori schermo."""
        self.y += self.speed
        if self.y < -20 or self.y > SCREEN_HEIGHT + 20:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna il laser usando lo sprite pre-scalato (o fallback rettangolo)."""
        if self.image:
            # PERFORMANCE: lo sprite è già alla dimensione corretta, nessun transform
            surface.blit(self.image, (int(self.x), int(self.y)))
        else:
            pygame.draw.rect(surface, self.color, (self.x, self.y, self.WIDTH, self.HEIGHT))

    def get_rect(self) -> pygame.Rect:
        """Rettangolo di collisione."""
        return pygame.Rect(self.x, self.y, self.WIDTH, self.HEIGHT)


class AngledLaser(Laser):
    """Laser angolato usato dal power-up arma (sparo triplo).

    Si muove nella direzione indicata dall'angolo (in gradi).

    Args:
        angle_deg: Angolo in gradi rispetto alla verticale
                   (negativo = sinistra, positivo = destra).
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
        if self.y < -40 or self.y > SCREEN_HEIGHT + 40:
            self.active = False
        if self.x < -40 or self.x > SCREEN_WIDTH + 40:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna il laser angolato (gli sprite sono già orientati correttamente)."""
        if self.image:
            surface.blit(self.image, (int(self.x), int(self.y)))
        else:
            pygame.draw.rect(surface, self.color, (self.x, self.y, self.WIDTH, self.HEIGHT))
