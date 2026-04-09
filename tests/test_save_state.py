from engine.game_state import GameState


def test_snapshot_roundtrip_preserves_progress():
    gs = GameState()
    gs.player.inventory["machete"] = 1
    gs.player.inventory["wood"] = 3
    gs.player.discovered_rooms.add("thick_forest")
    gs.player.explored_rooms.add("thick_forest")
    gs.current_room_id = "thick_forest"
    gs.local_x = 5
    gs.local_y = 4
    gs.player.visited_tiles.add((20, 20))

    snap = gs.snapshot()

    restored = GameState()
    assert restored.apply_snapshot(snap) is True
    assert restored.current_room_id == "thick_forest"
    assert restored.player.inventory.get("machete", 0) == 1
    assert restored.player.inventory.get("wood", 0) == 3
    assert restored.local_x == 5
    assert restored.local_y == 4
    assert (20, 20) in restored.player.visited_tiles


def test_snapshot_restores_room_loot_visibility():
    gs = GameState()
    gs.player.inventory["machete"] = 1
    gs.local_y = 0
    gs.process_command("go", "north")
    gs.process_command("enter", "cabin")
    assert "lantern" in gs.rooms["cabin_interior"].visible_loot()

    snap = gs.snapshot()
    restored = GameState()
    assert restored.apply_snapshot(snap) is True
    assert "lantern" in restored.rooms["cabin_interior"].visible_loot()
