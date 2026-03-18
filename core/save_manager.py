"""
Gestione del salvataggio e caricamento dei dati di gioco.

Salva/carica record, sblocchi navicelle e top punteggi da un file JSON.
"""

import json
import os


def _get_save_path():
    """Restituisce il percorso del file di salvataggio."""
    try:
        base_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))
    except Exception:
        base_dir = os.getcwd()
    return os.path.join(base_dir, "save_data.json")


SAVE_FILE = _get_save_path()

# Dati di default per una prima installazione
_DEFAULT_DATA = {
    "high_score": 0,
    "unlocked_ships": [True, True, False],  # Nave 1 e 2 sbloccate, Nave 3 bloccata
    "best_scores": [],
}


def load_save_data():
    """Carica i dati di salvataggio dal disco.

    Returns:
        dict: Dati di salvataggio, con campi mancanti riempiti dai default.
    """
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)
                # Merge con default per campi mancanti
                for key, default_value in _DEFAULT_DATA.items():
                    if key not in data:
                        data[key] = default_value
                return data
    except (json.JSONDecodeError, IOError):
        pass
    return dict(_DEFAULT_DATA)


def save_data(data):
    """Salva i dati di gioco su disco.

    Args:
        data: Dizionario con i dati da salvare.
    """
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError:
        pass
