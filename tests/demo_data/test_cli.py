import pytest

from quant_allocator.demo_data.__main__ import main


def test_build_unknown_card_errors():
    with pytest.raises(SystemExit):
        main(["build", "does-not-exist"])


def test_build_all_builds_registered_cards(tmp_path, monkeypatch):
    import quant_allocator.demo_data.s1_ledger as s1_ledger

    calls = []
    monkeypatch.setattr(s1_ledger, "build", lambda: calls.append("s1_ledger") or tmp_path)
    assert main(["build", "all"]) == 0
    assert calls == ["s1_ledger"]
