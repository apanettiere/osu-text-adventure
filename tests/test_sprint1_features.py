import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from engine.game_state import GameState
from engine.parser import parse_command


@pytest.fixture
def gs():
    return GameState()


class TestSaveCommand:
    def test_save_returns_confirmation(self, gs):
        lines = gs.process_command("save", None)
        assert any("saved" in ln.lower() for ln in lines)

    def test_save_parsed_correctly(self):
        verb, target = parse_command("save")
        assert verb == "save"
        assert target is None

    def test_game_still_running_after_save(self, gs):
        gs.process_command("save", None)
        assert gs.is_running is True


class TestStatusCommand:
    def test_status_shows_hp(self, gs):
        lines = gs.process_command("status", None)
        full = " ".join(lines).lower()
        assert "hp" in full

    def test_status_shows_location(self, gs):
        lines = gs.process_command("status", None)
        full = " ".join(lines)
        assert "Forest Clearing" in full

    def test_status_shows_carry_weight(self, gs):
        lines = gs.process_command("status", None)
        full = " ".join(lines).lower()
        assert "carry weight" in full

    def test_status_shows_rooms_explored(self, gs):
        lines = gs.process_command("status", None)
        full = " ".join(lines).lower()
        assert "rooms explored" in full

    def test_status_parsed_correctly(self):
        verb, target = parse_command("status")
        assert verb == "status"

    def test_stats_alias_works(self):
        verb, target = parse_command("stats")
        assert verb == "status"

    def test_hp_alias_works(self):
        verb, target = parse_command("hp")
        assert verb == "status"


class TestEatCommand:
    def test_eat_consumes_food(self, gs):
        gs.player.inventory["food"] = 3
        gs.process_command("eat", None)
        assert gs.player.inventory["food"] == 2

    def test_eat_heals_hp(self, gs):
        gs.player.hp = 20
        gs.player.inventory["food"] = 2
        gs.process_command("eat", None)
        assert gs.player.hp == 25

    def test_eat_does_not_exceed_max_hp(self, gs):
        gs.player.hp = 28
        gs.player.inventory["food"] = 2
        gs.process_command("eat", None)
        assert gs.player.hp == gs.player.max_hp

    def test_eat_at_full_hp_shows_satisfied(self, gs):
        gs.player.hp = gs.player.max_hp
        gs.player.inventory["food"] = 1
        lines = gs.process_command("eat", None)
        full = " ".join(lines).lower()
        assert "satisfied" in full

    def test_eat_with_no_food(self, gs):
        gs.player.inventory["food"] = 0
        lines = gs.process_command("eat", None)
        full = " ".join(lines).lower()
        assert "no food" in full

    def test_eat_non_food_item(self, gs):
        lines = gs.process_command("eat", "stone")
        full = " ".join(lines).lower()
        assert "cannot eat" in full

    def test_eat_shows_recovery_amount(self, gs):
        gs.player.hp = 20
        gs.player.inventory["food"] = 1
        lines = gs.process_command("eat", None)
        full = " ".join(lines).lower()
        assert "recover" in full
        assert "5" in full

    def test_eat_parsed_correctly(self):
        verb, target = parse_command("eat")
        assert verb == "eat"

    def test_consume_alias_works(self):
        verb, target = parse_command("consume food")
        assert verb == "eat"
        assert target == "food"

    def test_eat_with_explicit_food_target(self, gs):
        gs.player.inventory["food"] = 1
        lines = gs.process_command("eat", "food")
        full = " ".join(lines).lower()
        assert "eat" in full


class TestTorchAsLightSource:
    def test_cave_blocked_without_any_light(self, gs):
        gs.player.inventory["machete"] = 1
        room = gs.rooms["clearing"]
        gs.local_x = room.width - 1
        gs.local_y = room.height // 2
        lines = gs.process_command("go", "east")
        full = " ".join(lines).lower()
        assert "lantern" in full or "pitch black" in full

    def test_cave_accessible_with_lantern(self, gs):
        gs.player.inventory["machete"] = 1
        gs.player.inventory["lantern"] = 1
        room = gs.rooms["clearing"]
        gs.local_x = room.width - 1
        gs.local_y = room.height // 2
        lines = gs.process_command("go", "east")
        assert gs.current_room_id == "cave_entrance"

    def test_cave_accessible_with_torch(self, gs):
        gs.player.inventory["machete"] = 1
        gs.player.inventory["torch"] = 1
        room = gs.rooms["clearing"]
        gs.local_x = room.width - 1
        gs.local_y = room.height // 2
        lines = gs.process_command("go", "east")
        assert gs.current_room_id == "cave_entrance"

    def test_cave_still_blocked_without_light_or_torch(self, gs):
        gs.player.inventory["machete"] = 1
        gs.player.inventory["knife"] = 1
        room = gs.rooms["clearing"]
        gs.local_x = room.width - 1
        gs.local_y = room.height // 2
        lines = gs.process_command("go", "east")
        assert gs.current_room_id == "clearing"


class TestRaftCraftingRecipe:
    def test_raft_recipe_exists(self, gs):
        assert "raft" in gs.recipes

    def test_raft_recipe_requires_wood_and_stone(self, gs):
        requires = gs.recipes["raft"]["requires"]
        assert "wood" in requires
        assert "stone" in requires

    def test_craft_raft_with_enough_resources(self, gs):
        gs.player.inventory["wood"] = 4
        gs.player.inventory["stone"] = 1
        lines = gs.process_command("craft", "raft")
        assert gs.player.inventory.get("raft", 0) == 1
        assert gs.player.inventory["wood"] == 0
        assert gs.player.inventory["stone"] == 0

    def test_craft_raft_fails_without_enough_wood(self, gs):
        gs.player.inventory["wood"] = 2
        gs.player.inventory["stone"] = 1
        lines = gs.process_command("craft", "raft")
        full = " ".join(lines).lower()
        assert "cannot craft" in full
        assert gs.player.inventory.get("raft", 0) == 0

    def test_crafted_raft_enables_water_crossing(self, gs):
        gs.player.inventory["wood"] = 4
        gs.player.inventory["stone"] = 1
        gs.process_command("craft", "raft")
        assert gs.player.inventory.get("raft", 0) == 1

    def test_raft_recipe_in_recipe_list(self, gs):
        lines = gs.process_command("craft", "list")
        full = " ".join(lines).lower()
        assert "raft" in full


class TestHelpIncludesNewCommands:
    def test_help_mentions_eat(self, gs):
        lines = gs.process_command("help", None)
        full = " ".join(lines).lower()
        assert "eat" in full

    def test_help_mentions_status(self, gs):
        lines = gs.process_command("help", None)
        full = " ".join(lines).lower()
        assert "status" in full

    def test_help_mentions_save(self, gs):
        lines = gs.process_command("help", None)
        full = " ".join(lines).lower()
        assert "save" in full
