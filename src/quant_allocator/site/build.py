"""Render-only static-site builder for the idea gallery.

This module validates the card manifest and (in later tasks) renders the site.
It must never import numpy, pandas, or simulator modules: the builder renders
committed inputs, it does not compute statistics.
"""

from __future__ import annotations

from pathlib import Path

import yaml

REQUIRED_KEYS = {"id", "title", "lane", "one_liner", "decisions", "tiers", "status"}
OPTIONAL_KEYS = {"doctrine", "demo", "data", "spec", "golive", "usage_note"}
ALLOWED_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS
VALID_LANES = {"S", "M", "P", "E", "X"}
VALID_STATUSES = {"live", "planned"}
GOLIVE_KEYS = {"data_ask", "sample", "effort"}


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
    for index, entry in enumerate(raw):
        _validate_entry(entry, index, path, site_dir)
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
