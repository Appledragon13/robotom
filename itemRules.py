# =====================================================
# Weapon Class
# Represents a weapon the player can equip
# =====================================================
class Weapon:
    def __init__(self, name, attack_bonus, price, keyitem=False):
        self.name = name
        self.attack_bonus = attack_bonus
        self.price = price
        self.keyitem = keyitem

    def __str__(self):
        return f"{self.name} (+{self.attack_bonus} ATK) - {self.price} gold"


# =====================================================
# Armor Class
# =====================================================
class Armor:
    def __init__(self, name, defense_bonus, price, keyitem=False):
        self.name = name
        self.defense_bonus = defense_bonus
        self.price = price
        self.keyitem = keyitem

    def __str__(self):
        return f"{self.name} (+{self.defense_bonus} DEF) - {self.price} gold"


# =====================================================
# Healing Item
# =====================================================
class HealingItem:
    def __init__(self, name, heal_amount, price, keyitem=False):
        self.name = name
        self.heal_amount = heal_amount
        self.price = price
        self.keyitem = keyitem

    def __str__(self):
        return f"{self.name} (Heals {self.heal_amount}) - {self.price} gold"