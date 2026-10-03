"""Quote loading; what happens when the quote file cannot be trusted.

The service is deliberately unkillable: a missing, malformed or wrongly shaped
quotes file must degrade to the built-in fallback rather than take the API
down, because a joke endpoint returning a 500 is worse than a joke endpoint
repeating itself.
"""

import json

from app.services.sarcasm_service import SarcasmService


def test_quotes_are_loaded_from_the_file(tmp_path):
    path = tmp_path / "quotes.json"
    path.write_text(json.dumps(["Only one thing to say."]), encoding="utf-8")

    assert SarcasmService(str(path)).get_quote() == "Only one thing to say."


def test_a_missing_file_falls_back(tmp_path, capsys):
    service = SarcasmService(str(tmp_path / "absent.json"))

    assert service.get_quote() in SarcasmService._default_quotes()
    assert "Failed to load quotes" in capsys.readouterr().out


def test_a_file_that_is_not_a_list_falls_back(tmp_path, capsys):
    path = tmp_path / "quotes.json"
    path.write_text(json.dumps({"not": "a list"}), encoding="utf-8")

    service = SarcasmService(str(path))

    assert service.get_quote() in SarcasmService._default_quotes()
    assert "Expected a list of strings" in capsys.readouterr().out


def test_a_list_of_non_strings_falls_back(tmp_path, capsys):
    # The shape check is per element, not just on the container.
    path = tmp_path / "quotes.json"
    path.write_text(json.dumps(["fine", 7]), encoding="utf-8")

    service = SarcasmService(str(path))

    assert service.get_quote() in SarcasmService._default_quotes()
    assert "Expected a list of strings" in capsys.readouterr().out


def test_the_fallback_is_not_empty():
    # _random_choice would raise on an empty sequence, so the fallback existing
    # is what makes the degraded path actually degrade rather than fail.
    assert SarcasmService._default_quotes()


def test_the_shipped_quotes_hold_no_repeats():
    # A repeated line is drawn twice as often as its neighbours. Loading through
    # the default path keeps that path in one place: the service.
    quotes = SarcasmService()._quotes

    assert quotes != SarcasmService._default_quotes()
    assert len(quotes) == len(set(quotes))
