import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from engine.game_state import GameState
from engine.combat import CombatState


def _make_state():
    return GameState()


class TestCombatState:

    def test_enemy_takes_damage(self):
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        inv = {"knife": 1}
        cs.player_attack(inv)
        assert cs.enemy_hp < 10

    def test_bare_fist_damage(self):
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        lines = cs.player_attack({})
        assert cs.enemy_hp == 8
        assert "bare-handed" in lines[0]

    def test_weapon_damage_knife(self):
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {"knife": 4})
        cs.player_attack({"knife": 1})
        assert cs.enemy_hp == 6

    def test_weapon_damage_axe_priority(self):
        cs = CombatState("boar", {"name": "boar", "hp": 20, "damage": 3, "symbol": "B"}, {"axe": 6, "knife": 4})
        cs.player_attack({"axe": 1, "knife": 1})
        assert cs.enemy_hp == 14

    def test_enemy_dies(self):
        cs = CombatState("boar", {"name": "boar", "hp": 2, "damage": 3, "symbol": "B"}, {})
        cs.player_attack({})
        assert cs.enemy_hp == 0
        assert cs.finished
        assert cs.player_won

    def test_enemy_attacks_player(self):
        state = _make_state()
        state.player.hp = 20
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        cs.enemy_attack(state.player)
        assert state.player.hp == 17

    def test_player_dies(self):
        state = _make_state()
        state.player.hp = 2
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        cs.enemy_attack(state.player)
        assert state.player.hp == 0
        assert cs.finished
        assert not cs.player_won

    def test_eat_heals(self):
        state = _make_state()
        state.player.hp = 10
        state.player.inventory["food"] = 3
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        lines = cs.player_eat(state.player)
        assert state.player.hp == 15
        assert state.player.inventory["food"] == 2
        assert "+5" in lines[0]

    def test_eat_no_food(self):
        state = _make_state()
        state.player.inventory["food"] = 0
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        lines = cs.player_eat(state.player)
        assert "no food" in lines[0]

    def test_eat_caps_at_max(self):
        state = _make_state()
        state.player.hp = 28
        state.player.inventory["food"] = 2
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        cs.player_eat(state.player)
        assert state.player.hp == 30

    def test_flee_takes_damage(self):
        state = _make_state()
        state.player.hp = 20
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        cs.player_flee(state.player)
        assert state.player.hp == 17
        assert cs.finished
        assert cs.player_fled

    def test_flee_can_kill_player(self):
        state = _make_state()
        state.player.hp = 2
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        cs.player_flee(state.player)
        assert state.player.hp == 0
        assert cs.finished
        assert not cs.player_fled
        assert not cs.player_won

    def test_best_weapon_priority(self):
        cs = CombatState("x", {"name": "x", "hp": 1, "damage": 1, "symbol": "?"}, {"axe": 6, "spear": 5, "knife": 4, "machete": 3})
        w, d = cs.best_weapon({"spear": 1, "machete": 1})
        assert w == "spear"
        assert d == 5


class TestEncounterIntegration:

    def test_encounters_in_game_data(self):
        state = _make_state()
        thick = state.rooms.get("thick_forest")
        assert thick is not None
        assert "feral_boar" in thick.encounters

        river = state.rooms.get("riverbank")
        assert river is not None
        assert "snarling_wolf" in river.encounters

        light = state.rooms.get("lighthouse_interior")
        assert light is not None
        assert "gaunt_man" in light.encounters

    def test_clearing_has_no_encounters(self):
        state = _make_state()
        clearing = state.rooms.get("clearing")
        assert clearing.encounters == []

    def test_check_encounter_triggers(self):
        state = _make_state()
        state.current_room_id = "thick_forest"
        combat = state.check_encounter()
        assert combat is not None
        assert combat.enemy_id == "feral_boar"

    def test_check_encounter_none_for_cleared(self):
        state = _make_state()
        state.current_room_id = "thick_forest"
        state.player.defeated_enemies.add("thick_forest:feral_boar")
        combat = state.check_encounter()
        assert combat is None

    def test_finish_combat_marks_defeated(self):
        state = _make_state()
        state.current_room_id = "thick_forest"
        combat = state.check_encounter()
        combat.enemy_hp = 0
        combat.finished = True
        combat.player_won = True
        state.finish_combat()
        assert "thick_forest:feral_boar" in state.player.defeated_enemies
        assert state.combat is None

    def test_finish_combat_death_ends_game(self):
        state = _make_state()
        state.current_room_id = "thick_forest"
        combat = state.check_encounter()
        combat.finished = True
        combat.player_won = False
        combat.player_fled = False
        state.finish_combat()
        assert state.game_outcome == "died"
        assert not state.is_running

    def test_finish_combat_flee_keeps_running(self):
        state = _make_state()
        state.current_room_id = "thick_forest"
        combat = state.check_encounter()
        combat.finished = True
        combat.player_won = False
        combat.player_fled = True
        state.finish_combat()
        assert state.is_running
        assert "thick_forest:feral_boar" not in state.player.defeated_enemies


class TestSaveDefeatedEnemies:

    def test_defeated_survives_save_load(self):
        state = _make_state()
        state.player.defeated_enemies.add("thick_forest:feral_boar")
        snap = state.snapshot()
        assert "thick_forest:feral_boar" in snap["player"]["defeated_enemies"]

        state2 = _make_state()
        state2.apply_snapshot(snap)
        assert "thick_forest:feral_boar" in state2.player.defeated_enemies

    def test_no_encounter_after_load_with_defeated(self):
        state = _make_state()
        state.player.defeated_enemies.add("thick_forest:feral_boar")
        snap = state.snapshot()
        state2 = _make_state()
        state2.apply_snapshot(snap)
        state2.current_room_id = "thick_forest"
        assert state2.check_encounter() is None


class TestFoodToHealth:

    def test_eat_heals_after_combat_damage(self):
        state = _make_state()
        state.player.hp = 20
        state.player.inventory["food"] = 2
        lines = state.process_command("eat", None)
        assert state.player.hp == 25
        assert state.player.inventory["food"] == 1
        assert "recover" in lines[1].lower() or "5" in lines[1]

    def test_eat_at_full_hp_still_consumes_food(self):
        state = _make_state()
        state.player.hp = 30
        state.player.inventory["food"] = 1
        lines = state.process_command("eat", None)
        assert state.player.hp == 30
        assert state.player.inventory["food"] == 0
        assert "satisfied" in lines[1].lower()

    def test_eat_caps_at_max_hp(self):
        state = _make_state()
        state.player.hp = 27
        state.player.inventory["food"] = 1
        state.process_command("eat", None)
        assert state.player.hp == 30

    def test_eat_with_no_food(self):
        state = _make_state()
        state.player.hp = 10
        state.player.inventory["food"] = 0
        lines = state.process_command("eat", None)
        assert state.player.hp == 10
        assert "no food" in lines[0].lower()

    def test_hp_persists_after_save_load(self):
        state = _make_state()
        state.player.hp = 18
        state.player.inventory["food"] = 3
        snap = state.snapshot()
        assert snap["player"]["hp"] == 18

        state2 = _make_state()
        state2.apply_snapshot(snap)
        assert state2.player.hp == 18
        assert state2.player.inventory["food"] == 3

    def test_combat_damage_then_eat_then_save(self):
        state = _make_state()
        state.player.hp = 30
        state.player.inventory["food"] = 5
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 4, "symbol": "B"}, {})
        cs.enemy_attack(state.player)
        assert state.player.hp == 26
        cs.player_eat(state.player)
        assert state.player.hp == 30
        assert state.player.inventory["food"] == 4
        snap = state.snapshot()
        state2 = _make_state()
        state2.apply_snapshot(snap)
        assert state2.player.hp == 30
        assert state2.player.inventory["food"] == 4

    def test_eat_during_combat_costs_enemy_turn(self):
        state = _make_state()
        state.player.hp = 20
        state.player.inventory["food"] = 1
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 3, "symbol": "B"}, {})
        eat_lines = cs.player_eat(state.player)
        attack_lines = cs.enemy_attack(state.player)
        assert state.player.hp == 22
        assert "+5" in eat_lines[0]
        assert "strikes" in attack_lines[0]

    def test_eat_cooldown_blocks_consecutive_eat(self):
        state = _make_state()
        state.player.hp = 10
        state.player.inventory["food"] = 5
        cs = CombatState("boar", {"name": "boar", "hp": 20, "damage": 1, "symbol": "B"}, {})
        cs.player_eat(state.player)
        assert cs.eat_cooldown == 2
        lines = cs.player_eat(state.player)
        assert "still recovering" in lines[0]

    def test_eat_cooldown_ticks_on_attack(self):
        state = _make_state()
        state.player.hp = 10
        state.player.inventory["food"] = 5
        cs = CombatState("boar", {"name": "boar", "hp": 20, "damage": 1, "symbol": "B"}, {})
        cs.player_eat(state.player)
        assert cs.eat_cooldown == 2
        cs.player_attack(state.player.inventory)
        assert cs.eat_cooldown == 1
        cs.player_attack(state.player.inventory)
        assert cs.eat_cooldown == 0
        assert cs.can_eat()

    def test_can_eat_initially(self):
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 1, "symbol": "B"}, {})
        assert cs.can_eat()

    def test_status_shows_reduced_hp(self):
        state = _make_state()
        state.player.hp = 15
        lines = state.process_command("status", None)
        hp_line = [l for l in lines if "HP" in l][0]
        assert "15/30" in hp_line


class TestWeaponDamageFromJson:

    def test_weapon_damage_loaded(self):
        state = _make_state()
        assert state.weapon_damage.get("axe") == 6
        assert state.weapon_damage.get("spear") == 5
        assert state.weapon_damage.get("knife") == 4
        assert state.weapon_damage.get("machete") == 3

    def test_enemy_data_loaded(self):
        state = _make_state()
        assert "feral_boar" in state.enemies
        assert state.enemies["feral_boar"]["hp"] == 8
        assert state.enemies["snarling_wolf"]["damage"] == 4
        assert state.enemies["gaunt_man"]["symbol"] == "M"
