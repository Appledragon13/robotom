"""
Imports needed to run the game
"""
import subprocess
import sys
try:
    import pyfiglet
except ImportError:
    print("pyfiglet not found. Installing...")
    subprocess.check_call([
        sys.executable,
        "-m",
        "pip",
        "install",
        "pyfiglet",
        "--break-system-packages"
    ])
    import pyfiglet
from gameUI import AdventureUI
import saveRules
import NpcAndPlayerRules

def loadgame(ui, player):

    player = saveRules.load_game()

    if player is None:

        ui.show_message(
            "No save file found.",
            "[ Press any key ]"
        )

        return

    # Prevent crashes on old saves
    if not hasattr(player, "completed_layers"):
        player.completed_layers = []

    weapon_name = (
        player.equipped_weapon.name
        if player.equipped_weapon else "None"
    )

    armor_name = (
        player.equipped_armor.name
        if player.equipped_armor else "None"
    )

    ui.show_message(
        f"Save Loaded.\n\n"
        f"Name: {player.name}\n"
        f"Layer: {player.layer} — {LAYER_NAMES[player.layer]}\n"
        f"HP: {player.current_health}/{player.max_health}\n"
        f"Gold: {player.gold}\n"
        f"Weapon: {weapon_name}\n"
        f"Armor: {armor_name}",
        "[ Press any key ]"
    )




def startGame():
    with AdventureUI(title="[ Robotom ]") as ui:
        while True:
            ui.type_speed = 0.0
            banner = pyfiglet.figlet_format("Robotom", font="doh", width=200)
            save_label = (
                "Load Game"
                if saveRules.save_exists()
                else "Load Game (No Save)"
            )
            choice = ui.show(
                banner,
                ["New Game", save_label, "Quit"]
                )
            ui.type_speed=0.06
            # =========================
            # NEW GAME
            # =========================
            if choice == 1:
                pass

            # =========================
            # LOAD GAME
            # =========================
            elif choice == 2:

                if saveRules.save_exists():
                    loadgame(ui)

                else:
                    ui.show_message(
                        "No save file exists.",
                        "[ Press any key ]"
                    )

            # =========================
            # QUIT
            # =========================
            elif choice == 3:

                ui.show_message(
                    "Thanks for playing Robotom.",
                    "[ Press any key ]"
                )

                break


if __name__ == "__main__":
    startGame()
