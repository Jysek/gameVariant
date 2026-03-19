"""
Effetti sonori procedurali e musica di sottofondo.

Tutti i suoni vengono generati a runtime senza file audio esterni.
La musica di sottofondo è un loop ambientale spaziale generato proceduralmente.

Usa numpy per generazione campioni veloce invece di loop Python per-campione.
"""

import numpy as np
import pygame


def _generate_sound(
    frequency: float, duration_ms: int, volume: float = 0.3,
    wave_type: str = "square",
) -> pygame.mixer.Sound:
    """Genera un singolo effetto sonoro procedurale usando numpy.

    Args:
        frequency:   Frequenza in Hz.
        duration_ms: Durata in millisecondi.
        volume:      Volume (0.0 - 1.0).
        wave_type:   Tipo onda ('square', 'sine', 'noise', 'sweep').

    Returns:
        Un oggetto ``pygame.mixer.Sound``.
    """
    sample_rate = 22050
    n_samples = int(sample_rate * duration_ms / 1000)
    max_amp = 32767 * volume

    t = np.arange(n_samples, dtype=np.float64) / sample_rate

    if wave_type == "square":
        vals = np.where(
            np.sin(2 * np.pi * frequency * t) >= 0,
            max_amp, -max_amp)
    elif wave_type == "sine":
        vals = max_amp * np.sin(2 * np.pi * frequency * t)
    elif wave_type == "noise":
        vals = np.random.randint(
            -int(max_amp), int(max_amp) + 1,
            n_samples).astype(np.float64)
    elif wave_type == "sweep":
        f = frequency * (1 - 0.8 * np.arange(n_samples) / n_samples)
        phase = np.cumsum(2 * np.pi * f / sample_rate)
        vals = max_amp * np.sin(phase)
    else:
        vals = np.zeros(n_samples)

    # Fade out nell'ultimo 20%
    fade_start = int(n_samples * 0.8)
    fade_len = n_samples - fade_start
    if fade_len > 0:
        fade = np.ones(n_samples)
        fade[fade_start:] = 1.0 - np.arange(fade_len) / fade_len
        vals *= fade

    vals = np.clip(vals, -32768, 32767).astype(np.int16)
    return pygame.mixer.Sound(buffer=vals.tobytes())


def generate_background_music(
    duration_ms: int = 8000, volume: float = 0.12,
) -> pygame.mixer.Sound:
    """Genera un loop di musica ambientale spaziale usando numpy.

    Sovrappone tre livelli:
    - Drone basso pulsante (onda sinusoidale a bassa frequenza)
    - Arpeggio pentatonico lento
    - Rumore cosmico filtrato (shimmer)

    Args:
        duration_ms: Durata del loop in ms (default 8 secondi).
        volume:      Volume complessivo (basso per non coprire gli SFX).

    Returns:
        Un oggetto ``pygame.mixer.Sound``.
    """
    sample_rate = 22050
    n = int(sample_rate * duration_ms / 1000)
    max_amp = 32767 * volume

    t = np.arange(n, dtype=np.float64) / sample_rate
    vals = np.zeros(n, dtype=np.float64)

    # Scala pentatonica minore (Hz) per l'arpeggio
    pentatonic = [
        65.4, 77.8, 87.3, 98.0, 116.5,
        130.8, 155.6, 174.6, 196.0, 233.1,
    ]
    arp_notes = [pentatonic[i % len(pentatonic)] for i in range(12)]
    note_dur = n // len(arp_notes)

    # --- Livello 1: drone basso pulsante ---
    drone_freq = 55.0  # A1
    lfo = 0.6 + 0.4 * np.sin(2 * np.pi * 0.15 * t)
    vals += max_amp * 0.45 * lfo * np.sin(2 * np.pi * drone_freq * t)
    vals += max_amp * 0.15 * lfo * np.sin(2 * np.pi * drone_freq * 2 * t)

    # --- Livello 2: arpeggio pentatonico ---
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
        vals[start:end] += (
            max_amp * 0.20 * env * np.sin(2 * np.pi * note_freq * seg_t))

    # --- Livello 3: shimmer cosmico ---
    shimmer_lfo = 0.3 + 0.7 * np.abs(np.sin(2 * np.pi * 0.07 * t))
    shimmer = np.random.randint(
        -int(max_amp), int(max_amp) + 1, n).astype(np.float64)
    vals += shimmer * 0.04 * shimmer_lfo

    # Fade in/out ai confini del loop (previene click)
    fade_len = int(sample_rate * 0.3)
    if fade_len > 0 and n > 2 * fade_len:
        vals[:fade_len] *= np.arange(fade_len) / fade_len
        vals[-fade_len:] *= np.arange(fade_len, 0, -1) / fade_len

    vals = np.clip(vals, -32768, 32767).astype(np.int16)
    return pygame.mixer.Sound(buffer=vals.tobytes())


def create_sounds() -> dict[str, pygame.mixer.Sound]:
    """Crea e restituisce il dizionario completo degli effetti sonori.

    Returns:
        Mappa da nome suono a oggetto ``pygame.mixer.Sound``.
    """
    sounds = {
        # -- Giocatore --
        "laser":       _generate_sound(880, 120, 0.2, "square"),
        "player_hit":  _generate_sound(350, 200, 0.3, "noise"),

        # -- Nemici --
        "enemy_laser": _generate_sound(440, 150, 0.15, "square"),
        "explosion":   _generate_sound(200, 300, 0.3, "noise"),

        # -- Boss --
        "boss_warning":  _generate_sound(150, 600, 0.4, "square"),
        "boss_laser":    _generate_sound(220, 200, 0.25, "square"),
        "boss_hit":      _generate_sound(500, 100, 0.2, "noise"),
        "boss_defeated": _generate_sound(600, 1200, 0.35, "sweep"),

        # -- Power-up --
        "carrier_hit":       _generate_sound(600, 80, 0.2, "noise"),
        "carrier_destroyed": _generate_sound(400, 400, 0.3, "sweep"),
        "powerup_collect":   _generate_sound(1000, 300, 0.3, "sine"),
        "shield_active":     _generate_sound(500, 200, 0.2, "sine"),
        "shield_break":      _generate_sound(250, 400, 0.25, "noise"),

        # -- Asteroidi --
        "asteroid_warning":      _generate_sound(120, 400, 0.2, "square"),
        "asteroid_rain_warning": _generate_sound(100, 800, 0.4, "square"),

        # -- UI / Menu --
        "game_over": _generate_sound(300, 800, 0.3, "sweep"),
        "select":    _generate_sound(660, 80, 0.15, "sine"),
        "confirm":   _generate_sound(880, 100, 0.2, "sine"),
        "unlock":    _generate_sound(1200, 400, 0.25, "sine"),

        # -- Pausa --
        "pause":  _generate_sound(740, 90, 0.15, "sine"),
        "resume": _generate_sound(880, 90, 0.15, "sine"),

        # -- Bomba --
        "bomb":   _generate_sound(150, 500, 0.35, "noise"),
    }
    return sounds
