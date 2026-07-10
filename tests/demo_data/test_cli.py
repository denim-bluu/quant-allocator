import pytest

from quant_allocator.demo_data.__main__ import main
from quant_allocator.demo_data._emit import SITE_DATA_DIR


def test_build_unknown_card_errors():
    with pytest.raises(SystemExit):
        main(["build", "does-not-exist"])


def test_build_all_builds_registered_cards(tmp_path, monkeypatch):
    import quant_allocator.demo_data.e2_pack as e2_pack
    import quant_allocator.demo_data.e3_knowledge as e3_knowledge
    import quant_allocator.demo_data.m1_drift as m1_drift
    import quant_allocator.demo_data.m2_convexity as m2_convexity
    import quant_allocator.demo_data.m3_alarms as m3_alarms
    import quant_allocator.demo_data.m4_crowding as m4_crowding
    import quant_allocator.demo_data.m5_saydo as m5_saydo
    import quant_allocator.demo_data.m6_holdings as m6_holdings
    import quant_allocator.demo_data.p1_allocation as p1_allocation
    import quant_allocator.demo_data.p2_xray as p2_xray
    import quant_allocator.demo_data.p3_hirefire as p3_hirefire
    import quant_allocator.demo_data.powergate_registry as powergate_registry
    import quant_allocator.demo_data.s1_ledger as s1_ledger
    import quant_allocator.demo_data.s2_tearsheet as s2_tearsheet
    import quant_allocator.demo_data.s3_lab as s3_lab
    import quant_allocator.demo_data.s4_sell as s4_sell
    import quant_allocator.demo_data.s5_shortbook as s5_shortbook
    import quant_allocator.demo_data.s6_signatures as s6_signatures
    import quant_allocator.demo_data.x1_atlas as x1_atlas
    import quant_allocator.demo_data.x2_playground as x2_playground

    calls = []
    monkeypatch.setattr(e2_pack, "build", lambda: calls.append("e2_pack") or tmp_path)
    monkeypatch.setattr(e3_knowledge, "build", lambda: calls.append("e3_knowledge") or tmp_path)
    monkeypatch.setattr(m1_drift, "build", lambda: calls.append("m1_drift") or tmp_path)
    monkeypatch.setattr(m2_convexity, "build", lambda: calls.append("m2_convexity") or tmp_path)
    monkeypatch.setattr(m3_alarms, "build", lambda: calls.append("m3_alarms") or tmp_path)
    monkeypatch.setattr(m4_crowding, "build", lambda: calls.append("m4_crowding") or tmp_path)
    monkeypatch.setattr(m5_saydo, "build", lambda: calls.append("m5_saydo") or tmp_path)
    monkeypatch.setattr(m6_holdings, "build", lambda: calls.append("m6_holdings") or tmp_path)
    monkeypatch.setattr(p1_allocation, "build", lambda: calls.append("p1_allocation") or tmp_path)
    monkeypatch.setattr(p2_xray, "build", lambda: calls.append("p2_xray") or tmp_path)
    monkeypatch.setattr(p3_hirefire, "build", lambda: calls.append("p3_hirefire") or tmp_path)
    monkeypatch.setattr(
        powergate_registry,
        "build",
        lambda: calls.append("powergate_registry") or tmp_path,
    )
    monkeypatch.setattr(s1_ledger, "build", lambda: calls.append("s1_ledger") or tmp_path)
    monkeypatch.setattr(s2_tearsheet, "build", lambda: calls.append("s2_tearsheet") or tmp_path)
    monkeypatch.setattr(s3_lab, "build", lambda: calls.append("s3_lab") or tmp_path)
    monkeypatch.setattr(s4_sell, "build", lambda: calls.append("s4_sell") or tmp_path)
    monkeypatch.setattr(s5_shortbook, "build", lambda: calls.append("s5_shortbook") or tmp_path)
    monkeypatch.setattr(s6_signatures, "build", lambda: calls.append("s6_signatures") or tmp_path)
    monkeypatch.setattr(x1_atlas, "build", lambda: calls.append("x1_atlas") or tmp_path)
    monkeypatch.setattr(x2_playground, "build", lambda: calls.append("x2_playground") or tmp_path)
    assert main(["build", "all"]) == 0
    assert sorted(calls) == [
        "e2_pack",
        "e3_knowledge",
        "m1_drift",
        "m2_convexity",
        "m3_alarms",
        "m4_crowding",
        "m5_saydo",
        "m6_holdings",
        "p1_allocation",
        "p2_xray",
        "p3_hirefire",
        "powergate_registry",
        "s1_ledger",
        "s2_tearsheet",
        "s3_lab",
        "s4_sell",
        "s5_shortbook",
        "s6_signatures",
        "x1_atlas",
        "x2_playground",
    ]


def test_batch_three_names_are_unique_across_committed_cards():
    from quant_allocator.demo_data import e3_knowledge, m4_crowding, m6_holdings, p2_xray

    name_groups = {
        "e3_knowledge.json": set(e3_knowledge.APPROVED_NAMES),
        "m4_crowding.json": {row["name"] for row in m4_crowding.MANAGERS},
        "m6_holdings.json": set(m6_holdings.APPROVED_NAMES),
        "p2_xray.json": set(p2_xray.P2_NAMES),
    }
    all_new_names = [name for names in name_groups.values() for name in names]
    assert len(all_new_names) == len(set(all_new_names))

    old_payloads = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in sorted(SITE_DATA_DIR.glob("*.json"))
        if path.name not in name_groups
    )
    for name in all_new_names:
        assert name.lower() not in old_payloads
