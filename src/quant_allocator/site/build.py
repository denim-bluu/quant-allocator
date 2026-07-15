"""Render-only static-site builder for the idea gallery.

This module validates the card manifest and renders the site.
It must never import numpy, pandas, or simulator modules: the builder renders
committed inputs, it does not compute statistics.
"""

from __future__ import annotations

import json
import shutil
import xml.etree.ElementTree as etree
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import markdown
import yaml
from jinja2 import Environment, FileSystemLoader
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor
from markdown.treeprocessors import Treeprocessor
from markdown.util import AtomicString

REQUIRED_KEYS = {
    "access_contexts",
    "asset_classes",
    "claims",
    "decisions",
    "decision_question",
    "decision_readiness",
    "evidence_roles",
    "id",
    "lane",
    "minimum_data",
    "minimum_data_modalities",
    "one_liner",
    "primary_stage",
    "stages",
    "status",
    "supported_data_modalities",
    "tiers",
    "title",
    "validation_status",
    "vehicle_types",
}
LEGACY_REQUIRED_KEYS = {"id", "title", "lane", "one_liner", "decisions", "tiers", "status"}
PHASE1_REQUIRED_KEYS = REQUIRED_KEYS - LEGACY_REQUIRED_KEYS
OPTIONAL_KEYS = {
    "access_contexts",
    "article",
    "asset_classes",
    "claims",
    "decision_question",
    "decision_readiness",
    "doctrine",
    "demo",
    "data",
    "spec",
    "golive",
    "evidence_roles",
    "minimum_data",
    "minimum_data_modalities",
    "primary_stage",
    "stages",
    "supported_data_modalities",
    "usage_note",
    "standing_note",
    "theme",
    "validation_status",
    "vehicle_types",
}
ALLOWED_KEYS = REQUIRED_KEYS | OPTIONAL_KEYS
VALID_LANES = {"S", "M", "P", "E", "X"}
VALID_STATUSES = {"live", "planned"}
GOLIVE_KEYS = {"data_ask", "sample", "effort"}
VALID_THEMES = {"light", "dark"}
VALID_STAGES = {"discover", "underwrite", "mandate", "construct", "monitor", "govern"}
VALID_ASSET_CLASSES = {
    "cross-asset",
    "public-equity",
    "hedge-funds",
    "rates-macro",
    "fixed-income-credit",
    "structured-credit",
    "private-credit",
    "private-equity",
    "real-assets",
}
VALID_VEHICLE_TYPES = {
    "pooled-fund",
    "fund-of-funds",
    "segregated-mandate",
    "drawdown-fund",
    "co-investment",
    "public-filing-portfolio",
}
VALID_ACCESS_CONTEXTS = {
    "public",
    "pre-hire-public",
    "shortlisted-nda",
    "funded-commingled",
    "funded-private-partnership",
    "segregated-mandate",
    "internal-governance",
}
VALID_DATA_MODALITIES = {
    "returns",
    "documents",
    "exposures",
    "holdings",
    "trades",
    "cashflows-nav",
    "operating-data",
    "filings",
    "mandate-terms",
}
VALID_DECISION_READINESS = {
    "usable-now",
    "data-conditional",
    "prototype",
    "redesign-required",
    "research-finding",
}
VALID_EVIDENCE_ROLES = {
    "operational-analysis",
    "governance-workflow",
    "teaching-simulator",
    "negative-result",
}
VALID_VALIDATION_STATUSES = {
    "synthetic-demo-verified",
    "protocol-ready",
    "live-calibration-required",
    "redesign-required",
    "negative-result",
}
VALID_OUTPUT_TYPES = {
    "exact-measurement",
    "interval",
    "scenario-set",
    "distribution",
    "evidence-graph",
    "verdict",
    "refusal",
}
VALID_ATTESTATIONS = {"A", "B", "C", "D"}
VALID_ACCESS_SEMANTICS = {
    "exact-per-dataset",
    "exact-per-selected-dataset",
    "all-required-per-selected-dataset",
    "all-required-per-dataset",
    "synthetic-fixture-only",
    "refusal-in-every-context",
    "refusal-per-inadmissible-input",
}
CLAIM_KEYS = {
    "id",
    "output_type",
    "access_contexts",
    "access_semantics",
    "current_attestation",
    "live_attestation_ceiling",
    "validation_status",
    "receipt_required",
    "refusal",
}

# Placeholder repo URL; set the real one at Pages enablement (see docs/PUBLISHING.md).
REPO_URL = "https://github.com/denim-bluu/quant-allocator"
SITE_TITLE = "Quant Allocator"
ASSET_VERSION = "editorial-v9"
LANE_ORDER = ["S", "M", "P", "E", "X"]
LANE_HEADINGS = {
    "S": "S — Skill & inference",
    "M": "M — Monitoring & early warning",
    "P": "P — Portfolio construction & governance",
    "E": "E — Engagement & knowledge",
    "X": "X — Meta / infrastructure",
}
CURRICULUM_STEPS = (
    {
        "id": "s2",
        "position": "Foundation · Step 1 of 3",
        "trap": "Treating a point estimate as evidence.",
        "ability": (
            "Read track-record statistics as uncertain estimates and know when to "
            "refuse a conclusion."
        ),
        "reading_time": "12 min",
        "difficulty": "Intermediate",
        "next_reason": (
            "Next, compare several noisy manager records without rewarding the noisiest."
        ),
    },
    {
        "id": "s1",
        "position": "Foundation · Step 2 of 3",
        "trap": "Treating a noisy ranking as a ranking of manager skill.",
        "ability": "Understand shrinkage, partial pooling, and posterior rank uncertainty.",
        "reading_time": "14 min",
        "difficulty": "Intermediate",
        "next_reason": (
            "Next, turn manager-specific uncertainty into a calibrated monitoring baseline."
        ),
    },
    {
        "id": "m3",
        "position": "Foundation · Step 3 of 3",
        "trap": "Applying the same flat drawdown threshold to unlike managers.",
        "ability": (
            "Compare a realized drawdown with the manager-specific null and treat an "
            "alarm as a review trigger rather than an automatic redemption."
        ),
        "reading_time": "13 min",
        "difficulty": "Advanced",
        "next_reason": "Then branch into the five research pillars by the decision at hand.",
    },
)
CURRICULUM_IDS = tuple(step["id"] for step in CURRICULUM_STEPS)
FEATURED_IDS = ("s1", "m3", "m4", "p1", "s7")
ARTICLE_TITLES = {
    "s1": "Hierarchical Bayesian alpha engine",
    "s2": "Uncertainty-honest tear-sheet engine",
    "s3": "Sizing & alpha-decay lab",
    "s4": "Sell-discipline diagnostic",
    "s5": "Short-book quality score",
    "s6": "Returns-only sizing & decay signatures",
    "s7": "Track-record provenance inspector",
    "m1": "Exposure hygiene & drift monitor",
    "m2": "Hidden-convexity / short-vol screen",
    "m3": "Simulation-calibrated drawdown alarms",
    "m4": "Crowding & overlap radar",
    "m5": "Say–do gap monitor",
    "m6": "13F long-book intelligence",
    "p1": "Allocation under alpha uncertainty",
    "p2": "Tiered book X-ray",
    "p3": "Hire/fire decision audit & journal",
    "e1": "Trust-preserving transparency ladder",
    "e2": "Narrated engagement-pack generator",
    "e3": "Manager knowledge graph & retrieval",
    "e4": "Operational evidence & change graph",
    "x1": "Tier & Power Atlas",
    "x2": "Transparency playground",
    "x3": "Manager-universe & sourcing-funnel coverage map",
}
ARTICLE_READING_DETAILS = {
    "s1": ("14 min", "Intermediate"),
    "s2": ("12 min", "Intermediate"),
    "s3": ("12 min", "Advanced"),
    "s4": ("11 min", "Intermediate"),
    "s5": ("13 min", "Advanced"),
    "s6": ("10 min", "Intermediate"),
    "s7": ("11 min", "Intermediate"),
    "m1": ("10 min", "Intermediate"),
    "m2": ("12 min", "Advanced"),
    "m3": ("13 min", "Advanced"),
    "m4": ("11 min", "Intermediate"),
    "m5": ("10 min", "Intermediate"),
    "m6": ("11 min", "Intermediate"),
    "p1": ("12 min", "Advanced"),
    "p2": ("11 min", "Intermediate"),
    "p3": ("11 min", "Intermediate"),
    "e1": ("9 min", "Intermediate"),
    "e2": ("10 min", "Intermediate"),
    "e3": ("11 min", "Intermediate"),
    "e4": ("11 min", "Advanced"),
    "x1": ("14 min", "Advanced"),
    "x2": ("12 min", "Intermediate"),
    "x3": ("10 min", "Intermediate"),
}
ARTICLE_PATHS = (
    ("Foundation", ("s2", "s1", "m3"), "Step"),
    ("Signal & skill", ("s3", "s4", "s5", "s6", "s7"), "Reading"),
    ("Monitoring", ("m1", "m2", "m4", "m5", "m6"), "Reading"),
    ("Portfolio decisions", ("p1", "p2", "p3"), "Reading"),
    ("Evidence & engagement", ("e1", "e2", "e3", "e4"), "Reading"),
    ("Cross-cutting foundations", ("x1", "x2", "x3"), "Reading"),
)


def _public_article_meta() -> dict[str, dict[str, str]]:
    metadata = {}
    for path_label, card_ids, position_label in ARTICLE_PATHS:
        for index, card_id in enumerate(card_ids):
            reading_time, difficulty = ARTICLE_READING_DETAILS[card_id]
            entry = {
                "position": (
                    f"{path_label} · {position_label} {index + 1} of {len(card_ids)}"
                ),
                "reading_time": reading_time,
                "difficulty": difficulty,
            }
            if index:
                previous_id = card_ids[index - 1]
                entry.update(
                    previous_id=previous_id,
                    previous_title=ARTICLE_TITLES[previous_id],
                )
            if index + 1 < len(card_ids):
                next_id = card_ids[index + 1]
                entry.update(next_id=next_id, next_title=ARTICLE_TITLES[next_id])
            metadata[card_id] = entry
    return metadata


PUBLIC_ARTICLE_META = _public_article_meta()
PILLAR_DETAILS = {
    "S": ("Signal & skill", "Measure skill without rewarding noise."),
    "M": ("Monitoring", "Detect change, deterioration, and hidden concentration."),
    "P": ("Portfolio decisions", "Size, combine, and govern under uncertainty."),
    "E": ("Evidence & engagement", "Gather, challenge, and act on dated evidence."),
    "X": ("Cross-cutting foundations", "Define what the available data can support."),
}
TIER_LABELS = {
    "R": "Returns only",
    "E": "Exposure summaries",
    "P": "Positions and trades",
}
EVIDENCE_READINESS_LABELS = {
    "D": "Illustrative synthetic evidence",
    "C": "Evidence-backed interpretation or disclosed scenario",
    "B": "Reproducible manager output",
    "A": "Independently reconstructable evidence",
}
ACCESS_RULE_LABELS = {
    "exact-per-dataset": "Each dataset is evaluated separately.",
    "exact-per-selected-dataset": "Each selected dataset is evaluated separately.",
    "all-required-per-selected-dataset": (
        "All required fields must be present in each selected dataset."
    ),
    "all-required-per-dataset": (
        "All required fields must be present in each dataset."
    ),
    "synthetic-fixture-only": "This result is demonstrated with synthetic data only.",
    "refusal-in-every-context": (
        "No result is produced in the current evidence contexts."
    ),
    "refusal-per-inadmissible-input": (
        "The method stops when an input does not meet its evidence rules."
    ),
}
STAGE_ORDER = ["discover", "underwrite", "mandate", "construct", "monitor", "govern"]
STAGE_HEADINGS = {
    "discover": "Discover opportunities and managers",
    "underwrite": "Underwrite manager and strategy",
    "mandate": "Design mandate and terms",
    "construct": "Construct and fund the portfolio",
    "monitor": "Monitor and re-underwrite",
    "govern": "Govern, learn, and attest",
}
TOKEN_LABELS = {
    "cross-asset": "Cross-asset",
    "public-equity": "Public equity",
    "hedge-funds": "Hedge funds",
    "rates-macro": "Rates and macro",
    "fixed-income-credit": "Fixed income and credit",
    "structured-credit": "Structured credit",
    "private-credit": "Private credit",
    "private-equity": "Private equity",
    "real-assets": "Real assets",
    "pooled-fund": "Pooled fund",
    "fund-of-funds": "Fund of funds",
    "segregated-mandate": "Segregated mandate",
    "drawdown-fund": "Drawdown fund",
    "co-investment": "Co-investment",
    "public-filing-portfolio": "Public filing portfolio",
    "public": "Public",
    "pre-hire-public": "Pre-hire public",
    "shortlisted-nda": "Shortlisted under NDA",
    "funded-commingled": "Funded commingled",
    "funded-private-partnership": "Funded private partnership",
    "internal-governance": "Internal governance",
    "exact-per-dataset": "Exact per dataset",
    "exact-per-selected-dataset": "Exact per selected dataset",
    "all-required-per-selected-dataset": "All required per selected dataset",
    "all-required-per-dataset": "All required per dataset",
    "synthetic-fixture-only": "Synthetic fixture only",
    "refusal-in-every-context": "Refusal in every context",
    "refusal-per-inadmissible-input": "Refusal per inadmissible input",
    "returns": "Returns",
    "documents": "Documents and DDQs",
    "exposures": "Exposures",
    "holdings": "Holdings",
    "trades": "Trades",
    "cashflows-nav": "Cash flows and NAV",
    "operating-data": "Operating data",
    "filings": "Public filings",
    "mandate-terms": "Mandate terms",
    "usable-now": "Usable now",
    "data-conditional": "Data conditional",
    "prototype": "Prototype",
    "redesign-required": "Redesign required",
    "research-finding": "Research finding",
    "synthetic-demo-verified": "Synthetic demo verified",
    "protocol-ready": "Protocol ready",
    "live-calibration-required": "Live calibration required",
    "negative-result": "Negative result",
}
MARKDOWN_EXTENSIONS = ["tables", "fenced_code", "toc"]
MATH_OPEN_PATTERN = r"(?<!\\)(?P<slash_pairs>(?:\\\\)*)(?P<delimiter>\$\$|(?<!\$)\$(?!\$))"


def _preceding_backslashes(data: str, index: int) -> int:
    count = 0
    while index > count and data[index - count - 1] == "\\":
        count += 1
    return count


def _closing_math_delimiter(data: str, start: int, delimiter: str) -> int | None:
    """Find a matching delimiter whose preceding backslash run has even parity."""
    index = start
    while index < len(data):
        if delimiter == "$" and data[index] == "\n":
            return None
        if data.startswith(delimiter, index) and _preceding_backslashes(data, index) % 2 == 0:
            if delimiter == "$" and index + 1 < len(data) and data[index + 1] == "$":
                index += 1
                continue
            return index
        index += 1
    return None


class _MathInlineProcessor(InlineProcessor):
    """Keep balanced TeX delimiters opaque to Markdown's escape/emphasis passes."""

    def handleMatch(self, match, data):  # noqa: N802 - Python-Markdown public API
        delimiter = match.group("delimiter")
        close_start = _closing_math_delimiter(data, match.end(0), delimiter)
        if close_start is None:
            return None, None, None
        close_end = close_start + len(delimiter)
        slash_pairs = match.group("slash_pairs")
        math_start = match.start(0) + len(slash_pairs)
        collapsed_prefix = "\\" * (len(slash_pairs) // 2)
        protected = collapsed_prefix + data[math_start:close_end]
        return AtomicString(protected), match.start(0), close_end


class _EscapedDollarInlineProcessor(InlineProcessor):
    r"""Keep an odd-escaped ``$`` literal and collapse preceding slash pairs."""

    def handleMatch(self, match, data):  # noqa: N802 - Python-Markdown public API
        span = etree.Element("span", {"class": "escaped-dollar"})
        slash_pairs = match.group("slash_pairs")
        span.text = AtomicString("\\" * (len(slash_pairs) // 2) + "$")
        return span, match.start(0), match.end(0)


class _EscapedDisplayDollarInlineProcessor(InlineProcessor):
    r"""Keep an odd-escaped ``$$`` token literal instead of splitting its dollars."""

    def handleMatch(self, match, data):  # noqa: N802 - Python-Markdown public API
        span = etree.Element("span", {"class": "escaped-dollar"})
        slash_pairs = match.group("slash_pairs")
        span.text = AtomicString("\\" * (len(slash_pairs) // 2) + "$$")
        return span, match.start(0), match.end(0)


class _MathProtectionExtension(Extension):
    """Protect code first, then TeX, then Markdown escapes and emphasis."""

    def extendMarkdown(self, md):  # noqa: N802 - Python-Markdown public API
        md.inlinePatterns.register(
            _MathInlineProcessor(MATH_OPEN_PATTERN, md), "protected_math", 186
        )
        md.inlinePatterns.register(
            _EscapedDisplayDollarInlineProcessor(r"(?<!\\)(?P<slash_pairs>(?:\\\\)*)\\\$\$", md),
            "escaped_display_dollar",
            185,
        )
        md.inlinePatterns.register(
            _EscapedDollarInlineProcessor(r"(?<!\\)(?P<slash_pairs>(?:\\\\)*)\\\$(?!\$)", md),
            "escaped_dollar",
            184,
        )


class _SourceLinkTreeprocessor(Treeprocessor):
    """Turn relative source-document links into stable repository links."""

    def __init__(self, md, *, source: Path, repo_root: Path):
        super().__init__(md)
        self.source = source
        self.repo_root = repo_root.resolve()

    def run(self, root):
        for anchor in root.iter("a"):
            href = anchor.get("href", "")
            split = urlsplit(href)
            if split.scheme or split.netloc or not split.path:
                continue
            target = (self.source.parent / unquote(split.path)).resolve()
            try:
                relative = target.relative_to(self.repo_root)
            except ValueError:
                continue
            if not target.exists():
                continue
            repository_href = f"{REPO_URL}/blob/main/{quote(relative.as_posix(), safe='/')}"
            if split.fragment:
                repository_href += f"#{quote(unquote(split.fragment), safe='-._~')}"
            anchor.set("href", repository_href)
        return root


class _SourceLinkExtension(Extension):
    def __init__(self, *, source: Path, repo_root: Path):
        super().__init__()
        self.source = source
        self.repo_root = repo_root

    def extendMarkdown(self, md):  # noqa: N802 - Python-Markdown public API
        md.treeprocessors.register(
            _SourceLinkTreeprocessor(
                md,
                source=self.source,
                repo_root=self.repo_root,
            ),
            "source_links",
            1,
        )


def _markdown_extensions() -> list[str | Extension]:
    return [*MARKDOWN_EXTENSIONS, _MathProtectionExtension()]


class BuildError(Exception):
    """Raised when the manifest or a rendered output violates a build rule.

    The message always names the offending file and the rule that failed.
    """


def load_manifest(path: Path, *, allow_legacy: bool = False) -> list[dict]:
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
        if (
            allow_legacy
            and isinstance(entry, dict)
            and LEGACY_REQUIRED_KEYS <= entry.keys()
            and not (PHASE1_REQUIRED_KEYS & entry.keys())
        ):
            _upgrade_legacy_entry(entry)
        _validate_entry(entry, index, path, site_dir)
        entry_id = entry["id"]
        if entry_id in seen_ids:
            raise BuildError(f"{path}: duplicate card id '{entry_id}'")
        seen_ids.add(entry_id)
        cards.append(entry)
    return cards


def _upgrade_legacy_entry(entry: dict) -> None:
    """Upgrade pre-Phase-1 test fixtures without weakening partial-schema validation."""
    decision_to_stage = {
        "select": "underwrite",
        "size": "construct",
        "monitor": "monitor",
        "redeem": "monitor",
        "engage": "govern",
    }
    stages = []
    for decision in entry["decisions"]:
        stage = decision_to_stage.get(decision, "underwrite")
        if stage not in stages:
            stages.append(stage)
    if not stages:
        stages = ["underwrite"]

    supported = []
    tier_modalities = {"R": "returns", "E": "exposures", "P": "holdings"}
    for tier in entry["tiers"]:
        modality = tier_modalities.get(tier)
        if modality and modality not in supported:
            supported.append(modality)
    if not supported:
        supported = ["documents"]
    access = ["pre-hire-public"]
    entry.update(
        {
            "decision_question": entry["one_liner"],
            "primary_stage": stages[0],
            "stages": stages,
            "asset_classes": ["cross-asset"],
            "vehicle_types": ["pooled-fund"],
            "access_contexts": access,
            "supported_data_modalities": supported,
            "minimum_data_modalities": [supported[0]],
            "decision_readiness": "prototype",
            "evidence_roles": ["operational-analysis"],
            "minimum_data": "Legacy fixture metadata; not a production data contract.",
            "validation_status": "synthetic-demo-verified",
            "claims": [
                {
                    "id": "legacy-fixture-claim",
                    "output_type": "verdict",
                    "access_contexts": access,
                    "access_semantics": "all-required-per-selected-dataset",
                    "current_attestation": "D",
                    "live_attestation_ceiling": "D",
                    "validation_status": "synthetic-demo-verified",
                    "receipt_required": False,
                    "refusal": "This compatibility metadata is not a live evidence contract.",
                }
            ],
        }
    )


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

    _validate_phase1_metadata(entry, card_id, path)

    theme = entry.get("theme")
    if theme is not None and theme not in VALID_THEMES:
        raise BuildError(
            f"{path}: card '{card_id}' has invalid theme '{theme}' "
            f"(must be one of {sorted(VALID_THEMES)})"
        )

    if entry["status"] == "live":
        _validate_live_entry(entry, card_id, path, site_dir)


def _validate_token_list(
    entry: dict,
    key: str,
    allowed: set[str],
    card_id: str,
    path: Path,
) -> None:
    values = entry[key]
    if not isinstance(values, list) or not values or not all(isinstance(v, str) for v in values):
        raise BuildError(f"{path}: card '{card_id}' {key} must be a non-empty string list")
    if len(values) != len(set(values)):
        raise BuildError(f"{path}: card '{card_id}' {key} contains duplicate values")
    invalid = set(values) - allowed
    if invalid:
        raise BuildError(f"{path}: card '{card_id}' has invalid {key}: {sorted(invalid)}")


def _validate_phase1_metadata(entry: dict, card_id: str, path: Path) -> None:
    for key in ("decision_question", "minimum_data"):
        if not isinstance(entry[key], str) or not entry[key].strip():
            raise BuildError(f"{path}: card '{card_id}' {key} must be a non-empty string")

    list_fields = {
        "stages": VALID_STAGES,
        "asset_classes": VALID_ASSET_CLASSES,
        "vehicle_types": VALID_VEHICLE_TYPES,
        "access_contexts": VALID_ACCESS_CONTEXTS,
        "supported_data_modalities": VALID_DATA_MODALITIES,
        "minimum_data_modalities": VALID_DATA_MODALITIES,
        "evidence_roles": VALID_EVIDENCE_ROLES,
    }
    for key, allowed in list_fields.items():
        _validate_token_list(entry, key, allowed, card_id, path)

    primary_stage = entry["primary_stage"]
    if primary_stage not in VALID_STAGES:
        raise BuildError(f"{path}: card '{card_id}' has invalid primary_stage '{primary_stage}'")
    if primary_stage not in entry["stages"]:
        raise BuildError(f"{path}: card '{card_id}' primary_stage must appear in stages")

    unsupported_minimum = set(entry["minimum_data_modalities"]) - set(
        entry["supported_data_modalities"]
    )
    if unsupported_minimum:
        raise BuildError(
            f"{path}: card '{card_id}' minimum_data_modalities must be a subset of "
            "supported_data_modalities"
        )

    if entry["decision_readiness"] not in VALID_DECISION_READINESS:
        raise BuildError(
            f"{path}: card '{card_id}' has invalid decision_readiness "
            f"'{entry['decision_readiness']}'"
        )
    if entry["validation_status"] not in VALID_VALIDATION_STATUSES:
        raise BuildError(
            f"{path}: card '{card_id}' has invalid validation_status "
            f"'{entry['validation_status']}'"
        )

    claims = entry["claims"]
    if not isinstance(claims, list) or not claims:
        raise BuildError(f"{path}: card '{card_id}' claims must be a non-empty list")
    claim_ids: set[str] = set()
    claim_access_union: set[str] = set()
    for claim_index, claim in enumerate(claims):
        if not isinstance(claim, dict) or set(claim) != CLAIM_KEYS:
            raise BuildError(
                f"{path}: card '{card_id}' claim #{claim_index} must define exactly "
                f"{sorted(CLAIM_KEYS)}"
            )
        claim_id = claim["id"]
        if not isinstance(claim_id, str) or not claim_id.strip() or claim_id in claim_ids:
            raise BuildError(f"{path}: card '{card_id}' has empty or duplicate claim id")
        claim_ids.add(claim_id)
        if claim["output_type"] not in VALID_OUTPUT_TYPES:
            raise BuildError(f"{path}: card '{card_id}' claim '{claim_id}' has invalid output_type")
        if (
            not isinstance(claim["access_semantics"], str)
            or claim["access_semantics"] not in VALID_ACCESS_SEMANTICS
        ):
            raise BuildError(
                f"{path}: card '{card_id}' claim '{claim_id}' has invalid access_semantics"
            )
        claim_access = claim["access_contexts"]
        if (
            not isinstance(claim_access, list)
            or not claim_access
            or len(claim_access) != len(set(claim_access))
            or set(claim_access) - VALID_ACCESS_CONTEXTS
            or set(claim_access) - set(entry["access_contexts"])
        ):
            raise BuildError(
                f"{path}: card '{card_id}' claim '{claim_id}' has invalid access_contexts"
            )
        claim_access_union.update(claim_access)
        for attestation_key in ("current_attestation", "live_attestation_ceiling"):
            if claim[attestation_key] not in VALID_ATTESTATIONS:
                raise BuildError(
                    f"{path}: card '{card_id}' claim '{claim_id}' has invalid {attestation_key}"
                )
        if claim["validation_status"] not in VALID_VALIDATION_STATUSES:
            raise BuildError(
                f"{path}: card '{card_id}' claim '{claim_id}' has invalid validation_status"
            )
        if not isinstance(claim["receipt_required"], bool):
            raise BuildError(
                f"{path}: card '{card_id}' claim '{claim_id}' receipt_required must be boolean"
            )
        if claim["live_attestation_ceiling"] in {"A", "B"} and not claim["receipt_required"]:
            raise BuildError(
                f"{path}: card '{card_id}' claim '{claim_id}' A/B ceiling requires a receipt"
            )
        if not isinstance(claim["refusal"], str) or not claim["refusal"].strip():
            raise BuildError(f"{path}: card '{card_id}' claim '{claim_id}' refusal is required")

    if set(entry["access_contexts"]) != claim_access_union:
        raise BuildError(
            f"{path}: card '{card_id}' access_contexts must exactly equal claim "
            "access_contexts union"
        )


def _validate_live_entry(entry: dict, card_id: str, path: Path, site_dir: Path) -> None:
    is_doctrine = entry.get("doctrine", False)

    required_live = {"demo", "spec"}
    if is_doctrine:
        required_live |= {"usage_note"}
    else:
        required_live |= {"data"}
        standing_note = entry.get("standing_note")
        if standing_note is not None and not (
            isinstance(standing_note, str) and standing_note.strip()
        ):
            # An empty note would fall through to the golive-box branch and crash
            # on Undefined golive fields — fail with a named error instead.
            raise BuildError(
                f"{path}: live card '{card_id}' standing_note must be a non-empty string"
            )
        if standing_note is None:
            required_live |= {"golive"}
    missing = required_live - entry.keys()
    if missing:
        raise BuildError(
            f"{path}: live card '{card_id}' is missing required keys: {sorted(missing)}"
        )

    if not is_doctrine and "golive" in entry:
        golive = entry["golive"]
        if not isinstance(golive, dict) or GOLIVE_KEYS - golive.keys():
            raise BuildError(
                f"{path}: live card '{card_id}' golive must define keys {sorted(GOLIVE_KEYS)}"
            )

    referenced = {
        "demo": site_dir / "templates" / entry["demo"],
        "spec": site_dir.parent / "docs" / "ideas" / "specs" / entry["spec"],
    }
    if "article" in entry:
        referenced["article"] = (
            site_dir.parent / "docs" / "ideas" / "articles" / entry["article"]
        )
    if not is_doctrine:
        referenced["data"] = site_dir / "data" / entry["data"]

    for kind, file_path in referenced.items():
        if not file_path.exists():
            raise BuildError(
                f"{path}: live card '{card_id}' references missing {kind} file: {file_path}"
            )


def build(site_dir: Path, out_dir: Path, *, allow_legacy: bool = False) -> None:
    """Validate the manifest, render index/specs/demo pages, copy assets, lint."""
    cards = load_manifest(site_dir / "cards.yaml", allow_legacy=allow_legacy)
    public_cards = [_public_card(card) for card in cards]

    env = Environment(
        loader=FileSystemLoader(str(site_dir / "templates")),
        autoescape=True,
    )
    env.globals["repo_url"] = REPO_URL
    env.globals["site_title"] = SITE_TITLE
    env.globals["asset_version"] = ASSET_VERSION
    env.globals["stage_headings"] = STAGE_HEADINGS
    env.globals["labels"] = TOKEN_LABELS

    out_dir.mkdir(parents=True, exist_ok=True)
    _render_index(env, public_cards, out_dir)
    _render_specs(env, public_cards, site_dir, out_dir)
    _render_demo_pages(env, public_cards, site_dir, out_dir)
    _copy_assets(site_dir, out_dir)
    _lint_outputs(public_cards, out_dir)


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _public_card(card: dict) -> dict:
    """Project internal manifest data into reader-facing labels and sentences."""
    projected = dict(card)
    claims = card.get("claims", [])
    projected["pillar_heading"] = PILLAR_DETAILS[card["lane"]][0]
    projected["tier_labels"] = [TIER_LABELS[tier] for tier in card["tiers"]]
    projected["public_access_rules"] = _dedupe(
        [ACCESS_RULE_LABELS[claim["access_semantics"]] for claim in claims]
    )
    projected["public_current_readiness"] = _dedupe(
        [EVIDENCE_READINESS_LABELS[claim["current_attestation"]] for claim in claims]
    )
    projected["public_live_readiness"] = _dedupe(
        [
            EVIDENCE_READINESS_LABELS[claim["live_attestation_ceiling"]]
            for claim in claims
        ]
    )
    projected["claim_access_contexts"] = sorted(
        {access for claim in claims for access in claim["access_contexts"]}
    )
    projected["search_corpus"] = _search_corpus(projected)
    return projected


def _render_index(env: Environment, cards: list[dict], out_dir: Path) -> None:
    view_cards = [dict(card) for card in cards]
    cards_by_id = {card["id"]: card for card in view_cards}
    start_here = []
    for step in CURRICULUM_STEPS:
        if step["id"] not in cards_by_id:
            continue
        curriculum_card = dict(cards_by_id[step["id"]])
        curriculum_card.update(step)
        start_here.append(curriculum_card)
    featured_cards = [
        cards_by_id[card_id] for card_id in FEATURED_IDS if card_id in cards_by_id
    ]
    pillars = [
        {
            "key": lane,
            "heading": PILLAR_DETAILS[lane][0],
            "description": PILLAR_DETAILS[lane][1],
            "cards": [card for card in view_cards if card["lane"] == lane],
        }
        for lane in LANE_ORDER
    ]
    stages = []
    for stage in STAGE_ORDER:
        stage_cards = [card for card in view_cards if card["primary_stage"] == stage]
        if stage_cards:
            stages.append(
                {
                    "key": stage,
                    "heading": STAGE_HEADINGS[stage],
                    "cards": stage_cards,
                }
            )
    html = env.get_template("index.html.j2").render(
        start_here=start_here,
        featured_cards=featured_cards,
        pillars=pillars,
        stages=stages,
        cards=view_cards,
        stage_headings=STAGE_HEADINGS,
        labels=TOKEN_LABELS,
        asset_options=sorted(VALID_ASSET_CLASSES),
        vehicle_options=sorted(VALID_VEHICLE_TYPES),
        access_options=sorted(VALID_ACCESS_CONTEXTS),
        modality_options=sorted(VALID_DATA_MODALITIES),
        readiness_options=[
            "usable-now",
            "data-conditional",
            "prototype",
            "redesign-required",
            "research-finding",
        ],
        lane_options=LANE_ORDER,
        page_title="Idea Gallery",
        is_home=True,
        asset_base="",
        default_theme="light",
    )
    (out_dir / "index.html").write_text(html, encoding="utf-8")
    exhibits_html = env.get_template("exhibits.html.j2").render(
        pillars=[
            {
                **pillar,
                "cards": [card for card in pillar["cards"] if card["status"] == "live"],
            }
            for pillar in pillars
            if any(card["status"] == "live" for card in pillar["cards"])
        ],
        page_title="Exhibits",
        asset_base="",
        default_theme="light",
    )
    (out_dir / "exhibits.html").write_text(exhibits_html, encoding="utf-8")


def _search_corpus(card: dict) -> str:
    """Return reader-facing search text without internal claim metadata."""
    parts = [
        card["title"],
        card["one_liner"],
        card["decision_question"],
        card["minimum_data"],
        STAGE_HEADINGS[card["primary_stage"]],
        TOKEN_LABELS[card["decision_readiness"]],
        card["pillar_heading"],
    ]
    parts.extend(card["tier_labels"])
    for field in (
        "asset_classes",
        "vehicle_types",
        "access_contexts",
        "supported_data_modalities",
        "minimum_data_modalities",
    ):
        parts.extend(TOKEN_LABELS[value] for value in card[field])
    return " ".join(_dedupe(parts))


def _copy_assets(site_dir: Path, out_dir: Path) -> None:
    dest = out_dir / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(site_dir / "assets", dest)


def _render_specs(env: Environment, cards: list[dict], site_dir: Path, out_dir: Path) -> None:
    template = env.get_template("spec.html.j2")
    specs_dir = site_dir.parent / "docs" / "ideas" / "specs"
    articles_dir = site_dir.parent / "docs" / "ideas" / "articles"
    out_specs = out_dir / "specs"
    out_specs.mkdir(parents=True, exist_ok=True)
    for card in cards:
        if card["status"] != "live":
            continue
        is_public_article = bool(card.get("article"))
        source = (
            articles_dir / card["article"]
            if is_public_article
            else specs_dir / card["spec"]
        )
        renderer = markdown.Markdown(
            extensions=[
                *_markdown_extensions(),
                _SourceLinkExtension(source=source, repo_root=site_dir.parent),
            ]
        )
        body_html = renderer.convert(source.read_text(encoding="utf-8"))
        method_source_url = (
            f"{REPO_URL}/blob/main/docs/ideas/specs/{quote(card['spec'], safe='')}"
        )
        html = template.render(
            page_title=card["title"],
            card=card,
            spec_html=body_html,
            article_toc=renderer.toc if is_public_article else "",
            article_meta=PUBLIC_ARTICLE_META.get(card["id"], {}),
            is_public_article=is_public_article,
            method_source_url=method_source_url,
            asset_base="../",
            default_theme="light",
        )
        (out_specs / f"{card['id']}.html").write_text(html, encoding="utf-8")


def _render_demo_pages(
    env: Environment, cards: list[dict], site_dir: Path, out_dir: Path
) -> None:
    card_titles = {card["id"]: card["title"] for card in cards}
    for card in cards:
        if card["status"] != "live":
            continue
        card_data_json = ""
        card_data = None
        if not card.get("doctrine", False):
            card_data_json = (site_dir / "data" / card["data"]).read_text(encoding="utf-8")
            card_data = json.loads(card_data_json)

        curriculum_previous = None
        curriculum_next = None
        if card["id"] in CURRICULUM_IDS:
            curriculum_index = CURRICULUM_IDS.index(card["id"])
            if curriculum_index > 0:
                previous_id = CURRICULUM_IDS[curriculum_index - 1]
                curriculum_previous = {
                    "href": f"{previous_id}.html",
                    "title": ARTICLE_TITLES[previous_id],
                }
            if curriculum_index < len(CURRICULUM_IDS) - 1:
                next_id = CURRICULUM_IDS[curriculum_index + 1]
                curriculum_next = {
                    "href": f"{next_id}.html",
                    "title": ARTICLE_TITLES[next_id],
                }
            else:
                curriculum_next = {
                    "href": "index.html#research",
                    "title": "Continue to the research pillars",
                }
        html = env.get_template(card["demo"]).render(
            page_title=card["title"],
            card=card,
            card_data_json=card_data_json,
            card_data=card_data,
            card_titles=card_titles,
            curriculum_previous=curriculum_previous,
            curriculum_next=curriculum_next,
            asset_base="",
            default_theme=card.get("theme", "light"),
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
            if "golive-box" not in html and "golive-replaced" not in html:
                raise BuildError(
                    f"{page_path}: card '{card['id']}' output missing golive-box "
                    f"or standing-note (golive-replaced)"
                )

        if "card-context" not in html:
            raise BuildError(
                f"{page_path}: card '{card['id']}' output missing card-context block"
            )

        spec_target = out_dir / "specs" / f"{card['id']}.html"
        if not spec_target.exists():
            raise BuildError(
                f"{page_path}: card '{card['id']}' spec link target missing: {spec_target}"
            )
