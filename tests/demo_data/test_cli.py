import pytest

from quant_allocator.demo_data.__main__ import main


def test_build_unknown_card_errors():
    with pytest.raises(SystemExit):
        main(["build", "does-not-exist"])


def test_build_all_builds_registered_cards(tmp_path, monkeypatch):
    import quant_allocator.demo_data.e2_pack as e2_pack
    import quant_allocator.demo_data.m1_drift as m1_drift
    import quant_allocator.demo_data.m2_convexity as m2_convexity
    import quant_allocator.demo_data.m3_alarms as m3_alarms
    import quant_allocator.demo_data.m5_saydo as m5_saydo
    import quant_allocator.demo_data.p3_hirefire as p3_hirefire
    import quant_allocator.demo_data.s1_ledger as s1_ledger
    import quant_allocator.demo_data.s2_tearsheet as s2_tearsheet
    import quant_allocator.demo_data.x1_atlas as x1_atlas
    import quant_allocator.demo_data.x2_playground as x2_playground

    calls = []
    monkeypatch.setattr(e2_pack, "build", lambda: calls.append("e2_pack") or tmp_path)
    monkeypatch.setattr(m1_drift, "build", lambda: calls.append("m1_drift") or tmp_path)
    monkeypatch.setattr(m2_convexity, "build", lambda: calls.append("m2_convexity") or tmp_path)
    monkeypatch.setattr(m3_alarms, "build", lambda: calls.append("m3_alarms") or tmp_path)
    monkeypatch.setattr(m5_saydo, "build", lambda: calls.append("m5_saydo") or tmp_path)
    monkeypatch.setattr(p3_hirefire, "build", lambda: calls.append("p3_hirefire") or tmp_path)
    monkeypatch.setattr(s1_ledger, "build", lambda: calls.append("s1_ledger") or tmp_path)
    monkeypatch.setattr(s2_tearsheet, "build", lambda: calls.append("s2_tearsheet") or tmp_path)
    monkeypatch.setattr(x1_atlas, "build", lambda: calls.append("x1_atlas") or tmp_path)
    monkeypatch.setattr(x2_playground, "build", lambda: calls.append("x2_playground") or tmp_path)
    assert main(["build", "all"]) == 0
    assert sorted(calls) == [
        "e2_pack",
        "m1_drift",
        "m2_convexity",
        "m3_alarms",
        "m5_saydo",
        "p3_hirefire",
        "s1_ledger",
        "s2_tearsheet",
        "x1_atlas",
        "x2_playground",
    ]
