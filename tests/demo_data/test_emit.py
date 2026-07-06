import json

from quant_allocator.demo_data._emit import round_floats, write_json


def test_round_floats_recurses_into_nested_structures():
    data = {"b": 0.123456789, "a": [1.111111119, {"c": 2.0}]}
    rounded = round_floats(data, ndigits=6)
    assert rounded["b"] == 0.123457
    assert rounded["a"][0] == 1.111111
    assert rounded["a"][1]["c"] == 2.0


def test_write_json_is_sorted_indented_and_newline_terminated(tmp_path):
    path = write_json(tmp_path / "out.json", {"z": 1.0, "a": 2.0})
    text = path.read_text(encoding="utf-8")
    assert text.endswith("\n")
    assert text.index('"a"') < text.index('"z"')  # keys sorted
    assert json.loads(text) == {"a": 2.0, "z": 1.0}


def test_write_json_is_byte_for_byte_deterministic(tmp_path):
    payload = {"m": [{"code": "A01", "x": 0.3333333333}, {"code": "A02", "x": 0.6}]}
    first = write_json(tmp_path / "a.json", payload).read_bytes()
    second = write_json(tmp_path / "b.json", payload).read_bytes()
    assert first == second
