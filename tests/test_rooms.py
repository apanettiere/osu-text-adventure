"""
Tests for the three connected rooms: Forest Clearing, Shadow Trees, Soggy Path.
Covers room dimensions, features, transitions between rooms, and world-map positions.
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
    def test_clearing_is_13x13(self, room_map):
        r = room_map["clearing"]
        assert r.width == 13 and r.height == 13

    def test_shadow_trees_is_15x9(self, room_map):
        r = room_map["shadow_trees"]
        assert r.width == 15 and r.height == 9

    def test_soggy_path_is_9x15(self, room_map):
        r = room_map["soggy_path"]
        assert r.width == 9 and r.height == 15

    def test_all_three_are_walkable(self, room_map):
        for rid in ("clearing", "shadow_trees", "soggy_path"):
            assert room_map[rid].is_walkable, f"{rid} should be walkable"


# ─── Room features ────────────────────────────────────────────────────────────

class TestRoomFeatures:
    def test_clearing_has_three_features(self, room_map):
        assert len(room_map["clearing"].features) == 3

    def test_clearing_well_at_centre(self, room_map):
        well = next(f for f in room_map["clearing"].features if f["id"] == "well")
        assert well["pos"] == (6, 6)

    def test_clearing_feature_labels(self, room_map):
        labels = {f["label"] for f in room_map["clearing"].features}
        assert labels == {"W", "T", "F"}

    def test_shadow_trees_has_two_features(self, room_map):
        assert len(room_map["shadow_trees"].features) == 2

    def test_shadow_trees_feature_labels(self, room_map):
        labels = {f["label"] for f in room_map["shadow_trees"].features}
        assert labels == {"B", "S"}

    def test_soggy_path_has_two_features(self, room_map):
        assert len(room_map["soggy_path"].features) == 2

    def test_soggy_path_feature_labels(self, room_map):
        labels = {f["label"] for f in room_map["soggy_path"].features}
        assert labels == {"R", "C"}

    def test_all_features_have_desc(self, room_map):
        for rid in ("clearing", "shadow_trees", "soggy_path"):
            for feat in room_map[rid].features:
                assert feat["desc"], f"{rid} feature '{feat['id']}' missing desc"

    def test_feature_positions_in_bounds(self, room_map):
        for rid in ("clearing", "shadow_trees", "soggy_path"):
            r = room_map[rid]
            for feat in r.features:
                fx, fy = feat["pos"]
                assert 0 <= fx < r.width,  f"{rid}/{feat['id']} x={fx} out of bounds"
                assert 0 <= fy < r.height, f"{rid}/{feat['id']} y={fy} out of bounds"


class TestRoomExits:
    def test_clearing_has_four_exits(self, room_map):
        assert set(room_map["clearing"].exits.keys()) == {"north","south","east","west"}

    def test_clearing_north_leads_to_shadow_trees(self, room_map):
        assert room_map["clearing"].exits["north"] == "shadow_trees"

    def test_clearing_south_leads_to_soggy_path(self, room_map):
        assert room_map["clearing"].exits["south"] == "soggy_path"

    def test_shadow_trees_south_returns_to_clearing(self, room_map):
        assert room_map["shadow_trees"].exits["south"] == "clearing"

    def test_soggy_path_north_returns_to_clearing(self, room_map):
        assert room_map["soggy_path"].exits["north"] == "clearing"


def build_state() -> GameState:
    """Build a real GameState from the actual game.json."""
    return GameState()


def walk_to_edge(state: GameState, direction: str):
    """Walk until we hit the exit edge in the given direction."""
    room = state.get_current_room()
    limit = max(room.width, room.height) + 2
    for _ in range(limit):
        if state._at_exit_edge(direction, room):
            break
        state.handle_go(direction)


class TestClearingToShadowTrees:
    def setup_method(self):
        self.state = build_state()

    def test_takes_multiple_steps_to_reach_north_wall(self):
        steps = 0
        room = self.state.get_current_room()
        while not self.state._at_exit_edge("north", room):
            self.state.handle_go("north")
            steps += 1
        assert steps > 0

    def test_transition_on_step_from_north_wall(self):
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        assert self.state.current_room_id == "shadow_trees"

    def test_shadow_trees_discovered_after_transition(self):
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        assert "shadow_trees" in self.state.player.discovered_rooms

    def test_world_map_position_correct(self):
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        # clearing is (0,0), north = (0,-1)
        assert self.state.player.room_positions["shadow_trees"] == (0, -1)

    def test_spawns_at_south_wall_of_shadow_trees(self):
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        shadow = self.state.rooms["shadow_trees"]
        assert self.state.local_y == shadow.height - 1

    def test_spawns_at_horizontal_centre(self):
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        shadow = self.state.rooms["shadow_trees"]
        assert self.state.local_x == shadow.width // 2


class TestClearingToSoggyPath:
    def setup_method(self):
        self.state = build_state()

    def test_transition_to_soggy_path(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        assert self.state.current_room_id == "soggy_path"

    def test_world_map_position_correct(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        assert self.state.player.room_positions["soggy_path"] == (0, 1)

    def test_spawns_at_north_wall_of_soggy_path(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        assert self.state.local_y == 0

    def test_spawns_at_horizontal_centre(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        soggy = self.state.rooms["soggy_path"]
        assert self.state.local_x == soggy.width // 2


class TestReturnJourney:
    def setup_method(self):
        self.state = build_state()

    def test_shadow_trees_back_to_clearing(self):
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        assert self.state.current_room_id == "shadow_trees"

        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        assert self.state.current_room_id == "clearing"

    def test_soggy_path_back_to_clearing(self):
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        assert self.state.current_room_id == "soggy_path"

        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        assert self.state.current_room_id == "clearing"

    def test_world_map_has_all_three_rooms_after_full_loop(self):
        walk_to_edge(self.state, "north")
        self.state.handle_go("north")
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")
        walk_to_edge(self.state, "south")
        self.state.handle_go("south")

        for rid in ("clearing", "shadow_trees", "soggy_path"):
            assert rid in self.state.player.room_positions


class TestGatherInRooms:
    def test_clearing_has_wood(self):
        state = build_state()
        lines = state.handle_gather("wood")
        assert state.player.inventory["wood"] > 0

    def test_clearing_has_food(self):
        state = build_state()
        state.handle_gather("food")
        assert state.player.inventory["food"] > 0

    def test_shadow_trees_has_wood(self):
        state = build_state()
        walk_to_edge(state, "north")
        state.handle_go("north")
        state.handle_gather("wood")
        assert state.player.inventory["wood"] > 0

    def test_soggy_path_has_food(self):
        state = build_state()
        walk_to_edge(state, "south")
        state.handle_go("south")
        state.handle_gather("food")
        assert state.player.inventory["food"] > 0

    def test_cannot_gather_stone_in_soggy_path(self):
        state = build_state()
        walk_to_edge(state, "south")
        state.handle_go("south")
        lines = state.handle_gather("stone")
        assert state.player.inventory.get("stone", 0) == 0
        assert any("cannot" in l.lower() for l in lines)