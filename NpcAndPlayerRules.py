import random

def roll(base, variance=0.10): 
    return int(base * random.uniform(1 - variance, 1 + variance))

class Enemy:
    def __init__(self, name, max_health, attack_power, defense):
        self.name = name
        self.max_health = max_health
        self.current_health = max_health
        self.attack_power = attack_power
        self.defense = defense

    def is_alive(self):
        return self.current_health > 0

    def attack(self, target):
        damage = max(
            1,
            int(self.attack_power * (100 / (100 + target.get_defense() * 2.2)))
        )
        target.take_damage(damage)

    def get_defense(self):
        return self.defense

    def take_damage(self, damage):
        self.current_health = max(0, self.current_health - damage)

    def __str__(self):
        return f"{self.name} HP: {self.current_health}/{self.max_health}"    

class Boss:
    def __init__(self, name, max_health, attack_power, defense, phases=None):
        self.name = name
        self.max_health = max_health
        self.current_health = max_health
        self.attack_power = attack_power
        self.defense = defense

        # optional multi-phase system
        self.phases = phases or {}

    def is_alive(self):
        return self.current_health > 0

    def get_phase(self):
        ratio = self.current_health / self.max_health

        if ratio > 0.66:
            return 1
        elif ratio > 0.33:
            return 2
        else:
            return 3

    def attack(self, target):

        phase = self.get_phase()
        phase_data = self.phases.get(phase, {})

        atk = phase_data.get("atk", self.attack_power)

        damage = max(
            2,
            int(
                atk *
                (100 / (100 + target.get_defense() * 3))
            )
        )

        target.take_damage(damage)

        # Optional DOT damage
        if "dot" in phase_data:
            target.take_damage(phase_data["dot"])

    def get_defense(self):
        return self.defense

    def take_damage(self, damage):
        self.current_health = max(0, self.current_health - damage)

    def __str__(self):
        return f"{self.name} HP: {self.current_health}/{self.max_health}"


class Player:
    def __init__(self, name, max_health):
        self.name = name
        self.max_health = max_health
        self.current_health = max_health
        self.inventory = []
        self.equipped_weapon = None
        self.equipped_armor = None
        self.money = 0
        self.base_defense = 2
        self.base_attack = 8



    def level_up(self, new_health):
        self.max_health = new_health
        self.current_health = self.max_health

    def is_alive(self):
        return self.current_health > 0

    def get_attack_power(self):
        
        if self.equipped_weapon:
            return self.base_attack + self.equipped_weapon.attack_bonus
        return self.base_attack

    def get_defense(self):
        if self.equipped_armor:
            return self.base_defense + self.equipped_armor.defense_bonus
        return self.base_defense

    def attack(self, target):
        damage = max(
            1,
            int(
                self.get_attack_power() *
                (100 / (100 + target.get_defense() * 3))
            )
        )

        target.take_damage(damage)

    def take_damage(self, damage):
        self.current_health -= damage
        self.current_health = max(0, self.current_health)

    def heal(self, healing_item):
        if healing_item in self.inventory:
            self.current_health += healing_item.heal_amount
            self.current_health = min(self.max_health, self.current_health)
            self.inventory.remove(healing_item)

    def equip_weapon(self, weapon):
        self.equipped_weapon = weapon

    def equip_armor(self, armor):
        self.equipped_armor = armor

    def add_to_inventory(self, item):
        """
        Add item to inventory. Auto-equip if it's better than current gear.
        Returns an auto-equip message string, or None if no auto-equip happened.
        """
        self.inventory.append(item)
        auto_msg = None

        if hasattr(item, "attack_bonus"):
            current_bonus = self.equipped_weapon.attack_bonus if self.equipped_weapon else -1
            if item.attack_bonus > current_bonus:
                self.equipped_weapon = item
                auto_msg = f"Auto-equipped {item.name} (+{item.attack_bonus} ATK) — stronger than your old weapon!"

        elif hasattr(item, "defense_bonus"):
            current_bonus = self.equipped_armor.defense_bonus if self.equipped_armor else -1
            if item.defense_bonus > current_bonus:
                self.equipped_armor = item
                auto_msg = f"Auto-equipped {item.name} (+{item.defense_bonus} DEF) — stronger than your old armor!"

        return auto_msg
    def menu(self, ui):
            """
            Let the player view their inventory and manually change equipped gear.
            Items are shown 6 per page so large inventories don't break the UI.
            Loops until the player chooses to go back.
            """
            while True:
                weapon_name = self.equipped_weapon.name if self.equipped_weapon else "None"
                armor_name  = self.equipped_armor.name  if self.equipped_armor  else "None"

                # ── Summary header shown above the action menu ──
                header = "\n".join([
                    "=== INVENTORY ===",
                    f"HP: {self.current_health} / {self.max_health}",
                    f"Gold: {self.gold}",
                    f"ATK: {self.get_attack_power()}  |  DEF: {self.get_defense()}",
                    "",
                    f"Equipped Weapon : {weapon_name}",
                    f"Equipped Armor  : {armor_name}",
                    "",
                    f"Items in bag: {len(self.inventory)}",
                ])

                # ── Top-level action choice ──
                action = ui.show(header, ["Use / Equip item", "Back"])

                if action == 2:
                    break

                # ── Pick an item from the paged list ──
                if not self.inventory:
                    ui.show_message("Your inventory is empty.")
                    continue

                # Build display labels that show equipped tags
                class LabelledItem:
                    def __init__(self, item, label):
                        self.item  = item
                        self._label = label
                    def __str__(self):
                        return self._label

                labelled = []
                for item in self.inventory:
                    tag = ""
                    if item is self.equipped_weapon:
                        tag = " [W]"
                    elif item is self.equipped_armor:
                        tag = " [A]"
                    labelled.append(LabelledItem(item, f"{item}{tag}"))

                picked = paged_item_picker(ui, labelled, title="Select an item")
                if picked is None:
                    continue

                item = picked.item

                # ── Act on the chosen item ──
                if item.keyitem == True:
                    ui.show_message(
                        f"{item.name} cannot be used right now."
                    )
                if hasattr(item, "heal_amount"):
                    old_hp = self.current_health
                    self.heal(item)
                    healed = self.current_health - old_hp
                    ui.show_message(
                        f"Used {item.name}.\n"
                        f"Healed {healed} HP.\n"
                        f"HP: {self.current_health}/{self.max_health}"
                    )

                elif hasattr(item, "attack_bonus"):
                    self.equipped_weapon = item
                    ui.show_message(f"Equipped {item.name} (+{item.attack_bonus} ATK).")

                elif hasattr(item, "defense_bonus"):
                    self.equipped_armor = item
                    ui.show_message(f"Equipped {item.name} (+{item.defense_bonus} DEF).")

                else:
                    ui.show_message(
                        f"{item.name} cannot be used right now."
                    )

    def __str__(self):
        return (f"{self.name} HP: {self.current_health}/{self.max_health}\n"
                f"Weapon: {self.equipped_weapon.name if self.equipped_weapon else 'None'}\n"
                f"Armor: {self.equipped_armor.name if self.equipped_armor else 'None'}")