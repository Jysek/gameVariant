"""
Procedural sound effects and background music generation.

All sounds are generated at runtime without external audio files.
Background music is a procedurally generated space ambient loop.

Uses numpy for fast sample generation instead of per-sample Python loops.
"""

import math
import random
import numpy as np
import pygame


def _generate_sound(
    frequency: float, duration_ms: int, volume: float = 0.3, wave_type: str = "square"
) -> pygame.mixer.Sound:
    """Generate a single procedural sound effect using numpy.

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
    max_amp = 32767 * volume

    t = np.arange(n_samples, dtype=np.float64) / sample_rate

    if wave_type == "square":
        vals = np.where(np.sin(2 * np.pi * frequency * t) >= 0, max_amp, -max_amp)
    elif wave_type == "sine":
        vals = max_amp * np.sin(2 * np.pi * frequency * t)
    elif wave_type == "noise":
        vals = np.random.randint(-int(max_amp), int(max_amp) + 1, n_samples).astype(np.float64)
    elif wave_type == "sweep":
        f = frequency * (1 - 0.8 * np.arange(n_samples) / n_samples)
        phase = np.cumsum(2 * np.pi * f / sample_rate)
        vals = max_amp * np.sin(phase)
    else:
        vals = np.zeros(n_samples)

    # Fade out in the last 20%
    fade_start = int(n_samples * 0.8)
    fade_len = n_samples - fade_start
    if fade_len > 0:
        fade = np.ones(n_samples)
        fade[fade_start:] = 1.0 - np.arange(fade_len) / fade_len
        vals *= fade

    vals = np.clip(vals, -32768, 32767).astype(np.int16)
    return pygame.mixer.Sound(buffer=vals.tobytes())


def generate_background_music(
    duration_ms: int = 8000, volume: float = 0.12
) -> pygame.mixer.Sound:
    """Generate a space ambient music loop using numpy.

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
    max_amp = 32767 * volume

    t = np.arange(n, dtype=np.float64) / sample_rate
    vals = np.zeros(n, dtype=np.float64)

    # Minor pentatonic scale (Hz) for the arpeggio
    pentatonic = [
        65.4, 77.8, 87.3, 98.0, 116.5,
        130.8, 155.6, 174.6, 196.0, 233.1,
    ]
    arp_notes = [pentatonic[i % len(pentatonic)] for i in range(12)]
    note_dur = n // len(arp_notes)

    # --- Layer 1: pulsating bass drone ---
    drone_freq = 55.0  # A1
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t)
    vals += max_amp * 0.45 * lfo * np.sin(2 * np.pi * drone_freq * t)
    vals += max_amp * 0.15 * lfo * np.sin(2 * np.pi * drone_freq * 2 * t)

    # --- Layer 2: pentatonic arpeggio ---
    for ni in range(len(arp_notes)):
        start = ni * note_dur
        end = min(start + note_dur, n)
        segment_len = end - start
        if segment_len <= 0:
            continue
        note_freq = arp_notes[ni]
        note_phase = np.arange(segment_len, dtype=np.float64) / segment_len
        env = np.where(
            note_phase < 0.05,
            note_phase / 0.05,
            np.maximum(0.0, 1.0 - (note_phase - 0.05) * 0.9),
        )
        seg_t = t[start:end]
        vals[start:end] += max_amp * 0.20 * env * np.sin(2 * np.pi * note_freq * seg_t)

    # --- Layer 3: cosmic shimmer ---
    shimmer_lfo = 0.3 + 0.7 * np.abs(np.sin(2 * np.pi * 0.07 * t))
    shimmer = np.random.randint(-int(max_amp), int(max_amp) + 1, n).astype(np.float64)
    vals += shimmer * 0.04 * shimmer_lfo

    # Fade in/out at loop boundaries (prevent clicks)
    fade_len = int(sample_rate * 0.3)
    if fade_len > 0 and n > 2 * fade_len:
        vals[:fade_len] *= np.arange(fade_len) / fade_len
        vals[-fade_len:] *= np.arange(fade_len, 0, -1) / fade_len

    vals = np.clip(vals, -32768, 32767).astype(np.int16)
    return pygame.mixer.Sound(buffer=vals.tobytes())


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
