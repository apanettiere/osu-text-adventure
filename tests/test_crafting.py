import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from engine.game_state import GameState


@pytest.fixture
def gs():
    return GameState()


class TestCraftingV1:
    def test_basic_recipes_are_loaded(self, gs):
        assert {"knife", "spear", "axe"} <= set(gs.recipes.keys())

    def test_craft_without_target_lists_recipes(self, gs):
        lines = gs.process_command("craft", None)
        full = " ".join(lines).lower()
        assert "crafting recipes" in full
        assert "spear" in full
        assert "wood" in full
        assert "stone" in full

    def test_recipe_alias_lists_recipes(self, gs):
        lines = gs.process_command("craft", "list")
        full = " ".join(lines).lower()
        assert "crafting recipes" in full
        assert "knife" in full

    def test_craft_spear_consumes_wood_and_stone(self, gs):
        gs.player.inventory["wood"] = 2
        gs.player.inventory["stone"] = 1

        lines = gs.process_command("craft", "spear")
        full = " ".join(lines).lower()

        assert gs.player.inventory.get("spear", 0) == 1
        assert gs.player.inventory.get("wood", 0) == 0
        assert gs.player.inventory.get("stone", 0) == 0
        assert "carry weight" in full

    def test_craft_fails_without_enough_resources(self, gs):
        gs.player.inventory["wood"] = 1
        gs.player.inventory["stone"] = 0
        before = dict(gs.player.inventory)

        lines = gs.process_command("craft", "spear")
        full = " ".join(lines).lower()

        assert "need" in full
        assert "wood" in full or "stone" in full
        assert gs.player.inventory == before

    def test_unknown_recipe_suggests_list(self, gs):
        lines = gs.process_command("craft", "hammer")
        full = " ".join(lines).lower()
        assert "don't know" in full
        assert "craft" in full
