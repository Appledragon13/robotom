import random
from gameUI import AdventureUI
from NpcAndPlayerRules import Boss
from itemRules import BOSS_ITEMS


# =====================================================
# BOSS PHASE TRACKER
# Returns which phase (1/2/3) a boss is in
# based on its remaining HP percentage
# =====================================================
def get_boss_phase(enemy):
    hp_ratio = enemy.current_health / enemy.max_health

    if hp_ratio > 0.66:
        return 1
    elif hp_ratio > 0.33:
        return 2
    else:
        return 3


def get_single_boss(enemies):
    living_bosses = [
        e for e in enemies
        if e.is_alive() and isinstance(e, Boss)
    ]
    return living_bosses[0] if len(living_bosses) == 1 else None


# =====================================================
# DAMAGE FORMULA
# Unified defense formula used for all damage in game.
# Enemies use multiplier 2.0, bosses use 2.5.
# Pass is_boss=True when a boss is attacking.
# =====================================================
def calc_damage(base, defense, is_boss=False):
    multiplier = 2.5 if is_boss else 2.0
    return max(1, int(base * (100 / (100 + defense * multiplier))))


# =====================================================
# PLAYER LAYER EFFECTS
# Rolls effects that apply to the player's turn only.
# Called once per round before the player acts.
# Includes: miss chance, DOTs, bonus damage, heal enemies
# =====================================================
def apply_player_effects(player, enemies: list) -> dict:
    layer = player.layer
    effects = {}

    boss = get_single_boss(enemies)

    if layer == 1:
        effects["layer_msg"] = "Hollow sighs fill Limbo."

    elif layer == 2:
        if random.random() < 0.25:
            effects["layer_msg"] = "You miss!"
            effects["miss"] = True
        else:
            effects["layer_msg"] = "Lust winds swirl."

    elif layer == 3:
        effects["layer_msg"] = "Acid rain burns you."
        effects["player_dot"] = 3

    elif layer == 4:
        effects["layer_msg"] = "Greed feeds enemies."
        effects["heal_enemies"] = 4

    elif layer == 5:
        effects["layer_msg"] = "Wrath ignites everything!"
        effects["bonus_damage"] = 4

        if boss and boss.name == "Luke the Breaking Point":
            phase = get_boss_phase(boss)
            if phase == 1:
                effects["layer_msg"] += "\nLuke is holding it together."
            elif phase == 2:
                effects["layer_msg"] += "\nHis restraint cracks."
                effects["bonus_damage"] = 8
            elif phase == 3:
                effects["layer_msg"] += "\nHE SNAPS."
                effects["bonus_damage"] = 14
                effects["player_dot"] = 2

    elif layer == 6:
        effects["layer_msg"] = "Flames scorch all."
        effects["player_dot"] = 2
        effects["enemy_dot"] = 2

    elif layer == 7:
        effects["layer_msg"] = "Blood frenzy!"
        effects["extra_player_atk"] = 1

    elif layer == 8:
        effects["layer_msg"] = "Fraud warps perception."

    elif layer == 9:
        effects["layer_msg"] = "Treachery's cold grips you."
        effects["player_def_bonus"] = 3

    return effects


# =====================================================
# ENEMY LAYER EFFECTS
# Rolls effects that apply to the enemy turn only.
# Called once per round before enemies act.
# Includes: attack multipliers, skip turn chance
# =====================================================
def apply_enemy_effects(player, enemies: list) -> dict:
    layer = player.layer
    effects = {}

    boss = get_single_boss(enemies)

    if layer == 1:
        effects["double_enemy_atk"] = 1.2

    elif layer == 5:
        effects["double_enemy_atk"] = 1.3

        if boss and boss.name == "Luke the Breaking Point":
            phase = get_boss_phase(boss)
            if phase == 2:
                effects["double_enemy_atk"] = 1.8
            elif phase == 3:
                effects["double_enemy_atk"] = 2.4

    elif layer == 8:
        if random.random() < 0.35:
            effects["layer_msg"] = "Illusions confuse enemies!"
            effects["skip_enemy_turn"] = True

    elif layer == 9:
        if random.random() < 0.2:
            effects["layer_msg"] = "Ice locks enemies!"
            effects["skip_enemy_turn"] = True

    return effects


# =====================================================
# LUKE PHASE TRANSITION
# Fires once per phase when Luke crosses a HP threshold.
# Tracked via _phase_bumped so it never runs twice.
# Phase 2: +6 ATK, Phase 3: +10 ATK
# Call once per round before the enemy turn.
# =====================================================
def handle_luke_phase_transition(boss):
    if boss.name != "Luke the Breaking Point":
        return

    if not hasattr(boss, "_phase_bumped"):
        boss._phase_bumped = set()

    phase = get_boss_phase(boss)

    if phase not in boss._phase_bumped:
        boss._phase_bumped.add(phase)
        if phase == 2:
            boss.attack_power += 6
        elif phase == 3:
            boss.attack_power += 10


# =====================================================
# COMBAT DIALOGUE BUILDER
# Assembles the battle screen shown to the player.
# Shows player stats, all enemy HP, and the last
# 15 lines of the combat log.
# =====================================================
def _build_dialogue(player, enemies, log):
    lines = []

    lines.append(f"{player.name}")
    lines.append(f"HP: {player.current_health}/{player.max_health}")
    lines.append(
        f"ATK: {player.get_attack_power()}  DEF: {player.get_defense()}"
    )
    lines.append("")
    lines.append("Enemies:")

    for enemy in enemies:
        status = "ALIVE" if enemy.is_alive() else "DEAD"
        lines.append(
            f"- {enemy.name} | "
            f"HP: {enemy.current_health}/{enemy.max_health} | "
            f"{status}"
        )

    lines.append("")
    lines.append("=" * 40)
    lines.append("")
    lines.extend(log[-15:])

    return "\n".join(lines)


# =====================================================
# EQUIPMENT REFRESH
# Scans inventory and auto-equips the highest stat
# weapon and armor before combat begins.
# =====================================================
def refresh_equipment(player):
    best_weapon = player.equipped_weapon
    best_armor = player.equipped_armor

    for item in player.inventory:
        if hasattr(item, "attack_bonus"):
            if best_weapon is None or item.attack_bonus > best_weapon.attack_bonus:
                best_weapon = item
        elif hasattr(item, "defense_bonus"):
            if best_armor is None or item.defense_bonus > best_armor.defense_bonus:
                best_armor = item

    player.equipped_weapon = best_weapon
    player.equipped_armor = best_armor


# =====================================================
# PAGED ITEM PICKER
# Shows items 6 at a time with Next/Prev page controls.
# Used whenever an item list could exceed the UI limit.
# Returns the chosen item, or None if the player cancels.
# PAGE_SIZE can be adjusted if the UI supports more rows.
# =====================================================
PAGE_SIZE = 6

def paged_item_picker(ui, items, title="Choose an item"):
    page = 0

    while True:
        total_pages = max(1, -(-len(items) // PAGE_SIZE))  # ceiling division
        start = page * PAGE_SIZE
        end   = start + PAGE_SIZE
        page_items = items[start:end]

        choices = [str(i) for i in page_items]

        nav = f"  (Page {page + 1}/{total_pages})" if total_pages > 1 else ""

        if page > 0:
            choices.append("< Prev page")
        if page < total_pages - 1:
            choices.append("Next page >")

        choices.append("Cancel")

        raw = ui.show(f"{title}{nav}", choices)
        picked_label = choices[raw - 1]

        if picked_label == "Cancel":
            return None
        elif picked_label == "Next page >":
            page += 1
        elif picked_label == "< Prev page":
            page -= 1
        else:
            return page_items[raw - 1]


# =====================================================
# PLAYER TURN
# Handles the player's action for one round.
# Applies heal_enemies passive before action choice.
# Player can Attack or Heal each turn.
# DOT damage is NOT applied here — see end_of_round.
# =====================================================
def player_turn(player, enemies, player_effects, log, ui):
    turn = list(log)

    if "layer_msg" in player_effects:
        turn.append(player_effects["layer_msg"])

    if player_effects.get("heal_enemies"):
        for e in enemies:
            if e.is_alive():
                e.current_health = min(
                    e.max_health,
                    e.current_health + player_effects["heal_enemies"]
                )

    living = [e for e in enemies if e.is_alive()]

    while True:
        action = ui.show(_build_dialogue(player, enemies, turn), ["Attack", "Heal"])

        if action == 1:
            if player_effects.get("miss"):
                turn.append("Your attack missed!")
                return turn

            target = living[0] if len(living) == 1 else living[
                ui.show("Pick target", [e.name for e in living]) - 1
            ]

            base = player.get_attack_power() + player_effects.get("bonus_damage", 0)
            dmg = calc_damage(base, target.get_defense(), is_boss=False)

            target.take_damage(dmg)
            turn.append(f"{player.name} hits {target.name} for {dmg}")

            for _ in range(player_effects.get("extra_player_atk", 0)):
                if target.is_alive():
                    extra = calc_damage(player.get_attack_power(), target.get_defense(), is_boss=False)
                    target.take_damage(extra)
                    turn.append(f"Frenzy hit for {extra}")

            return turn

        elif action == 2:
            heal_items = [i for i in player.inventory if hasattr(i, "heal_amount")]
            if not heal_items:
                turn.append("No healing items!")
                continue

            item = paged_item_picker(ui, heal_items, title="Choose a healing item")
            if item is None:
                continue  # player hit Cancel, loop back to Attack/Heal choice

            player.heal(item)
            turn.append(f"Used {item.name}")
            return turn


# =====================================================
# ENEMY TURN
# All living enemies attack the player.
# Uses is_boss flag to apply correct damage multiplier.
# Skips entirely if skip_enemy_turn effect is active.
# =====================================================
def enemies_turn(player, enemies, enemy_effects):
    if enemy_effects.get("skip_enemy_turn"):
        return [enemy_effects.get("layer_msg", "Enemies frozen!")]

    out = []

    if "layer_msg" in enemy_effects:
        out.append(enemy_effects["layer_msg"])

    player_def = player.get_defense() + enemy_effects.get("player_def_bonus", 0)

    for e in enemies:
        if e.is_alive():
            base = e.attack_power * enemy_effects.get("double_enemy_atk", 1.0)
            is_boss = isinstance(e, Boss)
            dmg = calc_damage(base, player_def, is_boss=is_boss)

            player.take_damage(dmg)
            out.append(f"{e.name} hits for {dmg}")

    return out


# =====================================================
# END OF ROUND EFFECTS
# DOT damage for both player and enemies fires here,
# after both sides have taken their turn.
# This prevents DOTs from giving free pre-turn damage.
# =====================================================
def end_of_round_effects(player, enemies, player_effects, enemy_effects) -> list:
    out = []

    if player_effects.get("player_dot"):
        dmg = player_effects["player_dot"]
        player.take_damage(dmg)
        out.append(f"You take {dmg} burn damage.")

    if player_effects.get("enemy_dot"):
        dmg = player_effects["enemy_dot"]
        for e in enemies:
            if e.is_alive():
                e.take_damage(dmg)
                out.append(f"{e.name} takes {dmg} DOT damage.")

    return out


# =====================================================
# BOSS LOOT DROPS
# Weapon is always awarded on boss kill.
# Armor is a 50% bonus drop.
# =====================================================
def get_boss_drops(boss):
    drops = BOSS_ITEMS.get(boss.name, [])

    weapons = [i for i in drops if hasattr(i, "attack_bonus")]
    armors  = [i for i in drops if hasattr(i, "defense_bonus")]

    result = []

    # Always give weapon if it exists
    if weapons:
        result.append(weapons[0])

    # Always give armor if it exists
    if armors:
        result.append(armors[0])

    return result


# =====================================================
# GOLD REWARD
# Base gold scales with layer: 40 + (layer-1)*30.
# Boss fights pay 2.5x the base amount.
# Final value has a +/-20% random variance.
# =====================================================
def calc_gold_reward(layer: int, is_boss: bool = False) -> int:
    base = 40 + (layer) * 30
    if is_boss:
        base = int(base * 4)
    variance = random.uniform(0.8, 1.2)
    return max(10, int(base * variance))


# =====================================================
# MAIN COMBAT LOOP
# Runs until the player or all enemies are dead.
# Each round: player acts, enemies act, DOTs tick.
# Luke phase transitions are checked every round.
# Gold and loot are awarded on victory.
# Combat log is capped at 50 entries in memory.
# =====================================================
def combat(player, enemies, ui: AdventureUI):
    refresh_equipment(player)

    if not isinstance(enemies, list):
        enemies = [enemies]
        
    if not enemies:
        ui.show_message("[ERROR] No valid enemies for this fight.")
        return False
    log = ["Battle begins!"]
    is_boss_fight = any(isinstance(e, Boss) for e in enemies)

    while player.is_alive() and any(e.is_alive() for e in enemies):

        player_effects = apply_player_effects(player, enemies)
        enemy_effects  = apply_enemy_effects(player, enemies)

        log = player_turn(player, enemies, player_effects, log, ui)

        if not any(e.is_alive() for e in enemies):

            dot_out = end_of_round_effects(player, enemies, player_effects, enemy_effects)
            log += dot_out
            log = log[-50:]

            boss = next(
                (e for e in enemies if isinstance(e, Boss)),
                None
            )
            loot_msgs = []

            if boss:
                drops = get_boss_drops(boss)

                loot_msgs.append("=" * 35)
                loot_msgs.append(f"{boss.name} defeated!")
                loot_msgs.append("=" * 35)
                loot_msgs.append("")

                if drops:
                    loot_msgs.append("BOSS LOOT ACQUIRED:")

                    for item in drops:
                        auto_msg = player.add_to_inventory(item)

                        if hasattr(item, "attack_bonus"):
                            loot_msgs.append(f"{item.name} (+{item.attack_bonus} ATK)")
                        elif hasattr(item, "defense_bonus"):
                            loot_msgs.append(f"{item.name} (+{item.defense_bonus} DEF)")

                        if auto_msg:
                            loot_msgs.append(auto_msg)

                    loot_msgs.append("")

            gold = calc_gold_reward(player.layer, is_boss=is_boss_fight)
            player.gold += gold
            loot_msgs.append(f"  Gold gained: {gold}  (Total: {player.gold})")

            ui.show_message("Victory!\n\n" + "\n".join(loot_msgs))
            return True

        boss = get_single_boss(enemies)
        if boss:
            handle_luke_phase_transition(boss)

        log += enemies_turn(player, enemies, enemy_effects)
        log += end_of_round_effects(player, enemies, player_effects, enemy_effects)
        log = log[-50:]

        if not player.is_alive():
            ui.show_message("You died.")
            return False

    return player.is_alive()