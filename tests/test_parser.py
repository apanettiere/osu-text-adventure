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