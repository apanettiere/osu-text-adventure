"""
Tests for walkable room movement, intra-room stepping, feature proximity,
room transitions, and blocked room logic.
"""

import pytest
from engine.models import Room, Player
from engine.game_state import GameState, ENTRY_SPAWN, DIRECTION_DELTAS



def make_walkable_room(room_id="clearing", w=7, h=7, exits=None, features=None):
    return {
        "id": room_id,
        "name": room_id.title(),
        "description": "A test room.",
        "width": w,
        "height": h,
        "exits": exits or {},
        "gather": {"wood": 2},
        "features": features or [],
        "requires": [],
        "encounters": [],
        "loot": {},
    }


def make_instant_room(room_id, exits=None, requires=None):
    return {
        "id": room_id,
        "name": room_id.title(),
        "description": "A test room.",
        "exits": exits or {},
        "gather": {},
        "features": [],
        "requires": requires or [],
        "encounters": [],
        "loot": {},
    }


def build_state(rooms_data: list, starting_room: str) -> GameState:
    """
    Build a GameState without touching the real game.json file.
    Patches loader internals so tests are fully self-contained.
    """
    from engine import loader, models

    room_map = {}
    for rd in rooms_data:
        r = Room(rd)
        room_map[r.id] = r

    state = object.__new__(GameState)
    state.player = Player()
    state.game_data = {"starting_room": starting_room, "rooms": rooms_data}
    state.rooms = room_map
    state.current_room_id = starting_room
    state.is_running = True

    state.player.discovered_rooms.add(starting_room)
    state.player.room_positions[starting_room] = (0, 0)
    state.player.current_pos = (0, 0)

    start_room = room_map[starting_room]
    state.local_x = start_room.width  // 2
    state.local_y = start_room.height // 2

    return state



class TestRoomModel:
    def test_walkable_when_width_gt_1(self):
        room = Room(make_walkable_room(w=7, h=7))
        assert room.is_walkable is True

    def test_not_walkable_when_1x1(self):
        room = Room(make_instant_room("hall"))
        assert room.is_walkable is False

    def test_width_height_stored(self):
        room = Room(make_walkable_room(w=5, h=9))
        assert room.width  == 5
        assert room.height == 9

    def test_features_parsed_with_position(self):
        data = make_walkable_room(features=[
            {"id": "well", "label": "W", "desc": "A well.", "pos": [3, 3]}
        ])
        room = Room(data)
        assert len(room.features) == 1
        f = room.features[0]
        assert f["label"] == "W"
        assert f["pos"]   == (3, 3)

    def test_features_empty_by_default(self):
        room = Room(make_instant_room("hall"))
        assert room.features == []



class TestIntraRoomMovement:
    def setup_method(self):
        # 7×7 clearing, no exits yet - tests pure walking
        self.state = build_state(
            [make_walkable_room("clearing", 7, 7)],
            "clearing",
        )
        # Starts at centre (3, 3)

    def test_starts_at_centre(self):
        assert self.state.local_x == 3
        assert self.state.local_y == 3

    def test_step_north_decreases_y(self):
        self.state.handle_go("north")
        assert self.state.local_y == 2

    def test_step_south_increases_y(self):
        self.state.handle_go("south")
        assert self.state.local_y == 4

    def test_step_east_increases_x(self):
        self.state.handle_go("east")
        assert self.state.local_x == 4

    def test_step_west_decreases_x(self):
        self.state.handle_go("west")
        assert self.state.local_x == 2

    def test_stay_in_same_room_after_one_step(self):
        self.state.handle_go("north")
        assert self.state.current_room_id == "clearing"

    def test_move_returns_move_message(self):
        lines = self.state.handle_go("north")
        assert any("move" in l.lower() for l in lines)

    def test_cannot_exit_without_exit_defined(self):
        # Walk all the way to north wall (3 steps from centre y=3)
        for _ in range(3):
            self.state.handle_go("north")
        assert self.state.local_y == 0
        lines = self.state.handle_go("north")
        # Still in the same room - no exit defined
        assert self.state.current_room_id == "clearing"
        assert any("cannot" in l.lower() or "nothing" in l.lower() for l in lines)

    def test_clamped_at_south_wall_without_exit(self):
        for _ in range(10):           # overshoot deliberately
            self.state.handle_go("south")
        assert self.state.local_y == 6   # height - 1

    def test_clamped_at_east_wall_without_exit(self):
        for _ in range(10):
            self.state.handle_go("east")
        assert self.state.local_x == 6   # width - 1



class TestFeatureProximity:
    def setup_method(self):
        features = [
            {"id": "well", "label": "W", "desc": "A stone well.", "pos": [3, 3]}
        ]
        self.state = build_state(
            [make_walkable_room("clearing", 7, 7, features=features)],
            "clearing",
        )
        # Player starts at (3, 3) - exactly on the well

    def test_feature_desc_shown_when_adjacent(self):
        # Move one step - still adjacent to (3,3)
        self.state.local_x = 3
        self.state.local_y = 4
        lines = self.state.handle_go("north")   # moves to (3,3)
        assert any("well" in l.lower() for l in lines)

    def test_no_feature_desc_when_far_away(self):
        self.state.local_x = 0
        self.state.local_y = 0
        lines = self.state.handle_go("east")    # moves to (1, 0) - far from well
        assert not any("well" in l.lower() for l in lines)


class TestNearbyItemHints:
    def test_nearby_visible_item_shows_item_hint(self):
        room = make_walkable_room("clearing", 7, 7)
        room["loot"] = {"note": 1}
        state = build_state([room], "clearing")
        state.local_x = 3
        state.local_y = 4

        lines = state.handle_go("south")

        assert any("nearby item" in l.lower() and "note" in l.lower() for l in lines)
        assert any("take note" in l.lower() for l in lines)

    def test_hidden_item_does_not_show_nearby_hint(self):
        room = make_walkable_room("clearing", 7, 7)
        room["loot"] = {"note": 1}
        room["loot_hidden"] = {"note": True}
        state = build_state([room], "clearing")
        state.local_x = 3
        state.local_y = 4

        lines = state.handle_go("south")

        assert not any("nearby item" in l.lower() for l in lines)



class TestRoomTransition:
    def setup_method(self):
        clearing = make_walkable_room("clearing", 7, 7, exits={"north": "shadow"})
        shadow   = make_instant_room("shadow", exits={"south": "clearing"})
        self.state = build_state([clearing, shadow], "clearing")

    def _walk_to_north_wall(self):
        """Walk from centre (3,3) to north edge (y=0)."""
        for _ in range(3):
            self.state.handle_go("north")

    def test_no_transition_before_reaching_edge(self):
        self.state.handle_go("north")      # y goes 3→2
        assert self.state.current_room_id == "clearing"

    def test_transition_happens_at_north_wall(self):
        self._walk_to_north_wall()
        assert self.state.local_y == 0
        self.state.handle_go("north")      # now at edge → transition
        assert self.state.current_room_id == "shadow"

    def test_new_room_added_to_discovered(self):
        self._walk_to_north_wall()
        self.state.handle_go("north")
        assert "shadow" in self.state.player.discovered_rooms

    def test_world_map_coordinate_assigned(self):
        self._walk_to_north_wall()
        self.state.handle_go("north")
        assert "shadow" in self.state.player.room_positions

    def test_world_map_coordinate_is_correct(self):
        self._walk_to_north_wall()
        self.state.handle_go("north")
        # clearing is at (0,0), north = (0,-1)
        assert self.state.player.room_positions["shadow"] == (0, -1)

    def test_spawn_at_south_wall_of_new_room(self):
        """Entering from the south wall means spawning at y = height-1."""
        self._walk_to_north_wall()
        self.state.handle_go("north")
        shadow = self.state.rooms["shadow"]
        assert self.state.local_y == shadow.height - 1



class TestEntrySpawn:
    """ENTRY_SPAWN lambdas are pure functions - test them directly."""

    def test_entering_from_north_spawns_at_south_wall(self):
        x, y = ENTRY_SPAWN["north"](7, 7)
        assert y == 6          # height - 1

    def test_entering_from_south_spawns_at_north_wall(self):
        x, y = ENTRY_SPAWN["south"](7, 7)
        assert y == 0

    def test_entering_from_east_spawns_at_west_wall(self):
        x, y = ENTRY_SPAWN["east"](7, 7)
        assert x == 0

    def test_entering_from_west_spawns_at_east_wall(self):
        x, y = ENTRY_SPAWN["west"](7, 7)
        assert x == 6          # width - 1

    def test_spawn_x_centred_for_north_south(self):
        x, _ = ENTRY_SPAWN["north"](7, 7)
        assert x == 3          # 7 // 2

    def test_spawn_y_centred_for_east_west(self):
        _, y = ENTRY_SPAWN["east"](7, 7)
        assert y == 3



class TestBlockedRooms:
    def setup_method(self):
        clearing = make_walkable_room("clearing", 7, 7, exits={"north": "bramble"})
        bramble  = make_instant_room("bramble", exits={"south": "clearing"}, requires=[
            {"type": "item", "item": "machete", "amount": 1,
             "message": "The brambles tear at you. You need a machete."}
        ])
        self.state = build_state([clearing, bramble], "clearing")

    def _walk_to_north_wall(self):
        for _ in range(3):
            self.state.handle_go("north")

    def test_blocked_room_not_entered_without_item(self):
        self._walk_to_north_wall()
        self.state.handle_go("north")
        assert self.state.current_room_id == "clearing"

    def test_blocked_room_message_returned(self):
        self._walk_to_north_wall()
        lines = self.state.handle_go("north")
        assert any("machete" in l.lower() for l in lines)

    def test_blocked_room_still_discovered(self):
        self._walk_to_north_wall()
        self.state.handle_go("north")
        assert "bramble" in self.state.player.discovered_rooms

    def test_blocked_room_coordinate_assigned(self):
        self._walk_to_north_wall()
        self.state.handle_go("north")
        assert "bramble" in self.state.player.room_positions

    def test_enters_blocked_room_with_item(self):
        self.state.player.inventory["machete"] = 1
        self._walk_to_north_wall()
        self.state.handle_go("north")
        assert self.state.current_room_id == "bramble"


class TestInstantTravelRooms:
    def setup_method(self):
        hall  = make_instant_room("hall",  exits={"east": "vault"})
        vault = make_instant_room("vault", exits={"west": "hall"})
        self.state = build_state([hall, vault], "hall")

    def test_instant_travel_on_first_command(self):
        self.state.handle_go("east")
        assert self.state.current_room_id == "vault"

    def test_invalid_direction_refused(self):
        lines = self.state.handle_go("north")
        assert self.state.current_room_id == "hall"
        assert any("cannot" in l.lower() for l in lines)

    def test_no_local_step_taken(self):
        x_before = self.state.local_x
        y_before = self.state.local_y
        self.state.handle_go("east")
        # local position resets to centre of new instant room (1x1 → 0,0)
        assert isinstance(self.state.local_x, int)


class TestDirectionDeltas:
    def test_north_decreases_y(self):
        assert DIRECTION_DELTAS["north"] == (0, -1)

    def test_south_increases_y(self):
        assert DIRECTION_DELTAS["south"] == (0, 1)

    def test_east_increases_x(self):
        assert DIRECTION_DELTAS["east"] == (1, 0)

    def test_west_decreases_x(self):
        assert DIRECTION_DELTAS["west"] == (-1, 0)
