import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from engine.game_state import GameState


def teleport(gs, room_id):
    gs.current_room_id = room_id
    room = gs.rooms[room_id]
    gs.local_x = room.width // 2
    gs.local_y = room.height // 2
    gs.player.explored_rooms.add(room_id)
    gs.player.discovered_rooms.add(room_id)


def at_edge(gs, direction):
    room = gs.rooms[gs.current_room_id]
    if direction == "north": gs.local_y = 0
    elif direction == "south": gs.local_y = room.height - 1
    elif direction == "east": gs.local_x = room.width - 1
    elif direction == "west": gs.local_x = 0


class TestWaterExitSymmetry:

    def test_far_shore_north_returns_to_riverbank(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "far_shore")
        at_edge(gs, "north")
        gs.process_command("go", "north")
        assert gs.current_room_id == "riverbank"

    def test_far_shore_east_reaches_river_lake(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "far_shore")
        at_edge(gs, "east")
        gs.process_command("go", "east")
        assert gs.current_room_id == "river_lake"

    def test_mountain_pass_south_reaches_river_run(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "mountain_pass")
        at_edge(gs, "south")
        gs.process_command("go", "south")
        assert gs.current_room_id == "river_run"

    def test_river_run_north_returns_to_mountain_pass(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        gs.player.inventory["climbing_gear"] = 1
        teleport(gs, "river_run")
        at_edge(gs, "north")
        gs.process_command("go", "north")
        assert gs.current_room_id == "mountain_pass"

    def test_roundtrip_riverbank_to_far_shore_and_back(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "riverbank")
        at_edge(gs, "south")
        gs.process_command("go", "south")
        assert gs.current_room_id == "far_shore"
        at_edge(gs, "north")
        gs.process_command("go", "north")
        assert gs.current_room_id == "riverbank"

    def test_roundtrip_river_run_to_open_waters_and_back(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "river_run")
        at_edge(gs, "west")
        gs.process_command("go", "west")
        assert gs.current_room_id == "open_waters"
        at_edge(gs, "east")
        gs.process_command("go", "east")
        assert gs.current_room_id == "river_run"

    def test_mountain_pass_has_no_ocean_exit(self):
        gs = GameState()
        gs.player.inventory["climbing_gear"] = 1
        teleport(gs, "mountain_pass")
        room = gs.rooms["mountain_pass"]
        assert "west" not in room.exits

    def test_ocean_reached_from_river_not_cliff(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "river_run")
        at_edge(gs, "west")
        gs.process_command("go", "west")
        assert gs.current_room_id == "open_waters"


class TestWaterMovementSpeed:

    def test_water_room_moves_two_tiles_with_raft(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "river_run")
        start_x = gs.local_x
        gs.process_command("go", "east")
        assert gs.local_x == start_x + 2

    def test_water_room_moves_one_tile_without_raft(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "river_run")
        gs.player.inventory["raft"] = 0
        start_x = gs.local_x
        gs.process_command("go", "east")
        assert gs.local_x == start_x + 1

    def test_open_waters_moves_three_tiles_with_raft(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "open_waters")
        gs.local_x = 10
        gs.local_y = 26
        start_x = gs.local_x
        gs.process_command("go", "east")
        assert gs.local_x == start_x + 3

    def test_land_room_moves_one_tile(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        start_x = gs.local_x
        gs.process_command("go", "east")
        assert gs.local_x == start_x + 1

    def test_water_movement_clamps_to_room_edge(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "river_run")
        room = gs.rooms["river_run"]
        gs.local_x = room.width - 2
        gs.process_command("go", "east")
        assert gs.local_x == room.width - 1


class TestWaterFlavorText:

    def test_paddle_text_in_water_room(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "river_run")
        result = gs.process_command("go", "east")
        assert any("paddle" in l.lower() for l in result)

    def test_move_text_in_land_room(self):
        gs = GameState()
        result = gs.process_command("go", "east")
        assert any("move east" in l.lower() for l in result)

    def test_no_paddle_without_raft(self):
        gs = GameState()
        teleport(gs, "riverbank")
        result = gs.process_command("go", "east")
        assert any("move east" in l.lower() for l in result)


class TestWaterBlockingRules:

    def test_water_to_water_not_blocked(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "far_shore")
        at_edge(gs, "east")
        gs.process_command("go", "east")
        assert gs.current_room_id == "river_lake"

    def test_land_to_water_blocked_without_raft(self):
        gs = GameState()
        teleport(gs, "riverbank")
        at_edge(gs, "east")
        result = gs.process_command("go", "east")
        assert gs.current_room_id == "riverbank"
        assert any("raft" in l.lower() for l in result)

    def test_river_run_west_to_ocean_allowed_water_to_water(self):
        gs = GameState()
        teleport(gs, "river_run")
        at_edge(gs, "west")
        gs.process_command("go", "west")
        assert gs.current_room_id == "open_waters"

    def test_river_run_west_to_ocean_with_raft(self):
        gs = GameState()
        gs.player.inventory["raft"] = 1
        teleport(gs, "river_run")
        at_edge(gs, "west")
        gs.process_command("go", "west")
        assert gs.current_room_id == "open_waters"
