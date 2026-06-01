"""
saveRules.py
────────────
Handles saving and loading player progress to/from a JSON file.
Save file is stored at: save_data.json (next to main.py)
"""

import json
import os

SAVE_FILE = "save_data.json"


# ── Helpers to serialize item objects ────────────────────────────────────────

def _item_to_dict(item):
    """Convert a Weapon / Armor / HealingItem object into a JSON-safe dict."""
    if item is None:
        return None
    return {"name": item.name}


def _item_from_name(name):
    """Look up an item object by name from the master item dict."""
    from itemRules import ITEM_DICT
    return ITEM_DICT.get(name)


# ── Public API ────────────────────────────────────────────────────────────────

def save_game(player):
    """
    Write the player's current state to SAVE_FILE.
    Returns True on success, False on failure.
    """
    try:
        data = {
            "name":             player.name,
            "max_health":       player.max_health,
            "current_health":   player.current_health,
            "money":            player.money,
            "equipped_weapon":  _item_to_dict(player.equipped_weapon),
            "equipped_armor":   _item_to_dict(player.equipped_armor),
            "inventory":        [_item_to_dict(i) for i in player.inventory],
            "location":         player.location,
            "visted location":   [_item_to_dict(i) for i in player.inventory],
        }
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        print(f"[Save Error] {e}")
        return False


def load_game():
    """
    Read SAVE_FILE and reconstruct a Player object.
    Returns a Player on success, or None if no save file exists or load fails.
    """
    if not os.path.exists(SAVE_FILE):
        return None

    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)

        from NpcAndPlayerRules import Player

        player = Player(data["name"], data["max_health"])
        player.current_health = data["current_health"]
        player.gold           = data["gold"]

        # Restore inventory
        player.inventory = []
        for item_dict in data.get("inventory", []):
            if item_dict:
                item = _item_from_name(item_dict["name"])
                if item:
                    player.inventory.append(item)

        # Restore equipped gear (look up by name so the object is live)
        w_data = data.get("equipped_weapon")
        if w_data:
            player.equipped_weapon = _item_from_name(w_data["name"])

        a_data = data.get("equipped_armor")
        if a_data:
            player.equipped_armor = _item_from_name(a_data["name"])

        return player

    except Exception as e:
        print(f"[Load Error] {e}")
        return None


def save_exists():
    """Return True if a save file is present."""
    return os.path.exists(SAVE_FILE)


def delete_save():
    """Delete the save file (e.g. after the player dies or finishes the game)."""
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)