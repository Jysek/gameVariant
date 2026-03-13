#!/usr/bin/env python3
"""
Space Shooter - Infinite Survival
Progetto di: Ceccariglia Emanuele e Andrea Cestelli - ITSUmbria 2026

Un videogioco 2D arcade ispirato a Space Invaders.
Sviluppato in Python con Pygame.

Entry point principale del gioco.
"""

import pygame
from core.assets import Assets
from game.game import Game


def main():
    """Inizializza Pygame, carica gli asset e avvia il gioco."""
    pygame.init()
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

    # Avvia il gioco (Assets.load() viene chiamato dentro Game.__init__
    # dopo display.set_mode(), così convert_alpha() funziona correttamente)
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
