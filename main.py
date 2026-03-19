#!/usr/bin/env python3
"""
Space Shooter - Infinite Survival
Project by: Ceccariglia Emanuele & Andrea Cestelli - ITSUmbria 2026

A 2D arcade shooter inspired by Space Invaders.
Developed in Python with Pygame.

This is the main entry point of the game.
"""

import pygame
from core.assets import Assets
from game.game import Game


def main():
    """Initialize Pygame, load assets, and start the game loop."""
    pygame.init()
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

    # Start the game (Assets.load() is called inside Game.__init__
    # after display.set_mode(), so convert_alpha() works correctly)
    game = Game()
    game.run()


if __name__ == "__main__":
    main()
