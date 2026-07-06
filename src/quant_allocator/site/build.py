"""Render-only static-site builder for the idea gallery.

This module validates the card manifest and renders the site.
It must never import numpy, pandas, or simulator modules: the builder renders
committed inputs, it does not compute statistics.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader

REQUIRED_KEYS = {"id", "title", "lane", "one_liner", "decisions", "tiers", "status"}
OPTIONAL_KEYS = {"doctrine", "demo", "data", "spec", "golive", "usage_note"}
ALLOWED_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS
VALID_LANES = {"S", "M", "P", "E", "X"}
VALID_STATUSES = {"live", "planned"}
GOLIVE_KEYS = {"data_ask", "sample", "effort"}

# Placeholder repo URL; set the real one at Pages enablement (see docs/PUBLISHING.md).
REPO_URL = "https://github.com/USERNAME/quant-allocator"
SITE_TITLE = "Quant Allocator — Idea Gallery"
LANE_ORDER = ["S", "M", "P", "E", "X"]
LANE_HEADINGS = {
    "S": "S — Skill & inference",
    "M": "M — Monitoring & early warning",
    "P": "P — Portfolio construction & governance",
    "E": "E — Engagement & knowledge",
    "X": "X — Meta / infrastructure",
}
MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "toc"]


class BuildError(Exception):
    """Raised when the manifest or a rendered output violates a build rule.

    The message always names the offending file and the rule that failed.
    """


def load_manifest(path: Path) -> list[dict]:
    """Load and strictly validate the card manifest at ``path``.

    ``site_dir`` is ``path.parent``. Referenced files are resolved relative to
    the repo layout: demo under ``site_dir/templates``, data under
    ``site_dir/data``, spec under ``site_dir.parent/docs/ideas/specs``.
    """
    site_dir = path.parent
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise BuildError(f"{path}: manifest must be a YAML list of card entries")

    cards: list[dict] = []
    seen_ids: set[str] = set()
    for index, entry in enumerate(raw):
        _validate_entry(entry, index, path, site_dir)
        entry_id = entry["id"]
        if entry_id in seen_ids:
            raise BuildError(f"{path}: duplicate card id '{entry_id}'")
        seen_ids.add(entry_id)
        cards.append(entry)
    return cards


def _validate_entry(entry: object, index: int, path: Path, site_dir: Path) -> None:
    if not isinstance(entry, dict):
        raise BuildError(f"{path}: entry #{index} is not a mapping")

    card_id = entry.get("id", f"#{index}")

    missing = REQUIRED_KEYS - entry.keys()
    if missing:
        raise BuildError(
            f"{path}: card '{card_id}' is missing required keys: {sorted(missing)}"
        )

    unknown = entry.keys() - ALLOWED_KEYS
    if unknown:
        raise BuildError(f"{path}: card '{card_id}' has unknown keys: {sorted(unknown)}")

    if entry["lane"] not in VALID_LANES:
        raise BuildError(
            f"{path}: card '{card_id}' has invalid lane '{entry['lane']}' "
            f"(must be one of {sorted(VALID_LANES)})"
        )

    if entry["status"] not in VALID_STATUSES:
        raise BuildError(
            f"{path}: card '{card_id}' has invalid status '{entry['status']}' "
            f"(must be one of {sorted(VALID_STATUSES)})"
        )

    if entry["status"] == "live":
        _validate_live_entry(entry, card_id, path, site_dir)


def _validate_live_entry(entry: dict, card_id: str, path: Path, site_dir: Path) -> None:
    is_doctrine = entry.get("doctrine", False)

    required_live = {"demo", "spec"}
    required_live |= {"usage_note"} if is_doctrine else {"data", "golive"}
    missing = required_live - entry.keys()
    if missing:
        raise BuildError(
            f"{path}: live card '{card_id}' is missing required keys: {sorted(missing)}"
        )

    if not is_doctrine:
        golive = entry["golive"]
        if not isinstance(golive, dict) or GOLIVE_KEYS - golive.keys():
            raise BuildError(
                f"{path}: live card '{card_id}' golive must define keys {sorted(GOLIVE_KEYS)}"
            )

    referenced = {
        "demo": site_dir / "templates" / entry["demo"],
        "spec": site_dir.parent / "docs" / "ideas" / "specs" / entry["spec"],
    }
    if not is_doctrine:
        referenced["data"] = site_dir / "data" / entry["data"]

    for kind, file_path in referenced.items():
        if not file_path.exists():
            raise BuildError(
                f"{path}: live card '{card_id}' references missing {kind} file: {file_path}"
            )


def build(site_dir: Path, out_dir: Path) -> None:
    """Validate the manifest, render index/specs/demo pages, copy assets, lint."""
    cards = load_manifest(site_dir / "cards.yaml")

    env = Environment(
        loader=FileSystemLoader(str(site_dir / "templates")),
        autoescape=True,
    )
    env.globals["repo_url"] = REPO_URL
    env.globals["site_title"] = SITE_TITLE

    out_dir.mkdir(parents=True, exist_ok=True)
    _render_index(env, cards, out_dir)
    _render_specs(env, cards, site_dir, out_dir)
    _render_demo_pages(env, cards, site_dir, out_dir)
    _copy_assets(site_dir, out_dir)
    _lint_outputs(cards, out_dir)


def _render_index(env: Environment, cards: list[dict], out_dir: Path) -> None:
    lanes = [
        {
            "key": lane,
            "heading": LANE_HEADINGS[lane],
            "cards": [card for card in cards if card["lane"] == lane],
        }
        for lane in LANE_ORDER
    ]
    html = env.get_template("index.html.j2").render(
        lanes=lanes, page_title="Idea Gallery", asset_base="", default_theme="light"
    )
    (out_dir / "index.html").write_text(html, encoding="utf-8")


def _copy_assets(site_dir: Path, out_dir: Path) -> None:
    dest = out_dir / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(site_dir / "assets", dest)


def _render_specs(env: Environment, cards: list[dict], site_dir: Path, out_dir: Path) -> None:
    template = env.get_template("spec.html.j2")
    specs_dir = site_dir.parent / "docs" / "ideas" / "specs"
    out_specs = out_dir / "specs"
    out_specs.mkdir(parents=True, exist_ok=True)
    for card in cards:
        if card["status"] != "live":
            continue
        source = specs_dir / card["spec"]
        body_html = markdown.markdown(
            source.read_text(encoding="utf-8"), extensions=MARKDOWN_EXTENSIONS
        )
        html = template.render(
            page_title=card["title"],
            card=card,
            spec_html=body_html,
            asset_base="../",
            default_theme="light",
        )
        (out_specs / f"{card['id']}.html").write_text(html, encoding="utf-8")


def _render_demo_pages(
    env: Environment, cards: list[dict], site_dir: Path, out_dir: Path
) -> None:
    for card in cards:
        if card["status"] != "live":
            continue
        card_data_json = ""
        card_data = None
        if not card.get("doctrine", False):
            card_data_json = (site_dir / "data" / card["data"]).read_text(encoding="utf-8")
            card_data = json.loads(card_data_json)
        html = env.get_template(card["demo"]).render(
            page_title=card["title"],
            card=card,
            card_data_json=card_data_json,
            card_data=card_data,
            asset_base="",
            default_theme="light",
        )
        (out_dir / f"{card['id']}.html").write_text(html, encoding="utf-8")


def _lint_outputs(cards: list[dict], out_dir: Path) -> None:
    """Fail loudly if any live page is missing its provenance furniture or spec link."""
    for card in cards:
        if card["status"] != "live":
            continue
        page_path = out_dir / f"{card['id']}.html"
        html = page_path.read_text(encoding="utf-8")

        if card.get("doctrine", False):
            if "usage-note" not in html:
                raise BuildError(
                    f"{page_path}: doctrine card '{card['id']}' output missing usage-note block"
                )
        else:
            if "synthetic-badge" not in html:
                raise BuildError(
                    f"{page_path}: card '{card['id']}' output missing synthetic-badge"
                )
            if "golive-box" not in html:
                raise BuildError(
                    f"{page_path}: card '{card['id']}' output missing golive-box"
                )

        spec_target = out_dir / "specs" / f"{card['id']}.html"
        if not spec_target.exists():
            raise BuildError(
                f"{page_path}: card '{card['id']}' spec link target missing: {spec_target}"
            )
