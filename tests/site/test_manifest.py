import yaml

import pytest

from quant_allocator.site.build import BuildError, load_manifest


def _write_manifest(tmp_path, entries):
    site_dir = tmp_path / "site"
    site_dir.mkdir(parents=True, exist_ok=True)
    manifest = site_dir / "cards.yaml"
    manifest.write_text(yaml.safe_dump(entries), encoding="utf-8")
    return manifest


def _make_live_files(tmp_path):
    site_dir = tmp_path / "site"
    (site_dir / "templates" / "pages").mkdir(parents=True, exist_ok=True)
    (site_dir / "templates" / "pages" / "t1.html.j2").write_text("x", encoding="utf-8")
    (site_dir / "data").mkdir(parents=True, exist_ok=True)
    (site_dir / "data" / "t1.json").write_text("{}", encoding="utf-8")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    (specs / "t1.md").write_text("# t1", encoding="utf-8")


def _planned_entry():
    return {
        "id": "s1",
        "title": "Skill ledger",
        "lane": "S",
        "one_liner": "Posterior alpha across the roster.",
        "decisions": ["select", "size"],
        "tiers": ["R", "E", "P"],
        "status": "planned",
    }


def _live_entry():
    return {
        "id": "t1",
        "title": "Test card",
        "lane": "S",
        "one_liner": "A live card.",
        "decisions": ["select"],
        "tiers": ["R"],
        "status": "live",
        "demo": "pages/t1.html.j2",
        "data": "t1.json",
        "spec": "t1.md",
        "golive": {"data_ask": "R", "sample": "36m", "effort": "S"},
    }


def test_valid_planned_entry_loads(tmp_path):
    manifest = _write_manifest(tmp_path, [_planned_entry()])
    cards = load_manifest(manifest)
    assert cards[0]["id"] == "s1"


def test_valid_live_entry_loads(tmp_path):
    _make_live_files(tmp_path)
    manifest = _write_manifest(tmp_path, [_live_entry()])
    cards = load_manifest(manifest)
    assert cards[0]["status"] == "live"


def test_missing_required_key_raises(tmp_path):
    entry = _planned_entry()
    del entry["one_liner"]
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="missing required keys"):
        load_manifest(manifest)


def test_invalid_lane_raises(tmp_path):
    entry = _planned_entry()
    entry["lane"] = "Z"
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="invalid lane"):
        load_manifest(manifest)


def test_invalid_status_raises(tmp_path):
    entry = _planned_entry()
    entry["status"] = "shipped"
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="invalid status"):
        load_manifest(manifest)


def test_unknown_key_raises(tmp_path):
    entry = _planned_entry()
    entry["surprise"] = True
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="unknown keys"):
        load_manifest(manifest)


def test_live_missing_required_key_raises(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    del entry["spec"]
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="missing required keys"):
        load_manifest(manifest)


def test_live_missing_data_file_raises(tmp_path):
    _make_live_files(tmp_path)
    (tmp_path / "site" / "data" / "t1.json").unlink()
    manifest = _write_manifest(tmp_path, [_live_entry()])
    with pytest.raises(BuildError, match="missing data file"):
        load_manifest(manifest)


def test_live_dangling_spec_raises(tmp_path):
    _make_live_files(tmp_path)
    (tmp_path / "docs" / "ideas" / "specs" / "t1.md").unlink()
    manifest = _write_manifest(tmp_path, [_live_entry()])
    with pytest.raises(BuildError, match="missing spec file"):
        load_manifest(manifest)


def test_live_standing_note_satisfies_golive(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    del entry["golive"]
    entry["standing_note"] = "this page never goes live"
    manifest = _write_manifest(tmp_path, [entry])
    cards = load_manifest(manifest)
    assert cards[0]["standing_note"] == "this page never goes live"


def test_live_missing_golive_and_standing_note_raises(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    del entry["golive"]
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="missing required keys"):
        load_manifest(manifest)


def test_invalid_theme_raises(tmp_path):
    _make_live_files(tmp_path)
    entry = _live_entry()
    entry["theme"] = "sepia"
    manifest = _write_manifest(tmp_path, [entry])
    with pytest.raises(BuildError, match="invalid theme"):
        load_manifest(manifest)


def test_duplicate_id_raises(tmp_path):
    entry = _planned_entry()
    manifest = _write_manifest(tmp_path, [entry, dict(entry)])
    with pytest.raises(BuildError, match="duplicate card id 's1'"):
        load_manifest(manifest)
