from __future__ import annotations


BASE_DAMAGE = 2

WEAPON_PRIORITY = ["axe", "spear", "knife", "machete"]


class CombatState:

    def __init__(self, enemy_id: str, enemy_data: dict, weapon_damage: dict, damage_mult: float = 1.0):
        self.enemy_id: str = enemy_id
        self.enemy_name: str = enemy_data.get("name", "an enemy")
        self.enemy_desc: str = enemy_data.get("desc", "")
        self.enemy_symbol: str = enemy_data.get("symbol", "?")
        self.enemy_max_hp: int = int(enemy_data.get("hp", 10))
        self.enemy_hp: int = self.enemy_max_hp
        self.enemy_damage: int = max(1, int(int(enemy_data.get("damage", 3)) * damage_mult))
        self.weapon_damage: dict = weapon_damage
        self.combat_log: list[str] = []
        self.finished: bool = False
        self.player_won: bool = False
        self.player_fled: bool = False
        self.eat_cooldown: int = 0

    def best_weapon(self, inventory: dict) -> tuple[str | None, int]:
        for weapon in WEAPON_PRIORITY:
            if inventory.get(weapon, 0) > 0:
                dmg = self.weapon_damage.get(weapon, BASE_DAMAGE)
                return weapon, dmg
        return None, BASE_DAMAGE

    def player_attack(self, inventory: dict) -> list[str]:
        weapon, dmg = self.best_weapon(inventory)
        self.enemy_hp = max(0, self.enemy_hp - dmg)
        if self.eat_cooldown > 0:
            self.eat_cooldown -= 1
        if weapon:
            lines = [f"you strike with the {weapon} for {dmg} damage."]
        else:
            lines = [f"you swing bare-handed for {dmg} damage."]
        if self.enemy_hp <= 0:
            lines.append(f"{self.enemy_name} collapses.")
            self.finished = True
            self.player_won = True
        return lines

    def enemy_attack(self, player) -> list[str]:
        if self.finished:
            return []
        player.hp = max(0, player.hp - self.enemy_damage)
        lines = [f"{self.enemy_name} strikes for {self.enemy_damage} damage."]
        if player.hp <= 0:
            lines.append("you collapse. darkness takes you.")
            self.finished = True
            self.player_won = False
        return lines

    def can_eat(self) -> bool:
        return self.eat_cooldown <= 0

    def player_eat(self, player) -> list[str]:
        if self.eat_cooldown > 0:
            return [f"still recovering. eat ready in {self.eat_cooldown} turn{'s' if self.eat_cooldown > 1 else ''}."]
        food = player.inventory.get("food", 0)
        if food <= 0:
            return ["no food left."]
        player.inventory["food"] -= 1
        healed = min(5, player.max_hp - player.hp)
        player.hp = min(player.max_hp, player.hp + 5)
        self.eat_cooldown = 2
        if healed > 0:
            return [f"+{healed} hp. (food: {player.inventory.get('food', 0)})"]
        return [f"already full. (food: {player.inventory.get('food', 0)})"]

    def player_flee(self, player) -> list[str]:
        player.hp = max(0, player.hp - self.enemy_damage)
        lines = [f"{self.enemy_name} strikes as you turn to run."]
        self.finished = True
        self.player_fled = True
        if player.hp <= 0:
            lines.append("you collapse. darkness takes you.")
            self.player_fled = False
            self.player_won = False
        return lines
