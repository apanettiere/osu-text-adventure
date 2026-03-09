"""
Tests for the three main walkable rooms: Forest Clearing, Thick Forest, Riverbank.
Covers dimensions, features, exits, transitions, gather, and blocked-room logic.
"""

import pytest
import json
from pathlib import Path
from engine.models import Room, Player
from engine.game_state import GameState, ENTRY_SPAWN


@pytest.fixture(scope="module")
def game_data():
    path = Path(__file__).resolve().parents[1] / "data" / "game.json"
    with path.open() as f:
        return json.load(f)


@pytest.fixture(scope="module")
def room_map(game_data):
    return {r["id"]: Room(r) for r in game_data["rooms"]}


class TestRoomDimensions:
    def test_clearing_is_17x17(self, room_map):
        r = room_map["clearing"]
        assert r.width == 17 and r.height == 17

    def test_thick_forest_is_19x13(self, room_map):
        r = room_map["thick_forest"]
        assert r.width == 19 and r.height == 13

    def test_riverbank_is_17x13(self, room_map):
        r = room_map["riverbank"]
        assert r.width == 17 and r.height == 13

    def test_cave_entrance_is_13x11(self, room_map):
        r = room_map["cave_entrance"]
        assert r.width == 13 and r.height == 11

    def test_all_three_main_rooms_are_walkable(self, room_map):
        for rid in ("clearing", "thick_forest", "riverbank"):
            assert room_map[rid].is_walkable

    def test_far_shore_is_not_walkable(self, room_map):
        assert not room_map["far_shore"].is_walkable

    def test_mountain_pass_is_walkable(self, room_map):
        assert room_map["mountain_pass"].is_walkable


class TestRoomFeatures:
    def test_clearing_has_three_features(self, room_map):
        assert len(room_map["clearing"].features) == 3

    def test_clearing_stump_at_centre(self, room_map):
        stump = next(f for f in room_map["clearing"].features if f["id"] == "stump")
        assert stump["pos"] == (8, 8)

    def test_clearing_feature_labels(self, room_map):
        labels = {f["label"] for f in room_map["clearing"].features}
        assert labels == {"S", "F", "T"}

    def test_thick_forest_has_two_features(self, room_map):
        assert len(room_map["thick_forest"].features) == 2

    def test_thick_forest_feature_labels(self, room_map):
        labels = {f["label"] for f in room_map["thick_forest"].features}
        assert labels == {"C", "L"}

    def test_riverbank_has_two_features(self, room_map):
        assert len(room_map["riverbank"].features) == 2

    def test_riverbank_feature_labels(self, room_map):
        labels = {f["label"] for f in room_map["riverbank"].features}
        assert labels == {"P", "R"}

    def test_all_features_have_desc(self, room_map):
        for rid in ("clearing", "thick_forest", "riverbank", "cave_entrance", "mountain_pass"):
            for feat in room_map[rid].features:
                assert feat["desc"]

    def test_feature_positions_in_bounds(self, room_map):
        for rid in ("clearing", "thick_forest", "riverbank", "cave_entrance", "mountain_pass"):
            r = room_map[rid]
            for feat in r.features:
                fx, fy = feat["pos"]
                assert 0 <= fx < r.width
                assert 0 <= fy < r.height

    def test_mountain_pass_has_lighthouse_feature(self, room_map):
        ids = {f["id"] for f in room_map["mountain_pass"].features}
        assert "lighthouse" in ids


class TestRoomExits:
    def test_clearing_has_four_exits(self, room_map):
        assert set(room_map["clearing"].exits.keys()) == {"north", "south", "east", "west"}

    def test_clearing_north_leads_to_thick_forest(self, room_map):
        assert room_map["clearing"].exits["north"] == "thick_forest"

    def test_clearing_south_leads_to_riverbank(self, room_map):
        assert room_map["clearing"].exits["south"] == "riverbank"

    def test_clearing_east_leads_to_cave_entrance(self, room_map):
        assert room_map["clearing"].exits["east"] == "cave_entrance"

    def test_clearing_west_leads_to_mountain_pass(self, room_map):
        assert room_map["clearing"].exits["west"] == "mountain_pass"

    def test_thick_forest_south_returns_to_clearing(self, room_map):
        assert room_map["thick_forest"].exits["south"] == "clearing"

    def test_riverbank_north_returns_to_clearing(self, room_map):
        assert room_map["riverbank"].exits["north"] == "clearing"


class TestRoomRequirements:
    def test_thick_forest_requires_machete(self, room_map):
        items = [r["item"] for r in room_map["thick_forest"].requires if r.get("type") == "item"]
        assert "machete" in items

    def test_cave_entrance_requires_lantern(self, room_map):
        items = [r["item"] for r in room_map["cave_entrance"].requires if r.get("type") == "item"]
        assert "lantern" in items

    def test_far_shore_requires_raft(self, room_map):
        items = [r["item"] for r in room_map["far_shore"].requires if r.get("type") == "item"]
        assert "raft" in items

    def test_mountain_pass_requires_climbing_gear(self, room_map):
        items = [r["item"] for r in room_map["mountain_pass"].requires if r.get("type") == "item"]
        assert "climbing_gear" in items

    def test_clearing_has_no_requirements(self, room_map):
        assert room_map["clearing"].requires == []

    def test_riverbank_has_no_requirements(self, room_map):
        assert room_map["riverbank"].requires == []


def build_state():
    return GameState()


def walk_to_edge(state, direction):
    room = state.get_current_room()
    limit = max(room.width, room.height) + 2
    for _ in range(limit):
        if state._at_exit_edge(direction, room):
            break
        state.handle_go(direction)


class TestClearingToRiverbank:
    def setup_method(self):
        self.state = build_state()

    def test_takes_multiple_steps_to_reach_south_wall(self):
        steps = 0
        room = self.state.get_current_room()
        while not self.state._at_exit_edge("south", room):
            self.state.handle_go("south")
            steps += 1
        assert steps > 0

    def test_transition_to_riverbank(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        assert self.state.current_room_id == "riverbank"

    def test_riverbank_discovered_after_transition(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        assert "riverbank" in self.state.player.discovered_rooms

    def test_world_map_position_correct(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        assert self.state.player.room_positions["riverbank"] == (0, 1)

    def test_spawns_at_north_wall_of_riverbank(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        assert self.state.local_y == 0

    def test_spawns_at_horizontal_centre(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        riverbank = self.state.rooms["riverbank"]
        assert self.state.local_x == riverbank.width // 2


class TestClearingToThickForest:
    def setup_method(self):
        self.state = build_state()

    def test_blocked_without_machete(self):
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        assert self.state.current_room_id == "clearing"

    def test_blocked_message_mentions_machete(self):
        walk_to_edge(self.state, "north")
        lines = self.state.handle_go("north")
        assert any("machete" in l.lower() for l in lines)

    def test_thick_forest_discovered_after_bump(self):
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        assert "thick_forest" in self.state.player.discovered_rooms

    def test_enters_with_machete(self):
        self.state.player.inventory["machete"] = 1
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        assert self.state.current_room_id == "thick_forest"

    def test_spawns_at_south_wall_of_thick_forest(self):
        self.state.player.inventory["machete"] = 1
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        forest = self.state.rooms["thick_forest"]
        assert self.state.local_y == forest.height - 1


class TestReturnJourney:
    def setup_method(self):
        self.state = build_state()

    def test_riverbank_back_to_clearing(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        assert self.state.current_room_id == "clearing"

    def test_world_map_has_both_rooms_after_loop(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        for rid in ("clearing", "riverbank"):
            assert rid in self.state.player.room_positions


class TestGatherInRooms:
    def test_clearing_has_wood(self):
        state = build_state()
        state.handle_gather("wood")
        assert state.player.inventory["wood"] > 0

    def test_clearing_has_food(self):
        state = build_state()
        state.handle_gather("food")
        assert state.player.inventory["food"] > 0

    def test_clearing_has_stone(self):
        state = build_state()
        state.handle_gather("stone")
        assert state.player.inventory["stone"] > 0

    def test_riverbank_has_food(self):
        state = build_state()
        walk_to_edge(state, "south")
        state.handle_go("south")
        state.handle_gather("food")
        assert state.player.inventory["food"] > 0

    def test_riverbank_cannot_gather_wood(self):
        state = build_state()
        walk_to_edge(state, "south")
        state.handle_go("south")
        lines = state.handle_gather("wood")
        assert state.player.inventory.get("wood", 0) == 0
        assert any("cannot" in l.lower() for l in lines)

    def test_thick_forest_has_wood(self):
        state = build_state()
        state.player.inventory["machete"] = 1
        walk_to_edge(state, "north")
        state.handle_go("north")
        state.handle_gather("wood")
        assert state.player.inventory["wood"] > 0


class TestLootInRooms:
    def test_machete_visible_in_clearing(self):
        state = build_state()
        assert "machete" in state.rooms["clearing"].visible_loot()

    def test_lantern_hidden_in_thick_forest(self):
        state = build_state()
        assert "lantern" not in state.rooms["thick_forest"].visible_loot()

    def test_raft_hidden_in_thick_forest(self):
        state = build_state()
        assert "raft" not in state.rooms["thick_forest"].visible_loot()

    def test_lantern_revealed_by_examining_cabin(self):
        state = build_state()
        state.current_room_id = "thick_forest"
        state.process_command("examine", "cabin")
        assert "lantern" in state.rooms["thick_forest"].visible_loot()

    def test_raft_revealed_by_examining_cabin(self):
        state = build_state()
        state.current_room_id = "thick_forest"
        state.process_command("examine", "cabin")
        assert "raft" in state.rooms["thick_forest"].visible_loot()

    def test_old_map_in_cave_loot(self):
        state = build_state()
        assert state.rooms["cave_entrance"].loot.get("old_map", 0) == 1
