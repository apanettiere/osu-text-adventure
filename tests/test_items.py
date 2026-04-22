"""
test_items.py - Sprint 1 item tests.
Covers item registry, read command, lantern uses, hidden loot,
examine clues, conditional descriptions, drop/retake, weight warnings,
and the full sprint 1 puzzle progression.
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from engine.game_state import GameState


@pytest.fixture
def gs():
    return GameState()


def teleport(gs, room_id):
    gs.current_room_id = room_id
    room = gs.rooms[room_id]
    gs.local_x = room.width  // 2
    gs.local_y = room.height // 2
    gs.player.explored_rooms.add(room_id)
    gs.player.discovered_rooms.add(room_id)


def at_edge(gs, direction):
    room = gs.rooms[gs.current_room_id]
    if direction == "north": gs.local_y = 0
    if direction == "south": gs.local_y = room.height - 1
    if direction == "east":  gs.local_x = room.width  - 1
    if direction == "west":  gs.local_x = 0


class TestItemRegistry:
    def test_all_expected_items_present(self, gs):
        expected = {"wood", "stone", "food", "machete", "lantern", "climbing_gear", "raft", "note", "old_map"}
        assert expected <= set(gs.item_registry.keys())

    def test_resources_have_correct_weights(self, gs):
        assert gs.item_registry["wood"]["weight"]  == 1
        assert gs.item_registry["stone"]["weight"] == 2
        assert gs.item_registry["food"]["weight"]  == 1

    def test_machete_weight(self, gs):
        assert gs.item_registry["machete"]["weight"] == 3

    def test_lantern_weight(self, gs):
        assert gs.item_registry["lantern"]["weight"] == 2

    def test_raft_weight(self, gs):
        assert gs.item_registry["raft"]["weight"] == 8

    def test_old_map_is_weightless(self, gs):
        assert gs.item_registry["old_map"]["weight"] == 0

    def test_old_map_is_readable(self, gs):
        assert gs.item_registry["old_map"].get("readable") is True

    def test_lantern_has_uses_field(self, gs):
        assert gs.item_registry["lantern"]["uses"] == 30

    def test_all_items_have_desc(self, gs):
        for name, data in gs.item_registry.items():
            assert "desc" in data, f"{name} missing desc"

    def test_all_items_have_type(self, gs):
        for name, data in gs.item_registry.items():
            assert "type" in data, f"{name} missing type"


class TestReadCommand:
    def test_old_map_in_cave_loot(self, gs):
        assert gs.rooms["cave_entrance"].loot.get("old_map", 0) == 1

    def test_read_without_old_map_fails(self, gs):
        result = gs.process_command("read", "old_map")
        assert any("not carrying" in l.lower() for l in result)

    def test_note_is_readable_from_clearing(self, gs):
        result = gs.process_command("read", "note")
        full = " ".join(result).lower()
        assert "goal" in full or "lighthouse" in full

    def test_take_old_map_adds_to_inventory(self, gs):
        teleport(gs, "cave_entrance")
        gs.rooms["cave_entrance"].loot_hidden["old_map"] = False
        gs.process_command("take", "old_map")
        assert gs.player.inventory.get("old_map", 0) == 1

    def test_read_old_map_after_taking(self, gs):
        gs.player.inventory["old_map"] = 1
        result = gs.process_command("read", "old_map")
        assert any("OLD MAP" in l.upper() or "---" in l for l in result)

    def test_read_old_map_contains_lighthouse(self, gs):
        gs.player.inventory["old_map"] = 1
        result = gs.process_command("read", "old_map")
        full = " ".join(result).lower()
        assert "lighthouse" in full or "escape" in full

    def test_bare_read_defaults_to_readable_in_inventory(self, gs):
        gs.player.inventory["old_map"] = 1
        result = gs.process_command("read", None)
        assert any("OLD MAP" in l.upper() or "---" in l for l in result)

    def test_cannot_read_non_readable_item(self, gs):
        gs.player.inventory["wood"] = 2
        result = gs.process_command("read", "wood")
        assert any("cannot read" in l.lower() for l in result)

    def test_read_with_nothing_readable(self, gs):
        result = gs.process_command("read", None)
        assert any("not carrying" in l.lower() or "nothing" in l.lower() for l in result)


class TestLantern:
    def _give_lantern(self, gs):
        gs.player.inventory["lantern"] = 1
        gs.player.torch_uses = gs.item_registry["lantern"]["uses"]

    def test_lantern_starts_with_30_uses(self, gs):
        self._give_lantern(gs)
        assert gs.player.torch_uses == 30

    def test_tick_decrements_lantern(self, gs):
        self._give_lantern(gs)
        gs._tick_torch()
        assert gs.player.torch_uses == 29

    def test_tick_at_7_gives_warning(self, gs):
        self._give_lantern(gs)
        gs.player.torch_uses = 8
        result = gs._tick_torch()
        assert any("burning low" in l.lower() for l in result)

    def test_tick_at_3_gives_urgent_warning(self, gs):
        self._give_lantern(gs)
        gs.player.torch_uses = 4
        result = gs._tick_torch()
        assert any("almost out" in l.lower() for l in result)

    def test_lantern_burns_out_at_zero(self, gs):
        self._give_lantern(gs)
        gs.player.torch_uses = 1
        result = gs._tick_torch()
        assert any("relight" in l.lower() or "reserve oil" in l.lower() for l in result)
        assert gs.player.torch_uses == gs.item_registry["lantern"]["uses"]

    def test_lantern_stays_in_inventory_on_burnout(self, gs):
        self._give_lantern(gs)
        gs.player.torch_uses = 1
        gs._tick_torch()
        assert gs.player.inventory.get("lantern", 0) == 1

    def test_no_tick_without_lantern(self, gs):
        result = gs._tick_torch()
        assert result == []

    def test_movement_ticks_lantern(self, gs):
        teleport(gs, "clearing")
        gs.player.inventory["lantern"] = 1
        gs.player.torch_uses = 30
        gs.process_command("go", "north")
        assert gs.player.torch_uses < 30


class TestHiddenLoot:
    def test_lantern_hidden_in_thick_forest(self, gs):
        assert "lantern" not in gs.rooms["thick_forest"].visible_loot()

    def test_raft_hidden_in_thick_forest(self, gs):
        assert "raft" not in gs.rooms["thick_forest"].visible_loot()

    def test_climbing_gear_not_in_thick_forest(self, gs):
        assert "climbing_gear" not in gs.rooms["thick_forest"].visible_loot()

    def test_cabin_interior_has_visible_lantern_and_raft(self, gs):
        teleport(gs, "thick_forest")
        gs.process_command("enter", "cabin")
        assert gs.current_room_id == "cabin_interior"
        assert "lantern" in gs.rooms["cabin_interior"].visible_loot()
        assert "raft" in gs.rooms["cabin_interior"].visible_loot()

    def test_examine_cabin_message_mentions_lantern(self, gs):
        teleport(gs, "thick_forest")
        result = gs.process_command("examine", "cabin")
        assert any("lantern" in l.lower() for l in result)

    def test_examine_cabin_message_mentions_raft(self, gs):
        teleport(gs, "thick_forest")
        result = gs.process_command("examine", "cabin")
        assert any("raft" in l.lower() for l in result)

    def test_lantern_takeable_after_reveal(self, gs):
        teleport(gs, "thick_forest")
        gs.process_command("enter", "cabin")
        gs.process_command("take", "lantern")
        assert gs.player.inventory.get("lantern", 0) == 1

    def test_climbing_gear_takeable_in_cabin_interior(self, gs):
        teleport(gs, "cabin_interior")
        result = gs.process_command("take", "climbing_gear")
        assert gs.player.inventory.get("climbing_gear", 0) == 1

    def test_enter_cabin_moves_to_interior_with_loot(self, gs):
        teleport(gs, "thick_forest")
        gs.process_command("enter", "cabin")
        assert gs.current_room_id == "cabin_interior"
        assert "lantern" in gs.rooms["cabin_interior"].visible_loot()

    def test_raft_not_takeable_before_reveal(self, gs):
        teleport(gs, "thick_forest")
        gs.process_command("take", "raft")
        assert gs.player.inventory.get("raft", 0) == 0


class TestExamineClues:
    def test_examine_stump_gives_clue(self, gs):
        result = gs.process_command("examine", "stump")
        full = " ".join(result).lower()
        assert "blade" in full or "machete" in full or "take" in full

    def test_examine_firepit_gives_direction_clue(self, gs):
        result = gs.process_command("examine", "firepit")
        full = " ".join(result).lower()
        assert "north" in full or "arrow" in full or "something" in full

    def test_examine_unknown_feature_fails_gracefully(self, gs):
        result = gs.process_command("examine", "nothing_here")
        assert result

    def test_examine_inventory_item_shows_weight(self, gs):
        gs.player.inventory["machete"] = 1
        result = gs.process_command("examine", "machete")
        assert any("kg" in l.lower() or "weight" in l.lower() for l in result)

    def test_examine_flat_stone_mentions_map(self, gs):
        teleport(gs, "cave_entrance")
        result = gs.process_command("examine", "flat_stone")
        full = " ".join(result).lower()
        assert "map" in full or "oilskin" in full


class TestConditionalDescriptions:
    def test_clearing_base_desc_no_lantern(self, gs):
        desc = gs.rooms["clearing"].get_description(gs.player.inventory)
        assert "boot prints" not in desc.lower()

    def test_clearing_extra_desc_with_lantern(self, gs):
        gs.player.inventory["lantern"] = 1
        desc = gs.rooms["clearing"].get_description(gs.player.inventory)
        assert "lantern" in desc.lower() or "light" in desc.lower()

    def test_riverbank_extra_desc_with_raft(self, gs):
        gs.player.inventory["raft"] = 1
        desc = gs.rooms["riverbank"].get_description(gs.player.inventory)
        assert "raft" in desc.lower() or "launch" in desc.lower()

    def test_thick_forest_extra_desc_with_lantern(self, gs):
        gs.player.inventory["lantern"] = 1
        desc = gs.rooms["thick_forest"].get_description(gs.player.inventory)
        assert "lantern" in desc.lower() or "light" in desc.lower()

    def test_look_command_includes_conditional_desc(self, gs):
        gs.player.inventory["lantern"] = 1
        result = gs.process_command("look", None)
        full = " ".join(result).lower()
        assert "lantern" in full or "light" in full


class TestDropAndRetake:
    def test_drop_removes_from_inventory(self, gs):
        gs.player.inventory["wood"] = 2
        gs.process_command("drop", "wood")
        assert gs.player.inventory["wood"] == 1

    def test_drop_adds_to_room_loot(self, gs):
        gs.player.inventory["wood"] = 1
        gs.process_command("drop", "wood")
        room = gs.rooms[gs.current_room_id]
        assert room.loot.get("wood", 0) >= 1

    def test_dropped_item_becomes_visible(self, gs):
        gs.player.inventory["machete"] = 1
        gs.process_command("drop", "machete")
        room = gs.rooms[gs.current_room_id]
        assert "machete" in room.visible_loot()

    def test_can_retake_dropped_item(self, gs):
        gs.player.inventory["stone"] = 1
        gs.process_command("drop", "stone")
        gs.process_command("take", "stone")
        assert gs.player.inventory.get("stone", 0) == 1

    def test_drop_nothing_gives_error(self, gs):
        result = gs.process_command("drop", "raft")
        assert any("not carrying" in l.lower() for l in result)

    def test_drop_with_no_target(self, gs):
        result = gs.process_command("drop", None)
        assert result


class TestWeightWarnings:
    def test_no_warning_when_light(self, gs):
        gs.player.inventory["wood"] = 1
        result = gs.process_command("look", None)
        assert not any("heavy" in l.lower() or "full" in l.lower() for l in result)

    def test_heavy_warning_at_85_percent(self, gs):
        gs.player.inventory["stone"] = 8
        gs.player.inventory["wood"]  = 1
        result = gs.process_command("look", None)
        assert any("heavy" in l.lower() for l in result)

    def test_full_warning_at_100_percent(self, gs):
        gs.player.inventory["stone"] = 10
        result = gs.process_command("look", None)
        assert any("full" in l.lower() or "barely" in l.lower() for l in result)

    def test_warning_gone_after_drop(self, gs):
        gs.player.inventory["stone"] = 10
        gs.process_command("drop", "stone")
        result = gs.process_command("look", None)
        assert not any("full" in l.lower() for l in result)

    def test_movement_message_changes_when_full(self, gs):
        teleport(gs, "clearing")
        gs.player.inventory["stone"] = 10
        result = gs.process_command("go", "north")
        assert any("strain" in l.lower() or "weight" in l.lower() for l in result)


class TestPuzzleFlows:
    def test_thick_forest_blocked_without_machete(self, gs):
        at_edge(gs, "north")
        result = gs.process_command("go", "north")
        assert any("machete" in l.lower() for l in result)
        assert gs.current_room_id == "clearing"

    def test_machete_visible_in_clearing(self, gs):
        assert "machete" in gs.rooms["clearing"].visible_loot()

    def test_take_machete_adds_to_inventory(self, gs):
        gs.process_command("take", "machete")
        assert gs.player.inventory.get("machete", 0) == 1

    def test_machete_unlocks_thick_forest(self, gs):
        gs.process_command("take", "machete")
        at_edge(gs, "north")
        gs.process_command("go", "north")
        assert gs.current_room_id == "thick_forest"

    def test_cave_blocked_without_lantern(self, gs):
        at_edge(gs, "east")
        result = gs.process_command("go", "east")
        assert any("lantern" in l.lower() for l in result)
        assert gs.current_room_id == "clearing"

    def test_cave_unlocked_with_lantern(self, gs):
        gs.player.inventory["lantern"] = 1
        at_edge(gs, "east")
        gs.process_command("go", "east")
        assert gs.current_room_id == "cave_entrance"

    def test_river_lake_blocked_without_raft(self, gs):
        teleport(gs, "riverbank")
        at_edge(gs, "east")
        result = gs.process_command("go", "east")
        assert gs.current_room_id == "riverbank"
        assert any("raft" in l.lower() for l in result)

    def test_riverbank_west_stays_in_room(self, gs):
        teleport(gs, "riverbank")
        x_before = gs.local_x
        y_before = gs.local_y
        result = gs.process_command("go", "west")
        assert gs.current_room_id == "riverbank"
        assert gs.local_x == x_before - 1
        assert gs.local_y == y_before
        assert any("move west" in l.lower() for l in result)

    def test_far_shore_accessible_from_river_lake(self, gs):
        gs.player.inventory["raft"] = 1
        teleport(gs, "river_lake")
        at_edge(gs, "south")
        gs.process_command("go", "south")
        assert gs.current_room_id == "far_shore"

    def test_riverbank_west_to_river_run_blocked_without_raft(self, gs):
        teleport(gs, "riverbank")
        at_edge(gs, "west")
        result = gs.process_command("go", "west")
        assert gs.current_room_id == "riverbank"
        assert any("raft" in l.lower() for l in result)

    def test_riverbank_west_to_river_run_with_raft(self, gs):
        gs.player.inventory["raft"] = 1
        teleport(gs, "riverbank")
        at_edge(gs, "west")
        gs.process_command("go", "west")
        assert gs.current_room_id == "river_run"

    def test_river_run_west_to_mountain_pass_with_raft(self, gs):
        gs.player.inventory["raft"] = 1
        teleport(gs, "river_run")
        at_edge(gs, "west")
        gs.process_command("go", "west")
        assert gs.current_room_id == "mountain_pass"

    def test_raft_found_in_cabin(self, gs):
        teleport(gs, "thick_forest")
        gs.process_command("enter", "cabin")
        assert "raft" in gs.rooms["cabin_interior"].visible_loot()

    def test_climbing_gear_found_in_cabin(self, gs):
        teleport(gs, "cabin_interior")
        assert "climbing_gear" in gs.rooms["cabin_interior"].visible_loot()

    def test_raft_unlocks_far_shore(self, gs):
        gs.player.inventory["raft"] = 1
        teleport(gs, "riverbank")
        at_edge(gs, "east")
        gs.process_command("go", "east")
        assert gs.current_room_id == "river_lake"
        at_edge(gs, "south")
        gs.process_command("go", "south")
        assert gs.current_room_id == "far_shore"

    def test_mountain_pass_blocked_without_climbing_gear(self, gs):
        at_edge(gs, "west")
        result = gs.process_command("go", "west")
        assert any("climbing" in l.lower() or "gear" in l.lower() for l in result)

    def test_use_machete_enters_thick_forest(self, gs):
        gs.player.inventory["machete"] = 1
        at_edge(gs, "north")
        result = gs.process_command("use", "machete")
        assert gs.current_room_id == "thick_forest"

    def test_use_lantern_enters_cave(self, gs):
        gs.player.inventory["lantern"] = 1
        gs.player.torch_uses = 30
        at_edge(gs, "east")
        result = gs.process_command("use", "lantern")
        assert gs.current_room_id == "cave_entrance"

    def test_use_raft_prepares_navigation(self, gs):
        gs.player.inventory["raft"] = 1
        teleport(gs, "riverbank")
        at_edge(gs, "south")
        result = gs.process_command("use", "raft")
        assert gs.current_room_id == "riverbank"
        assert any("go north" in l.lower() or "go south" in l.lower() for l in result)

    def test_old_map_in_cave(self, gs):
        assert gs.rooms["cave_entrance"].loot.get("old_map", 0) == 1

    def test_full_sprint1_chain(self, gs):
        gs2 = GameState()
        gs2.process_command("take", "machete")
        at_edge(gs2, "north")
        gs2.process_command("go", "north")
        assert gs2.current_room_id == "thick_forest"
        gs2.process_command("enter", "cabin")
        gs2.process_command("take", "lantern")
        gs2.process_command("take", "raft")
        gs2.process_command("take", "climbing_gear")
        teleport(gs2, "clearing")
        at_edge(gs2, "east")
        gs2.process_command("go", "east")
        assert gs2.current_room_id == "cave_entrance"
        gs2.process_command("take", "old_map")
        assert gs2.player.inventory.get("old_map", 0) == 1
        gs2.process_command("enter", "cave")
        assert gs2.current_room_id == "cave_chamber"
        assert gs2.player.inventory.get("climbing_gear", 0) == 1


class TestLighthouseWinCondition:
    def test_enter_lighthouse_goes_to_interior(self, gs):
        teleport(gs, "mountain_pass")
        gs.process_command("enter", "lighthouse")
        assert gs.current_room_id == "lighthouse_interior"

    def test_enter_top_goes_to_lantern_room(self, gs):
        teleport(gs, "lighthouse_interior")
        gs.process_command("enter", "top")
        assert gs.current_room_id == "lighthouse_top"

    def test_light_lighthouse_signal_ends_game(self, gs):
        teleport(gs, "lighthouse_top")
        result = gs.process_command("use", "lighthouse_light")
        full = " ".join(result).lower()
        assert "sos" in full
        assert gs.is_running is False
        assert gs.game_outcome == "won"
        assert gs.end_lines
