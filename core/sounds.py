"""
Procedural sound effects and background music generation.

All sounds are generated at runtime without external audio files.
Background music is a procedurally generated space ambient loop.
"""

import math
import random
import pygame


def _generate_sound(
    frequency: float, duration_ms: int, volume: float = 0.3, wave_type: str = "square"
) -> pygame.mixer.Sound:
    """Generate a single procedural sound effect.

    Args:
        frequency:   Frequency in Hz.
        duration_ms: Duration in milliseconds.
        volume:      Volume (0.0 - 1.0).
        wave_type:   Wave type ('square', 'sine', 'noise', 'sweep').

    Returns:
        A ``pygame.mixer.Sound`` object.
    """
    sample_rate = 22050
    n_samples = int(sample_rate * duration_ms / 1000)
    buf = bytearray(n_samples * 2)
    max_amp = int(32767 * volume)

    for i in range(n_samples):
        t = i / sample_rate

        if wave_type == "square":
            val = max_amp if math.sin(2 * math.pi * frequency * t) >= 0 else -max_amp
        elif wave_type == "sine":
            val = int(max_amp * math.sin(2 * math.pi * frequency * t))
        elif wave_type == "noise":
            val = random.randint(-max_amp, max_amp)
        elif wave_type == "sweep":
            f = frequency * (1 - 0.8 * i / n_samples)
            val = int(max_amp * math.sin(2 * math.pi * f * t))
        else:
            val = 0

        # Fade out in the last 20%
        fade_start = int(n_samples * 0.8)
        if i > fade_start:
            fade = 1.0 - (i - fade_start) / (n_samples - fade_start)
            val = int(val * fade)

        val = max(-32768, min(32767, val))
        buf[i * 2] = val & 0xFF
        buf[i * 2 + 1] = (val >> 8) & 0xFF

    return pygame.mixer.Sound(buffer=bytes(buf))


def generate_background_music(
    duration_ms: int = 8000, volume: float = 0.12
) -> pygame.mixer.Sound:
    """Generate a space ambient music loop.

    Overlays three layers:
    - Pulsating bass drone (low-frequency sine wave)
    - Slow pentatonic arpeggio
    - Filtered cosmic noise (shimmer)

    Args:
        duration_ms: Loop duration in ms (default 8 seconds).
        volume:      Overall volume (kept low so it doesn't drown SFX).

    Returns:
        A ``pygame.mixer.Sound`` object.
    """
    sample_rate = 22050
    n = int(sample_rate * duration_ms / 1000)
    buf = bytearray(n * 2)

    # Minor pentatonic scale (Hz) for the arpeggio
    pentatonic = [
        65.4, 77.8, 87.3, 98.0, 116.5,
        130.8, 155.6, 174.6, 196.0, 233.1,
    ]
    arp_notes = [pentatonic[i % len(pentatonic)] for i in range(12)]
    note_dur = n // len(arp_notes)

    max_amp = int(32767 * volume)

    for i in range(n):
        t = i / sample_rate
        val = 0

        # --- Layer 1: pulsating bass drone ---
        drone_freq = 55.0  # A1
        lfo = 0.6 + 0.4 * math.sin(2 * math.pi * 0.15 * t)
        val += int(max_amp * 0.45 * lfo * math.sin(2 * math.pi * drone_freq * t))
        val += int(max_amp * 0.15 * lfo * math.sin(2 * math.pi * drone_freq * 2 * t))

        # --- Layer 2: pentatonic arpeggio ---
        note_idx = (i // note_dur) % len(arp_notes)
        note_freq = arp_notes[note_idx]
        note_phase = (i % note_dur) / note_dur
        if note_phase < 0.05:
            env = note_phase / 0.05
        else:
            env = 1.0 - (note_phase - 0.05) * 0.9
        env = max(0.0, env)
        val += int(max_amp * 0.20 * env * math.sin(2 * math.pi * note_freq * t))

        # --- Layer 3: cosmic shimmer ---
        shimmer_lfo = 0.3 + 0.7 * abs(math.sin(2 * math.pi * 0.07 * t))
        shimmer = random.randint(-max_amp, max_amp) * 0.04 * shimmer_lfo
        val += int(shimmer)

        # Fade in/out at loop boundaries (prevent clicks)
        fade_len = int(sample_rate * 0.3)
        if i < fade_len:
            val = int(val * i / fade_len)
        elif i > n - fade_len:
            val = int(val * (n - i) / fade_len)

        val = max(-32768, min(32767, val))
        buf[i * 2] = val & 0xFF
        buf[i * 2 + 1] = (val >> 8) & 0xFF

    return pygame.mixer.Sound(buffer=bytes(buf))


def create_sounds() -> dict[str, pygame.mixer.Sound]:
    """Create and return the complete sound effects dictionary.

    Returns:
        Mapping of sound name to ``pygame.mixer.Sound`` object.
    """
    sounds = {
        # -- Player --
        "laser":       _generate_sound(880, 120, 0.2, "square"),
        "player_hit":  _generate_sound(350, 200, 0.3, "noise"),

        # -- Enemies --
        "enemy_laser": _generate_sound(440, 150, 0.15, "square"),
        "explosion":   _generate_sound(200, 300, 0.3, "noise"),

        # -- Boss --
        "boss_warning":  _generate_sound(150, 600, 0.4, "square"),
        "boss_laser":    _generate_sound(220, 200, 0.25, "square"),
        "boss_hit":      _generate_sound(500, 100, 0.2, "noise"),
        "boss_defeated": _generate_sound(600, 1200, 0.35, "sweep"),

        # -- Power-ups --
        "carrier_hit":       _generate_sound(600, 80, 0.2, "noise"),
        "carrier_destroyed": _generate_sound(400, 400, 0.3, "sweep"),
        "powerup_collect":   _generate_sound(1000, 300, 0.3, "sine"),
        "shield_active":     _generate_sound(500, 200, 0.2, "sine"),
        "shield_break":      _generate_sound(250, 400, 0.25, "noise"),

        # -- Asteroids --
        "asteroid_warning":      _generate_sound(120, 400, 0.2, "square"),
        "asteroid_rain_warning": _generate_sound(100, 800, 0.4, "square"),

        # -- UI / Menu --
        "game_over": _generate_sound(300, 800, 0.3, "sweep"),
        "select":    _generate_sound(660, 80, 0.15, "sine"),
        "confirm":   _generate_sound(880, 100, 0.2, "sine"),
        "unlock":    _generate_sound(1200, 400, 0.25, "sine"),

        # -- Pause --
        "pause":  _generate_sound(740, 90, 0.15, "sine"),
        "resume": _generate_sound(880, 90, 0.15, "sine"),

        # -- Bomb --
        "bomb":   _generate_sound(150, 500, 0.35, "noise"),
    }
    return sounds
