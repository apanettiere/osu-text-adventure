import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from engine.game_state import GameState
from engine.combat import CombatState
from engine.constants import DIFFICULTY_PRESETS


class TestDifficultyPresets:

    def test_all_presets_exist(self):
        assert "easy" in DIFFICULTY_PRESETS
        assert "normal" in DIFFICULTY_PRESETS
        assert "hard" in DIFFICULTY_PRESETS

    def test_presets_have_required_keys(self):
        for key, preset in DIFFICULTY_PRESETS.items():
            assert "label" in preset, f"{key} missing label"
            assert "player_hp" in preset, f"{key} missing player_hp"
            assert "enemy_damage_mult" in preset, f"{key} missing enemy_damage_mult"
            assert "gather_mult" in preset, f"{key} missing gather_mult"


class TestDifficultyPlayerHP:

    def test_easy_hp(self):
        state = GameState(difficulty="easy")
        assert state.player.max_hp == 40
        assert state.player.hp == 40

    def test_normal_hp(self):
        state = GameState(difficulty="normal")
        assert state.player.max_hp == 30
        assert state.player.hp == 30

    def test_hard_hp(self):
        state = GameState(difficulty="hard")
        assert state.player.max_hp == 20
        assert state.player.hp == 20

    def test_default_is_normal(self):
        state = GameState()
        assert state.difficulty == "normal"
        assert state.player.max_hp == 30


class TestDifficultyEnemyDamage:

    def test_easy_reduces_damage(self):
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 4, "symbol": "B"}, {}, 0.75)
        assert cs.enemy_damage == 3

    def test_normal_keeps_damage(self):
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 4, "symbol": "B"}, {}, 1.0)
        assert cs.enemy_damage == 4

    def test_hard_increases_damage(self):
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 4, "symbol": "B"}, {}, 1.5)
        assert cs.enemy_damage == 6

    def test_damage_never_below_one(self):
        cs = CombatState("boar", {"name": "boar", "hp": 10, "damage": 1, "symbol": "B"}, {}, 0.1)
        assert cs.enemy_damage >= 1

    def test_encounter_uses_state_mult(self):
        state = GameState(difficulty="hard")
        state.current_room_id = "thick_forest"
        combat = state.check_encounter()
        assert combat is not None
        base_damage = state.enemies["feral_boar"]["damage"]
        expected = max(1, int(base_damage * 1.5))
        assert combat.enemy_damage == expected


class TestDifficultyGather:

    def test_easy_doubles_gather(self):
        state = GameState(difficulty="easy")
        state.player.inventory["wood"] = 0
        lines = state.process_command("gather", "wood")
        assert state.player.inventory["wood"] == 4

    def test_normal_gather_unchanged(self):
        state = GameState(difficulty="normal")
        state.player.inventory["wood"] = 0
        lines = state.process_command("gather", "wood")
        assert state.player.inventory["wood"] == 2

    def test_hard_gather_unchanged(self):
        state = GameState(difficulty="hard")
        state.player.inventory["wood"] = 0
        lines = state.process_command("gather", "wood")
        assert state.player.inventory["wood"] == 2


class TestDifficultySaveLoad:

    def test_difficulty_in_snapshot(self):
        state = GameState(difficulty="hard")
        snap = state.snapshot()
        assert snap["difficulty"] == "hard"

    def test_difficulty_restored_from_snapshot(self):
        state = GameState(difficulty="easy")
        state.player.hp = 35
        snap = state.snapshot()

        state2 = GameState(difficulty="easy")
        state2.apply_snapshot(snap)
        assert state2.difficulty == "easy"
        assert state2.enemy_damage_mult == 0.75
        assert state2.gather_mult == 2
        assert state2.player.hp == 35

    def test_unknown_difficulty_defaults_to_normal(self):
        state = GameState(difficulty="normal")
        snap = state.snapshot()
        snap["difficulty"] = "nightmare"

        state2 = GameState()
        state2.apply_snapshot(snap)
        assert state2.difficulty == "normal"

    def test_missing_difficulty_defaults_to_normal(self):
        state = GameState()
        snap = state.snapshot()
        del snap["difficulty"]

        state2 = GameState()
        state2.apply_snapshot(snap)
        assert state2.difficulty == "normal"


class TestDifficultyStatus:

    def test_status_shows_difficulty(self):
        state = GameState(difficulty="hard")
        lines = state.process_command("status", None)
        diff_line = [l for l in lines if "Difficulty" in l]
        assert len(diff_line) == 1
        assert "Hard" in diff_line[0]

    def test_status_shows_easy(self):
        state = GameState(difficulty="easy")
        lines = state.process_command("status", None)
        diff_line = [l for l in lines if "Difficulty" in l]
        assert "Easy" in diff_line[0]
