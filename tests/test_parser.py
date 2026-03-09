import pytest

from engine.parser import parse_command


def test_parse_command_empty_string():
    verb, target = parse_command("")
    assert verb == ""
    assert target is None


def test_parse_command_whitespace_only():
    verb, target = parse_command("   ")
    assert verb == ""
    assert target is None


def test_parse_command_one_word():
    verb, target = parse_command("look")
    assert verb == "look"
    assert target is None


def test_parse_command_two_words():
    verb, target = parse_command("go north")
    assert verb == "go"
    assert target == "north"


def test_parse_command_extra_words_ignored():
    verb, target = parse_command("take rusty key")
    assert verb == "take"
    assert target == "rusty"


def test_parse_command_case_insensitive():
    verb, target = parse_command("Go North")
    assert verb == "go"
    assert target == "north"


def test_parse_help_alias():
    verb, target = parse_command("?")
    assert verb == "help"
    assert target is None


def test_parse_enter_with_article():
    verb, target = parse_command("enter the cabin")
    assert verb == "enter"
    assert target == "cabin"


def test_parse_take_climbing_gear_two_words():
    verb, target = parse_command("take climbing gear")
    assert verb == "take"
    assert target == "climbing_gear"


def test_parse_read_old_map_two_words():
    verb, target = parse_command("read old map")
    assert verb == "read"
    assert target == "old_map"


def test_parse_pick_up_phrase():
    verb, target = parse_command("pick up the raft")
    assert verb == "take"
    assert target == "raft"


def test_parse_look_at_phrase_maps_feature():
    verb, target = parse_command("look at rope post")
    assert verb == "examine"
    assert target == "rope_post"


def test_parse_move_direction_phrase():
    verb, target = parse_command("move north")
    assert verb == "go"
    assert target == "north"


def test_parse_go_to_direction_phrase():
    verb, target = parse_command("go to the west")
    assert verb == "go"
    assert target == "west"


def test_parse_where_am_i_phrase():
    verb, target = parse_command("where am i")
    assert verb == "look"
    assert target is None


def test_parse_what_do_i_do_phrase():
    verb, target = parse_command("what do i do")
    assert verb == "hint"
    assert target is None


def test_parse_controls_alias():
    verb, target = parse_command("controls")
    assert verb == "help"
    assert target is None
