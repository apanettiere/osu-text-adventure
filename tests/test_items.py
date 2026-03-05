"""
test_all_items.py
Comprehensive tests for every item feature:
  - item registry (weight, type, special fields)
  - note / readable items + read command
  - backpack carry bonus
  - torch uses + burn-out
  - hidden loot revealed by examine
  - examine clues on features
  - conditional room descriptions
  - combine command
  - drop and re-take
  - weight warnings in room descriptions
  - full unlock flows
"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from engine.game_state import GameState


@pytest.fixture
def gs():
    return GameState()


def teleport(gs, room_id):
    """Instantly move GameState to a room, positioned at centre."""
    gs.current_room_id = room_id
    room = gs.rooms[room_id]
    gs.local_x = room.width  // 2
    gs.local_y = room.height // 2
    gs.player.explored_rooms.add(room_id)
    gs.player.discovered_rooms.add(room_id)


def at_edge(gs, direction):
    """Move player to the exit edge of current room in given direction."""
    room = gs.rooms[gs.current_room_id]
    if direction == "north": gs.local_y = 0
    if direction == "south": gs.local_y = room.height - 1
    if direction == "east":  gs.local_x = room.width - 1
    if direction == "west":  gs.local_x = 0


class TestItemRegistry:
    """Every item in the registry has the right shape."""

    def test_all_expected_items_present(self, gs):
        expected = {"wood","stone","food","machete","axe","climbing_gear",
                    "raft","torch","note","backpack"}
        assert expected <= set(gs.item_registry.keys())

    def test_resources_have_weight_1_or_2(self, gs):
        assert gs.item_registry["wood"]["weight"]  == 1
        assert gs.item_registry["stone"]["weight"] == 2
        assert gs.item_registry["food"]["weight"]  == 1

    def test_tools_have_correct_weights(self, gs):
        assert gs.item_registry["machete"]["weight"]       == 3
        assert gs.item_registry["axe"]["weight"]           == 4
        assert gs.item_registry["climbing_gear"]["weight"] == 5

    def test_crafted_items_have_correct_weights(self, gs):
        assert gs.item_registry["raft"]["weight"]  == 8
        assert gs.item_registry["torch"]["weight"] == 1

    def test_note_is_weightless(self, gs):
        assert gs.item_registry["note"]["weight"] == 0

    def test_note_is_readable(self, gs):
        assert gs.item_registry["note"].get("readable") is True

    def test_backpack_has_carry_bonus(self, gs):
        assert gs.item_registry["backpack"]["carry_bonus"] == 15

    def test_torch_has_uses_field(self, gs):
        assert gs.item_registry["torch"]["uses"] == 15

    def test_all_items_have_desc(self, gs):
        for name, data in gs.item_registry.items():
            assert "desc" in data, f"{name} missing desc"

    def test_all_items_have_type(self, gs):
        for name, data in gs.item_registry.items():
            assert "type" in data, f"{name} missing type"


class TestReadCommand:
    def test_note_in_clearing_loot(self, gs):
        assert gs.rooms["clearing"].loot.get("note", 0) == 1

    def test_note_visible_in_clearing(self, gs):
        room = gs.rooms["clearing"]
        assert "note" in room.visible_loot()

    def test_read_without_note_fails(self, gs):
        result = gs.process_command("read", "note")
        assert any("not carrying" in l.lower() or "not" in l.lower() for l in result)

    def test_take_note_adds_to_inventory(self, gs):
        gs.process_command("take", "note")
        assert gs.player.inventory.get("note", 0) == 1

    def test_read_note_after_taking(self, gs):
        gs.process_command("take", "note")
        result = gs.process_command("read", "note")
        assert any("NOTE" in l.upper() or "---" in l for l in result)

    def test_read_note_contains_survivor_content(self, gs):
        gs.process_command("take", "note")
        result = gs.process_command("read", "note")
        full = " ".join(result).lower()
        assert "river" in full or "boulder" in full or "raft" in full

    def test_read_note_signed_r(self, gs):
        gs.process_command("take", "note")
        result = gs.process_command("read", "note")
        assert any("— r" in l.lower() or "- r" in l.lower() or l.strip() == "— R" for l in result)

    def test_cannot_read_non_readable_item(self, gs):
        gs.player.inventory["wood"] = 2
        result = gs.process_command("read", "wood")
        assert any("cannot read" in l.lower() for l in result)

    def test_bare_read_defaults_to_note(self, gs):
        gs.process_command("take", "note")
        result = gs.process_command("read", None)
        assert any("NOTE" in l.upper() or "---" in l for l in result)



class TestBackpack:
    def test_default_carry_limit_is_20(self, gs):
        assert gs.player.carry_limit(gs.item_registry) == 20.0

    def test_backpack_in_fallen_pines_loot(self, gs):
        assert gs.rooms["fallen_pines"].loot.get("backpack", 0) == 1

    def test_backpack_hidden_by_default(self, gs):
        room = gs.rooms["fallen_pines"]
        assert "backpack" not in room.visible_loot()

    def test_backpack_revealed_by_examining_lantern(self, gs):
        teleport(gs, "fallen_pines")
        gs.process_command("examine", "lantern")
        room = gs.rooms["fallen_pines"]
        assert "backpack" in room.visible_loot()

    def test_carry_limit_increases_after_taking_backpack(self, gs):
        teleport(gs, "fallen_pines")
        gs.process_command("examine", "lantern")
        gs.process_command("take", "backpack")
        assert gs.player.carry_limit(gs.item_registry) == 35.0

    def test_carry_limit_message_in_take_output(self, gs):
        teleport(gs, "fallen_pines")
        gs.process_command("examine", "lantern")
        result = gs.process_command("take", "backpack")
        assert any("35" in l or "carry" in l.lower() for l in result)

    def test_weight_bar_uses_dynamic_limit(self, gs):
        teleport(gs, "fallen_pines")
        gs.process_command("examine", "lantern")
        gs.process_command("take", "backpack")
        lines = gs.player.get_inventory_lines(gs.item_registry)
        assert any("35" in l for l in lines)



class TestTorch:
    def _give_torch(self, gs):
        gs.player.inventory["torch"] = 1
        gs.player.torch_uses = gs.item_registry["torch"]["uses"]

    def test_torch_starts_with_15_uses(self, gs):
        self._give_torch(gs)
        assert gs.player.torch_uses == 15

    def test_tick_torch_decrements(self, gs):
        self._give_torch(gs)
        gs._tick_torch()
        assert gs.player.torch_uses == 14

    def test_tick_at_7_gives_warning(self, gs):
        self._give_torch(gs)
        gs.player.torch_uses = 8
        result = gs._tick_torch()
        assert any("burning low" in l.lower() for l in result)

    def test_tick_at_3_gives_urgent_warning(self, gs):
        self._give_torch(gs)
        gs.player.torch_uses = 4
        result = gs._tick_torch()
        assert any("almost out" in l.lower() for l in result)

    def test_torch_burns_out_at_zero(self, gs):
        self._give_torch(gs)
        gs.player.torch_uses = 1
        result = gs._tick_torch()
        assert any("dies" in l.lower() or "darkness" in l.lower() for l in result)

    def test_torch_removed_from_inventory_on_burnout(self, gs):
        self._give_torch(gs)
        gs.player.torch_uses = 1
        gs._tick_torch()
        assert gs.player.inventory.get("torch", 0) == 0

    def test_torch_uses_reset_to_none_on_burnout(self, gs):
        self._give_torch(gs)
        gs.player.torch_uses = 1
        gs._tick_torch()
        assert gs.player.torch_uses is None

    def test_no_tick_without_torch(self, gs):
        result = gs._tick_torch()
        assert result == []

    def test_movement_ticks_torch(self, gs):
        teleport(gs, "clearing")
        gs.player.inventory["torch"] = 1
        gs.player.torch_uses = 15
        gs.process_command("go", "north")   # intra-room step
        assert gs.player.torch_uses < 15



class TestHiddenLoot:
    def test_axe_hidden_in_shadow_trees(self, gs):
        room = gs.rooms["shadow_trees"]
        assert "axe" not in room.visible_loot()

    def test_axe_revealed_after_examine_boulder(self, gs):
        teleport(gs, "shadow_trees")
        gs.process_command("examine", "boulder")
        room = gs.rooms["shadow_trees"]
        assert "axe" in room.visible_loot()

    def test_examine_boulder_message_mentions_axe(self, gs):
        teleport(gs, "shadow_trees")
        result = gs.process_command("examine", "boulder")
        assert any("axe" in l.lower() for l in result)

    def test_axe_takeable_after_reveal(self, gs):
        teleport(gs, "shadow_trees")
        gs.process_command("examine", "boulder")
        gs.process_command("take", "axe")
        assert gs.player.inventory.get("axe", 0) == 1

    def test_axe_not_takeable_before_reveal(self, gs):
        teleport(gs, "shadow_trees")
        result = gs.process_command("take", "axe")
        assert gs.player.inventory.get("axe", 0) == 0

    def test_backpack_hidden_in_fallen_pines(self, gs):
        room = gs.rooms["fallen_pines"]
        assert "backpack" not in room.visible_loot()

    def test_backpack_revealed_by_lantern(self, gs):
        teleport(gs, "fallen_pines")
        gs.process_command("examine", "lantern")
        assert "backpack" in gs.rooms["fallen_pines"].visible_loot()



class TestExamineClues:
    def test_examine_well_gives_clue(self, gs):
        result = gs.process_command("examine", "well")
        full = " ".join(result).lower()
        assert "w" in full and ("west" in full or "north" in full or "directions" in full or "letters" in full)

    def test_examine_tracks_mentions_origin(self, gs):
        result = gs.process_command("examine", "tracks")
        full = " ".join(result).lower()
        assert "north" in full or "shadow" in full or "clearing" in full

    def test_examine_inscription_mentions_tower(self, gs):
        teleport(gs, "stone_foothills")
        result = gs.process_command("examine", "inscription")
        assert any("tower" in l.lower() for l in result)

    def test_examine_cup_mentions_initial_r(self, gs):
        teleport(gs, "soggy_path")
        result = gs.process_command("examine", "cup")
        full = " ".join(result).lower()
        assert "r" in full and ("note" in full or "initial" in full or "name" in full or "same" in full or "letter" in full or "scratched" in full)

    def test_examine_scratches_shadow_trees(self, gs):
        teleport(gs, "shadow_trees")
        result = gs.process_command("examine", "scratches")
        full = " ".join(result).lower()
        assert "hands" in full or "fingers" in full or "south" in full or "regular" in full

    def test_examine_unknown_feature_fails_gracefully(self, gs):
        result = gs.process_command("examine", "nothing_here")
        assert result  # returns something, doesn't crash

    def test_examine_own_inventory_item(self, gs):
        gs.player.inventory["machete"] = 1
        result = gs.process_command("examine", "machete")
        assert any("machete" in l.lower() for l in result)
        assert any("kg" in l.lower() or "weight" in l.lower() for l in result)



class TestConditionalDescriptions:
    def test_clearing_base_desc_no_torch(self, gs):
        desc = gs.rooms["clearing"].get_description(gs.player.inventory)
        assert "torch" not in desc.lower() or "torchlight" not in desc.lower()

    def test_clearing_extra_desc_with_torch(self, gs):
        gs.player.inventory["torch"] = 1
        desc = gs.rooms["clearing"].get_description(gs.player.inventory)
        assert "torch" in desc.lower() or "light" in desc.lower()

    def test_shadow_trees_extra_desc_with_machete(self, gs):
        gs.player.inventory["machete"] = 1
        desc = gs.rooms["shadow_trees"].get_description(gs.player.inventory)
        assert "machete" in desc.lower() or "hold" in desc.lower() or "answer" in desc.lower()

    def test_soggy_path_extra_desc_with_raft(self, gs):
        gs.player.inventory["raft"] = 1
        desc = gs.rooms["soggy_path"].get_description(gs.player.inventory)
        assert "raft" in desc.lower() or "heavy" in desc.lower()

    def test_stone_foothills_extra_desc_with_climbing_gear(self, gs):
        gs.player.inventory["climbing_gear"] = 1
        desc = gs.rooms["stone_foothills"].get_description(gs.player.inventory)
        assert "harness" in desc.lower() or "climbing" in desc.lower() or "shoulder" in desc.lower()

    def test_fallen_pines_extra_desc_with_axe(self, gs):
        gs.player.inventory["axe"] = 1
        desc = gs.rooms["fallen_pines"].get_description(gs.player.inventory)
        assert "axe" in desc.lower() or "clear" in desc.lower() or "cut" in desc.lower()

    def test_look_command_includes_conditional_desc(self, gs):
        gs.player.inventory["torch"] = 1
        result = gs.process_command("look", None)
        full = " ".join(result).lower()
        assert "torch" in full or "light" in full



class TestCombine:
    def test_combine_rope_hook_gives_climbing_gear(self, gs):
        gs.player.inventory["rope"] = 1
        gs.player.inventory["hook"] = 1
        result = gs.process_command("combine", "rope hook")
        assert gs.player.inventory.get("climbing_gear", 0) == 1

    def test_combine_consumes_both_inputs(self, gs):
        gs.player.inventory["rope"] = 1
        gs.player.inventory["hook"] = 1
        gs.process_command("combine", "rope hook")
        assert gs.player.inventory.get("rope", 0) == 0
        assert gs.player.inventory.get("hook", 0) == 0

    def test_combine_reversed_order_also_works(self, gs):
        gs.player.inventory["rope"] = 1
        gs.player.inventory["hook"] = 1
        result = gs.process_command("combine", "hook rope")
        assert gs.player.inventory.get("climbing_gear", 0) == 1

    def test_combine_without_first_item_fails(self, gs):
        gs.player.inventory["hook"] = 1
        result = gs.process_command("combine", "rope hook")
        assert any("not carrying" in l.lower() for l in result)
        assert gs.player.inventory.get("climbing_gear", 0) == 0

    def test_combine_without_second_item_fails(self, gs):
        gs.player.inventory["rope"] = 1
        result = gs.process_command("combine", "rope hook")
        assert any("not carrying" in l.lower() for l in result)

    def test_combine_unknown_pair_fails(self, gs):
        gs.player.inventory["wood"] = 1
        gs.player.inventory["food"] = 1
        result = gs.process_command("combine", "wood food")
        assert any("cannot combine" in l.lower() for l in result)

    def test_combine_needs_two_words(self, gs):
        result = gs.process_command("combine", "rope")
        assert any("two" in l.lower() or "example" in l.lower() for l in result)

    def test_combine_with_no_target(self, gs):
        result = gs.process_command("combine", None)
        assert result  # returns help text, doesn't crash


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
        result = gs.process_command("drop", "axe")
        assert any("not carrying" in l.lower() for l in result)

    def test_drop_with_no_target(self, gs):
        result = gs.process_command("drop", None)
        assert result  # returns help text


class TestWeightWarnings:
    def test_no_warning_when_light(self, gs):
        gs.player.inventory["wood"] = 1
        result = gs.process_command("look", None)
        assert not any("heavy" in l.lower() or "full" in l.lower() for l in result)

    def test_heavy_warning_at_85_percent(self, gs):
        # 17 kg of 20 = 85%
        gs.player.inventory["stone"] = 8   # 16 kg
        gs.player.inventory["wood"]  = 1   # 1 kg → 17 kg total
        result = gs.process_command("look", None)
        assert any("heavy" in l.lower() for l in result)

    def test_full_warning_at_100_percent(self, gs):
        gs.player.inventory["stone"] = 10  # 20 kg = exactly at limit
        result = gs.process_command("look", None)
        assert any("full" in l.lower() or "barely" in l.lower() for l in result)

    def test_warning_gone_after_drop(self, gs):
        gs.player.inventory["stone"] = 10
        gs.process_command("drop", "stone")
        result = gs.process_command("look", None)
        assert not any("full" in l.lower() for l in result)

    def test_backpack_raises_limit_clears_warning(self, gs):
        gs.player.inventory["stone"] = 10  # 20 kg, hits default limit
        # Give backpack — limit jumps to 35
        teleport(gs, "fallen_pines")
        gs.process_command("examine", "lantern")
        gs.process_command("take", "backpack")
        result = gs.process_command("look", None)
        assert not any("full" in l.lower() for l in result)

    def test_movement_message_changes_when_full(self, gs):
        teleport(gs, "clearing")
        gs.player.inventory["stone"] = 10
        result = gs.process_command("go", "north")
        assert any("strain" in l.lower() or "weight" in l.lower() for l in result)



class TestPuzzleFlows:
    def test_bramble_wall_needs_machete(self, gs):
        teleport(gs, "shadow_trees")
        at_edge(gs, "north")
        result = gs.process_command("go", "north")
        assert any("machete" in l.lower() for l in result)
        assert gs.current_room_id == "shadow_trees"

    def test_find_machete_in_fallen_pines(self, gs):
        teleport(gs, "fallen_pines")
        assert gs.rooms["fallen_pines"].loot.get("machete", 0) == 1
        gs.process_command("take", "machete")
        assert gs.player.inventory.get("machete", 0) == 1

    def test_machete_unlocks_bramble_wall(self, gs):
        teleport(gs, "fallen_pines")
        gs.process_command("take", "machete")
        teleport(gs, "shadow_trees")
        at_edge(gs, "north")
        gs.process_command("go", "north")
        assert gs.current_room_id == "bramble_wall"

    def test_river_needs_raft(self, gs):
        teleport(gs, "soggy_path")
        at_edge(gs, "south")
        result = gs.process_command("go", "south")
        assert any("raft" in l.lower() for l in result)

    def test_craft_raft_unlocks_river(self, gs):
        gs.player.inventory["wood"]  = 4
        gs.player.inventory["stone"] = 1
        gs.process_command("craft", "raft")
        teleport(gs, "soggy_path")
        at_edge(gs, "south")
        gs.process_command("go", "south")
        assert gs.current_room_id == "rushing_river"

    def test_cliffline_needs_climbing_gear(self, gs):
        teleport(gs, "stone_foothills")
        at_edge(gs, "east")
        result = gs.process_command("go", "east")
        assert any("climbing" in l.lower() or "gear" in l.lower() for l in result)

    def test_take_climbing_gear_from_foothills(self, gs):
        teleport(gs, "stone_foothills")
        gs.process_command("take", "climbing_gear")
        assert gs.player.inventory.get("climbing_gear", 0) == 1

    def test_climbing_gear_unlocks_cliffline(self, gs):
        teleport(gs, "stone_foothills")
        gs.process_command("take", "climbing_gear")
        at_edge(gs, "east")
        gs.process_command("go", "east")
        assert gs.current_room_id == "black_cliffline"

    def test_deep_woods_needs_axe(self, gs):
        teleport(gs, "fallen_pines")
        at_edge(gs, "west")
        result = gs.process_command("go", "west")
        assert any("axe" in l.lower() for l in result)

    def test_find_axe_behind_boulder_then_unlock_deep_woods(self, gs):
        # Find the axe via examine
        teleport(gs, "shadow_trees")
        gs.process_command("examine", "boulder")
        gs.process_command("take", "axe")
        assert gs.player.inventory.get("axe", 0) == 1
        # Use it to enter deep woods
        teleport(gs, "fallen_pines")
        at_edge(gs, "west")
        gs.process_command("go", "west")
        assert gs.current_room_id == "deep_woods"