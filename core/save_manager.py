"""
Save data management for game progress.

Loads/saves records, ship unlocks, and top scores to a JSON file.
Supports 5 ships with progressive score-based unlocking.
"""

import json
import os

from core.constants import NUM_PLAYER_SHIPS, SHIP_UNLOCK_SCORES


def _get_save_path() -> str:
    """Return the absolute path to the save data file."""
    try:
        base_dir = os.path.dirname(os.path.abspath(os.path.join(__file__, os.pardir)))
    except Exception:
        base_dir = os.getcwd()
    return os.path.join(base_dir, "save_data.json")


SAVE_FILE = _get_save_path()

# Default: ships with unlock_score == 0 are unlocked by default
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
    """Load save data from disk.

    Automatically handles migration from previous versions
    (10/12 ships -> 5 ships).

    Returns:
        dict: Save data with missing fields filled from defaults.
    """
    try:
        if os.path.exists(SAVE_FILE):
            with open(SAVE_FILE, "r") as f:
                data = json.load(f)

                # Merge with defaults for missing fields
                for key, default_value in _DEFAULT_DATA.items():
                    if key not in data:
                        data[key] = default_value

                # Migration: handle transition to 5 ships
                ships = data.get("unlocked_ships", [])
                if len(ships) != NUM_PLAYER_SHIPS:
                    new_ships = []
                    for i in range(NUM_PLAYER_SHIPS):
                        if i < len(ships) and ships[i]:
                            new_ships.append(True)
                        else:
                            new_ships.append(data["high_score"] >= SHIP_UNLOCK_SCORES[i])
                    data["unlocked_ships"] = new_ships

                # Check unlocks based on current high score
                check_unlocks(data)
                return data
    except (json.JSONDecodeError, IOError):
        pass
    return dict(_DEFAULT_DATA)


def save_data(data: dict) -> None:
    """Persist game data to disk as JSON.

    Args:
        data: The save data dictionary to write.
    """
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except IOError:
        pass


def check_unlocks(data: dict) -> list[int]:
    """Check and unlock ships reachable with the current high score.

    Args:
        data: Save data dictionary (modified in-place).

    Returns:
        List of indices of newly unlocked ships.
    """
    newly_unlocked: list[int] = []
    high = data.get("high_score", 0)
    ships = data.get("unlocked_ships", list(_DEFAULT_UNLOCKED))

    # Ensure the list has the correct length
    while len(ships) < NUM_PLAYER_SHIPS:
        ships.append(False)
    ships = ships[:NUM_PLAYER_SHIPS]

    for i, req_score in enumerate(SHIP_UNLOCK_SCORES):
        if not ships[i] and high >= req_score:
            ships[i] = True
            newly_unlocked.append(i)

    data["unlocked_ships"] = ships
    return newly_unlocked
