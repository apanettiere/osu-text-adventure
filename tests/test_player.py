from engine.models import Player


def test_player_inventory_starts_at_zero():
    player = Player()

    assert player.inventory["wood"] == 0
    assert player.inventory["stone"] == 0
    assert player.inventory["food"] == 0