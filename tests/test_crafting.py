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
        assert {"knife", "spear", "axe", "torch"} <= set(gs.recipes.keys())

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
        assert "torch" in full

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

        assert "cannot craft" in full
        assert "wood" in full or "stone" in full
        assert gs.player.inventory == before

    def test_unknown_recipe_suggests_list(self, gs):
        lines = gs.process_command("craft", "hammer")
        full = " ".join(lines).lower()
        assert "don't know" in full
        assert "craft" in full


class TestCraftingRefined:
    """Refined crafting tests per Sprint 1 plan."""

    def test_torch_recipe_exists(self, gs):
        assert "torch" in gs.recipes
        requires = gs.recipes["torch"]["requires"]
        assert requires == {"wood": 1, "food": 1}

    def test_craft_torch_consumes_wood_and_food(self, gs):
        gs.player.inventory["wood"] = 3
        gs.player.inventory["food"] = 2

        lines = gs.process_command("craft", "torch")
        full = " ".join(lines).lower()

        assert gs.player.inventory.get("torch", 0) == 1
        assert gs.player.inventory["wood"] == 2
        assert gs.player.inventory["food"] == 1
        assert "carry weight" in full

    def test_torch_item_has_uses(self, gs):
        assert "torch" in gs.item_registry
        assert gs.item_registry["torch"]["uses"] == 15
        assert gs.item_registry["torch"]["weight"] == 1

    def test_food_is_used_in_at_least_one_recipe(self, gs):
        food_recipes = [
            name for name, r in gs.recipes.items()
            if "food" in r.get("requires", {})
        ]
        assert len(food_recipes) >= 1

    def test_all_resources_have_recipe_uses(self, gs):
        used_resources = set()
        for recipe in gs.recipes.values():
            used_resources.update(recipe.get("requires", {}).keys())
        assert {"wood", "stone", "food"} <= used_resources

    def test_missing_ingredients_shows_all(self, gs):
        gs.player.inventory["wood"] = 0
        gs.player.inventory["stone"] = 0

        lines = gs.process_command("craft", "axe")
        full = " ".join(lines).lower()

        assert "cannot craft" in full
        assert "wood" in full
        assert "stone" in full

    def test_missing_ingredients_shows_have_count(self, gs):
        gs.player.inventory["wood"] = 1
        gs.player.inventory["stone"] = 0

        lines = gs.process_command("craft", "axe")
        full = " ".join(lines).lower()

        assert "have 1" in full
        assert "have 0" in full

    def test_craft_knife_minimal(self, gs):
        gs.player.inventory["wood"] = 1
        gs.player.inventory["stone"] = 1

        lines = gs.process_command("craft", "knife")

        assert gs.player.inventory.get("knife", 0) == 1
        assert gs.player.inventory["wood"] == 0
        assert gs.player.inventory["stone"] == 0

    def test_craft_multiple_items_sequentially(self, gs):
        gs.player.inventory["wood"] = 3
        gs.player.inventory["food"] = 2

        gs.process_command("craft", "torch")
        gs.process_command("craft", "torch")

        assert gs.player.inventory.get("torch", 0) == 2
        assert gs.player.inventory["wood"] == 1
        assert gs.player.inventory["food"] == 0

    def test_craft_shows_item_description(self, gs):
        gs.player.inventory["wood"] = 1
        gs.player.inventory["food"] = 1

        lines = gs.process_command("craft", "torch")
        full = " ".join(lines).lower()

        assert "burns" in full or "resin" in full or "moss" in full

    def test_recipe_list_shows_all_recipes(self, gs):
        lines = gs.process_command("craft", None)
        full = " ".join(lines).lower()

        for recipe_name in gs.recipes:
            assert recipe_name.replace("_", " ") in full

    def test_craft_with_exact_resources_leaves_zero(self, gs):
        gs.player.inventory["wood"] = 1
        gs.player.inventory["food"] = 1

        gs.process_command("craft", "torch")

        assert gs.player.inventory["wood"] == 0
        assert gs.player.inventory["food"] == 0
