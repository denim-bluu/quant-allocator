import pytest

from quant_allocator.demo_data.__main__ import main


def test_build_unknown_card_errors():
    with pytest.raises(SystemExit):
        main(["build", "does-not-exist"])


def test_build_all_builds_registered_cards(tmp_path, monkeypatch):
    import quant_allocator.demo_data.m5_saydo as m5_saydo
    import quant_allocator.demo_data.s1_ledger as s1_ledger
    import quant_allocator.demo_data.s2_tearsheet as s2_tearsheet
    import quant_allocator.demo_data.x2_playground as x2_playground

    calls = []
    monkeypatch.setattr(s1_ledger, "build", lambda: calls.append("s1_ledger") or tmp_path)
    monkeypatch.setattr(m5_saydo, "build", lambda: calls.append("m5_saydo") or tmp_path)
    monkeypatch.setattr(s2_tearsheet, "build", lambda: calls.append("s2_tearsheet") or tmp_path)
    monkeypatch.setattr(x2_playground, "build", lambda: calls.append("x2_playground") or tmp_path)
    assert main(["build", "all"]) == 0
    assert sorted(calls) == ["m5_saydo", "s1_ledger", "s2_tearsheet", "x2_playground"]
