"""
Tests for map rendering helpers. Focus on tile ownership when interior rooms
sit geometrically inside an overworld room's bounds (e.g. the cabin sits inside
the thick forest). The fix guarantees the overworld view stays correct and the
focused interior view renders instead of a black screen.
"""

import os
import pytest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

from engine.game_state import GameState, MAP_ROOM_POS
from pygame_main import (
    FOCUSED_INTERIOR_ROOMS,
    INTERIOR_ONLY_ROOMS,
    MAP_NON_INTERIOR_BOUNDS,
    MAP_ROOM_BOUNDS,
    MAP_ROOM_SIZE,
    _overworld_room_at_cached,
    _room_at,
    _room_at_cached,
)


class TestRoomBoundsOrdering:
    def test_interior_rooms_come_first_in_bounds(self):
        first_overworld_index = next(
            i for i, entry in enumerate(MAP_ROOM_BOUNDS)
            if entry[0] not in INTERIOR_ONLY_ROOMS
        )
        for entry in MAP_ROOM_BOUNDS[:first_overworld_index]:
            assert entry[0] in INTERIOR_ONLY_ROOMS

    def test_non_interior_bounds_excludes_interiors(self):
        for entry in MAP_NON_INTERIOR_BOUNDS:
            assert entry[0] not in INTERIOR_ONLY_ROOMS

    def test_every_room_in_size_has_bounds(self):
        bound_ids = {entry[0] for entry in MAP_ROOM_BOUNDS}
        for rid in MAP_ROOM_SIZE:
            if rid in MAP_ROOM_POS:
                assert rid in bound_ids


class TestCabinInteriorInsideThickForest:
    def test_cabin_and_thick_forest_overlap(self):
        cx, cy = MAP_ROOM_POS["cabin_interior"]
        cw, ch = MAP_ROOM_SIZE["cabin_interior"]
        fx, fy = MAP_ROOM_POS["thick_forest"]
        fw, fh = MAP_ROOM_SIZE["thick_forest"]
        assert cx >= fx and cx + cw <= fx + fw
        assert cy + ch > fy
        assert cy < fy + fh

    def test_focus_mode_resolves_cabin_tiles_to_cabin(self):
        cx, cy = MAP_ROOM_POS["cabin_interior"]
        cw, ch = MAP_ROOM_SIZE["cabin_interior"]
        for dx in range(cw):
            for dy in range(ch):
                rid, _, _ = _room_at(cx + dx, cy + dy, None, focus_room_id="cabin_interior")
                assert rid == "cabin_interior"

    def test_overworld_mode_resolves_cabin_tiles_to_thick_forest(self):
        cx, cy = MAP_ROOM_POS["cabin_interior"]
        cw, ch = MAP_ROOM_SIZE["cabin_interior"]
        for dx in range(cw):
            for dy in range(ch):
                result = _room_at(cx + dx, cy + dy, None)
                if result is None:
                    continue
                assert result[0] == "thick_forest"

    def test_cached_lookup_returns_cabin_first(self):
        rid, _, _ = _room_at_cached(20, 2)
        assert rid == "cabin_interior"

    def test_overworld_cached_ignores_interior(self):
        rid, _, _ = _overworld_room_at_cached(20, 2)
        assert rid == "thick_forest"


class TestShedInteriorInsideRiverbank:
    def test_shed_overlaps_riverbank(self):
        sx, sy = MAP_ROOM_POS["shed_interior"]
        sw, sh = MAP_ROOM_SIZE["shed_interior"]
        rx, ry = MAP_ROOM_POS["riverbank"]
        rw, rh = MAP_ROOM_SIZE["riverbank"]
        assert sx + sw > rx and sx < rx + rw
        assert sy + sh > ry and sy < ry + rh

    def test_focus_mode_resolves_shed_tiles_to_shed(self):
        sx, sy = MAP_ROOM_POS["shed_interior"]
        sw, sh = MAP_ROOM_SIZE["shed_interior"]
        mid = _room_at(sx + sw // 2, sy + sh // 2, None, focus_room_id="shed_interior")
        assert mid[0] == "shed_interior"

    def test_overworld_mode_resolves_shed_tiles_to_riverbank(self):
        sx, sy = MAP_ROOM_POS["shed_interior"]
        sw, sh = MAP_ROOM_SIZE["shed_interior"]
        mid = _room_at(sx + sw // 2, sy + sh // 2, None)
        assert mid[0] == "riverbank"


class TestFocusedInteriorRooms:
    def test_all_focused_rooms_are_declared(self):
        for rid in ("cabin_interior", "cave_chamber", "shed_interior",
                    "lighthouse_interior", "lighthouse_top", "cave_entrance"):
            assert rid in FOCUSED_INTERIOR_ROOMS

    def test_every_interior_only_room_is_focusable(self):
        for rid in INTERIOR_ONLY_ROOMS:
            assert rid in FOCUSED_INTERIOR_ROOMS


class TestLightweightGameStateIntegration:
    def test_entering_cabin_switches_current_room(self):
        state = GameState()
        state.player.inventory["machete"] = 1
        state.current_room_id = "thick_forest"
        state.process_command("enter", "cabin")
        assert state.current_room_id == "cabin_interior"

    def test_cabin_interior_is_in_focused_set(self):
        state = GameState()
        state.current_room_id = "cabin_interior"
        assert state.current_room_id in FOCUSED_INTERIOR_ROOMS
