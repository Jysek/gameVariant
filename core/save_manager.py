"""
Gestione dati di salvataggio per il progresso di gioco.

Carica/salva record, sblocchi navi e punteggi migliori in un file JSON.
Supporta 5 navi con sblocco progressivo basato sul punteggio.
"""

import json
import os

from core.constants import NUM_PLAYER_SHIPS, SHIP_UNLOCK_SCORES


def _get_save_path() -> str:
    """Restituisce il percorso assoluto del file dati di salvataggio."""
    try:
        base_dir = os.path.dirname(
            os.path.abspath(os.path.join(__file__, os.pardir)))
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
        dict: Dati di salvataggio con campi mancanti riempiti dai default.
    """
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)

                # Unisci con i default per campi mancanti
                for key, default_value in _DEFAULT_DATA.items():
                    if key not in data:
                        data[key] = default_value

                # Migrazione: gestisci transizione a 5 navi
                ships = data.get("unlocked_ships", [])
                if len(ships) != NUM_PLAYER_SHIPS:
                    new_ships = []
                    for i in range(NUM_PLAYER_SHIPS):
                        if i < len(ships) and ships[i]:
                            new_ships.append(True)
                        else:
                            new_ships.append(
                                data["high_score"] >= SHIP_UNLOCK_SCORES[i])
                    data["unlocked_ships"] = new_ships

                # Controlla sblocchi basati sul punteggio corrente
                check_unlocks(data)
                return data
    except (json.JSONDecodeError, IOError):
        pass
    return dict(_DEFAULT_DATA)


def save_data(data: dict) -> None:
    """Persiste i dati di gioco su disco come JSON.

    Args:
        data: Il dizionario dati di salvataggio da scrivere.
    """
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError:
        pass


def check_unlocks(data: dict) -> list[int]:
    """Controlla e sblocca le navi raggiungibili con il punteggio corrente.

    Args:
        data: Dizionario dati di salvataggio (modificato in-place).

    Returns:
        Lista di indici delle navi appena sbloccate.
    """
    newly_unlocked: list[int] = []
    high = data.get("high_score", 0)
    ships = data.get("unlocked_ships", list(_DEFAULT_UNLOCKED))

    # Assicura che la lista abbia la lunghezza corretta
    while len(ships) < NUM_PLAYER_SHIPS:
        ships.append(False)
    ships = ships[:NUM_PLAYER_SHIPS]

    for i, req_score in enumerate(SHIP_UNLOCK_SCORES):
        if not ships[i] and high >= req_score:
            ships[i] = True
            newly_unlocked.append(i)

    data["unlocked_ships"] = ships
    return newly_unlocked
