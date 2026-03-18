"""
Gestione del salvataggio e caricamento dei dati di gioco.

Salva/carica record, sblocchi navicelle e top punteggi da un file JSON.
Supporta 5 navicelle con sblocco progressivo basato sul punteggio.
"""

import json
import os

from core.constants import NUM_PLAYER_SHIPS, SHIP_UNLOCK_SCORES


def _get_save_path():
    """Restituisce il percorso del file di salvataggio."""
    try:
        base_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))
    except Exception:
        base_dir = os.getcwd()
    return os.path.join(base_dir, "save_data.json")


SAVE_FILE = _get_save_path()

# Default: le navi con unlock_score == 0 sono sbloccate di default
_DEFAULT_UNLOCKED = [score == 0 for score in SHIP_UNLOCK_SCORES]

_DEFAULT_DATA = {
    "high_score": 0,
    "unlocked_ships": list(_DEFAULT_UNLOCKED),
    "best_scores": [],
    "total_playtime": 0,
    "total_kills": 0,
    "bosses_defeated": 0,
}


def load_save_data() -> dict:
    """Carica i dati di salvataggio dal disco.

    Gestisce automaticamente la migrazione da versioni precedenti
    (10/12 navi -> 5 navi).

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

                # Migrazione: gestisci il passaggio a 5 navi
                ships = data.get("unlocked_ships", [])
                if len(ships) != NUM_PLAYER_SHIPS:
                    # Ricrea la lista per 5 navi basandosi sul punteggio
                    new_ships = []
                    for i in range(NUM_PLAYER_SHIPS):
                        if i < len(ships) and ships[i]:
                            new_ships.append(True)
                        else:
                            new_ships.append(data["high_score"] >= SHIP_UNLOCK_SCORES[i])
                    data["unlocked_ships"] = new_ships

                # Controlla sblocchi in base al record corrente
                check_unlocks(data)

                return data
    except (json.JSONDecodeError, IOError):
        pass
    return dict(_DEFAULT_DATA)


def save_data(data: dict) -> None:
    """Salva i dati di gioco su disco."""
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError:
        pass


def check_unlocks(data: dict) -> list[int]:
    """Verifica e sblocca le navi raggiungibili con il punteggio corrente.

    Returns:
        Lista di indici delle navi appena sbloccate.
    """
    newly_unlocked: list[int] = []
    high = data.get("high_score", 0)
    ships = data.get("unlocked_ships", list(_DEFAULT_UNLOCKED))

    # Assicura che la lista abbia la lunghezza corretta
    while len(ships) < NUM_PLAYER_SHIPS:
        ships.append(False)
    # Tronca se troppo lunga
    ships = ships[:NUM_PLAYER_SHIPS]

    for i, req_score in enumerate(SHIP_UNLOCK_SCORES):
        if not ships[i] and high >= req_score:
            ships[i] = True
            newly_unlocked.append(i)

    data["unlocked_ships"] = ships
    return newly_unlocked
