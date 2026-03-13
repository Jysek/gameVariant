"""
Generazione procedurale degli effetti sonori e della musica di sottofondo.

Tutti i suoni vengono generati a runtime senza file audio esterni.
La musica di sottofondo è un loop ambientale spaziale generato proceduralmente.
"""

import math
import random
import pygame


def _generate_sound(frequency, duration_ms, volume=0.3, wave_type="square"):
    """Genera un singolo suono procedurale.

    Args:
        frequency: Frequenza in Hz.
        duration_ms: Durata in millisecondi.
        volume: Volume (0.0 - 1.0).
        wave_type: Tipo di onda ('square', 'sine', 'noise', 'sweep').

    Returns:
        pygame.mixer.Sound
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

        # Fade out nell'ultimo 20%
        fade_start = int(n_samples * 0.8)
        if i > fade_start:
            fade = 1.0 - (i - fade_start) / (n_samples - fade_start)
            val = int(val * fade)

        val = max(-32768, min(32767, val))
        buf[i * 2] = val & 0xFF
        buf[i * 2 + 1] = (val >> 8) & 0xFF

    return pygame.mixer.Sound(buffer=bytes(buf))


def generate_background_music(duration_ms=8000, volume=0.12):
    """Genera un loop di musica ambientale spaziale.

    Sovrappone tre strati:
    - Basso drone pulsante (onda sine a bassa frequenza)
    - Arpeggio pentatonico lento
    - Rumore cosmico filtrato (shimmer)

    Args:
        duration_ms: Durata del loop in ms (default 8 secondi).
        volume: Volume complessivo (tenuto basso per non coprire gli SFX).

    Returns:
        pygame.mixer.Sound
    """
    sample_rate = 22050
    n = int(sample_rate * duration_ms / 1000)
    buf = bytearray(n * 2)

    # Scala pentatonica minore (Hz) per l'arpeggio
    pentatonic = [65.4, 77.8, 87.3, 98.0, 116.5,  # C2-based
                  130.8, 155.6, 174.6, 196.0, 233.1]
    arp_notes = [pentatonic[i % len(pentatonic)] for i in range(12)]
    note_dur = n // len(arp_notes)  # campioni per nota dell'arpeggio

    max_amp = int(32767 * volume)

    for i in range(n):
        t = i / sample_rate
        val = 0

        # --- Strato 1: drone basso pulsante ---
        drone_freq = 55.0  # La1
        lfo = 0.6 + 0.4 * math.sin(2 * math.pi * 0.15 * t)  # LFO lento
        val += int(max_amp * 0.45 * lfo * math.sin(2 * math.pi * drone_freq * t))
        # Secondo armonico del drone
        val += int(max_amp * 0.15 * lfo * math.sin(2 * math.pi * drone_freq * 2 * t))

        # --- Strato 2: arpeggio pentatonico ---
        note_idx = (i // note_dur) % len(arp_notes)
        note_freq = arp_notes[note_idx]
        # Envelope della nota (attacco rapido, decay lento)
        note_phase = (i % note_dur) / note_dur
        if note_phase < 0.05:
            env = note_phase / 0.05
        else:
            env = 1.0 - (note_phase - 0.05) * 0.9
        env = max(0.0, env)
        val += int(max_amp * 0.20 * env * math.sin(2 * math.pi * note_freq * t))

        # --- Strato 3: shimmer cosmico ---
        # Rumore bianco attenuato con modulazione
        shimmer_lfo = 0.3 + 0.7 * abs(math.sin(2 * math.pi * 0.07 * t))
        shimmer = random.randint(-max_amp, max_amp) * 0.04 * shimmer_lfo
        val += int(shimmer)

        # Fade in/out agli estremi del loop (evita click)
        fade_len = int(sample_rate * 0.3)
        if i < fade_len:
            val = int(val * i / fade_len)
        elif i > n - fade_len:
            val = int(val * (n - i) / fade_len)

        val = max(-32768, min(32767, val))
        buf[i * 2] = val & 0xFF
        buf[i * 2 + 1] = (val >> 8) & 0xFF

    return pygame.mixer.Sound(buffer=bytes(buf))


def create_sounds():
    """Crea e restituisce il dizionario completo degli effetti sonori.

    Returns:
        dict[str, pygame.mixer.Sound]: Mappa nome -> suono.
    """
    sounds = {
        # -- Giocatore --
        "laser":           _generate_sound(880, 120, 0.2, "square"),
        "player_hit":      _generate_sound(350, 200, 0.3, "noise"),

        # -- Nemici --
        "enemy_laser":     _generate_sound(440, 150, 0.15, "square"),
        "explosion":       _generate_sound(200, 300, 0.3, "noise"),

        # -- Boss --
        "boss_warning":    _generate_sound(150, 600, 0.4, "square"),
        "boss_laser":      _generate_sound(220, 200, 0.25, "square"),
        "boss_hit":        _generate_sound(500, 100, 0.2, "noise"),
        "boss_defeated":   _generate_sound(600, 1200, 0.35, "sweep"),

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
        "game_over":  _generate_sound(300, 800, 0.3, "sweep"),
        "select":     _generate_sound(660, 80, 0.15, "sine"),
        "confirm":    _generate_sound(880, 100, 0.2, "sine"),
        "unlock":     _generate_sound(1200, 400, 0.25, "sine"),

        # -- Pausa --
        "pause":      _generate_sound(740, 90, 0.15, "sine"),
        "resume":     _generate_sound(880, 90, 0.15, "sine"),
    }
    return sounds
