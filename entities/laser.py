"""
Classi Laser e AngledLaser -- proiettili di gioco.

I laser possono essere sparati dal giocatore (verso l'alto) o dai
nemici/boss (verso il basso). Gli sprite sono pre-scalati in
Assets.load() per evitare scaling costoso ad ogni frame.

Supporta velocità orizzontale (``vx``) per pattern di sparo avanzati dei boss.
I laser nemici usano lo sprite orientato verso il basso; se non è
disponibile uno sprite, viene disegnato un piccolo rettangolo colorato
come fallback.

Le hitbox dei laser sono state rimosse: le collisioni usano
direttamente il rettangolo dello sprite senza restringimenti.
"""

import math
import pygame

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, CYAN


class Laser:
    """Proiettile laser rettilineo (giocatore o nemico).

    Supporta velocità orizzontale opzionale per pattern diagonali dei boss.

    Args:
        x, y:     Posizione iniziale (angolo in alto a sinistra).
        speed:    Velocità verticale (negativa = su, positiva = giù).
        color:    Colore fallback se lo sprite non è disponibile.
        is_enemy: True se questo laser appartiene a un nemico/boss.
        sprite:   Surface Pygame pre-caricata (opzionale).
        vx:       Velocità orizzontale (0 = dritto). Usato per pattern boss.
    """

    WIDTH  = 20
    HEIGHT = 40

    def __init__(
        self, x: float, y: float, speed: float, color: tuple = CYAN,
        is_enemy: bool = False, sprite: pygame.Surface = None,
        vx: float = 0.0,
    ):
        self.x = x
        self.y = y
        self.speed = speed
        self.vx = vx
        self.color = color
        self.is_enemy = is_enemy
        self.active = True

        # Assegna lo sprite: priorità parametro > sprite nemico di default > None
        if sprite:
            self.image = sprite
        elif is_enemy:
            from core.assets import Assets
            self.image = Assets.enemy_laser_sprite_scaled
        else:
            self.image = None

    def update(self) -> None:
        """Muove il laser lungo la sua traiettoria; disattiva se fuori schermo."""
        self.y += self.speed
        self.x += self.vx
        margin = 50
        if self.y < -margin or self.y > SCREEN_HEIGHT + margin:
            self.active = False
        if self.x < -margin or self.x > SCREEN_WIDTH + margin:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna il laser usando il suo sprite pre-scalato.

        Se non è disponibile uno sprite, disegna un piccolo rettangolo
        colorato come fallback minimale. Nessuna hitbox visiva.
        """
        if self.image:
            surface.blit(self.image, (int(self.x), int(self.y)))
        else:
            # Rettangolo colorato fallback minimale (senza glow)
            r, g, b = self.color[:3]
            pygame.draw.rect(
                surface, (r, g, b),
                (int(self.x) + 6, int(self.y), self.WIDTH - 12, self.HEIGHT),
            )

    def get_rect(self) -> pygame.Rect:
        """Restituisce il rettangolo di collisione del laser.

        Usa il rettangolo completo dello sprite senza restringimenti
        (le hitbox visive dei laser sono state rimosse).
        """
        return pygame.Rect(
            int(self.x), int(self.y),
            self.WIDTH, self.HEIGHT,
        )


class AngledLaser(Laser):
    """Laser angolato usato dal power-up sparo triplo.

    Si muove lungo una traiettoria diagonale definita dall'angolo.

    Args:
        x, y:       Posizione iniziale.
        base_speed: Velocità laser di base.
        angle_deg:  Angolo in gradi dalla verticale.
        color:      Colore fallback.
        sprite:     Surface pre-caricata (opzionale).
    """

    def __init__(
        self, x: float, y: float, base_speed: float, angle_deg: float,
        color: tuple = CYAN, sprite: pygame.Surface = None,
    ):
        super().__init__(x, y, base_speed, color, is_enemy=False, sprite=sprite)
        rad = math.radians(angle_deg)
        self.vx = -base_speed * math.sin(rad)
        self.vy = base_speed * math.cos(rad)
        self.angle_deg = angle_deg

    def update(self) -> None:
        """Muove il laser lungo la sua traiettoria angolata."""
        self.x += self.vx
        self.y += self.vy
        margin = 50
        if self.y < -margin or self.y > SCREEN_HEIGHT + margin:
            self.active = False
        if self.x < -margin or self.x > SCREEN_WIDTH + margin:
            self.active = False

    def draw(self, surface: pygame.Surface) -> None:
        """Disegna il laser angolato usando il suo sprite o un fallback minimale."""
        if self.image:
            surface.blit(self.image, (int(self.x), int(self.y)))
        else:
            r, g, b = self.color[:3]
            pygame.draw.rect(
                surface, (r, g, b),
                (int(self.x) + 6, int(self.y), self.WIDTH - 12, self.HEIGHT),
            )
