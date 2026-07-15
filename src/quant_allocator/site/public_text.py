"""Reader-facing HTML checks for internal publication language."""

from __future__ import annotations

import re
from collections.abc import Collection, Iterable
from dataclasses import dataclass
from html.parser import HTMLParser


_IGNORED_ELEMENTS = {"pre", "script", "style", "template"}
_ACCESSIBLE_ATTRIBUTES = {"alt", "aria-label", "placeholder", "title"}


@dataclass(frozen=True)
class PublicTextViolation:
    rule: str
    excerpt: str


class _PublicTextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._ignored_depth = 0
        self.segments: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if self._ignored_depth:
            self._ignored_depth += 1
            return
        if tag in _IGNORED_ELEMENTS:
            self._ignored_depth = 1
            return
        for name, value in attrs:
            if name in _ACCESSIBLE_ATTRIBUTES and value:
                self.segments.append(value)

    def handle_startendtag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        if not self._ignored_depth and tag not in _IGNORED_ELEMENTS:
            for name, value in attrs:
                if name in _ACCESSIBLE_ATTRIBUTES and value:
                    self.segments.append(value)

    def handle_endtag(self, tag: str) -> None:
        if self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth and data.strip():
            self.segments.append(data)


def _exact_token_pattern(values: Collection[str]) -> re.Pattern[str] | None:
    tokens = sorted({value for value in values if value}, key=len, reverse=True)
    if not tokens:
        return None
    alternatives = "|".join(re.escape(value) for value in tokens)
    return re.compile(rf"(?<![A-Za-z0-9])(?:{alternatives})(?![A-Za-z0-9])")


def _excerpt(text: str, match: re.Match[str]) -> str:
    normalized = re.sub(r"\s+", " ", text).strip()
    needle = re.sub(r"\s+", " ", match.group(0)).strip()
    position = normalized.find(needle)
    if position < 0:
        return normalized[:160]
    start = max(0, position - 60)
    end = min(len(normalized), position + len(needle) + 60)
    return normalized[start:end]


def _matches(
    segments: Iterable[str], rule: str, pattern: re.Pattern[str]
) -> Iterable[PublicTextViolation]:
    for segment in segments:
        for match in pattern.finditer(segment):
            yield PublicTextViolation(rule=rule, excerpt=_excerpt(segment, match))


def public_text_violations(
    html: str,
    *,
    card_ids: Collection[str],
    claim_ids: Collection[str],
    access_semantics: Collection[str],
) -> tuple[PublicTextViolation, ...]:
    """Return internal-language violations from reader-encounterable HTML copy."""
    parser = _PublicTextParser()
    parser.feed(html)

    patterns: list[tuple[str, re.Pattern[str] | None]] = [
        ("card-id", _exact_token_pattern(card_ids)),
        ("claim-id", _exact_token_pattern(claim_ids)),
        ("access-semantics", _exact_token_pattern(access_semantics)),
        (
            "readiness-grade",
            re.compile(r"\b(?:Current|Live ceiling)\s+[A-D]\b"),
        ),
        (
            "governance-language",
            re.compile(
                r"\b(?:access semantics|attestation|claim ID|state key|reason code)\b",
                re.IGNORECASE,
            ),
        ),
        (
            "workflow-language",
            re.compile(
                r"\b(?:wave-\d+|repository history|ship rule|PILOT|committed JSON|"
                r"fixture|harness|source card|render payload|registry row|"
                r"PowerGate registry)\b",
            ),
        ),
        (
            "raw-hash",
            re.compile(r"\b(?:receipt:)?sha256:[0-9a-f]{8,}\b", re.IGNORECASE),
        ),
    ]

    violations: list[PublicTextViolation] = []
    for rule, pattern in patterns:
        if pattern is not None:
            violations.extend(_matches(parser.segments, rule, pattern))
    return tuple(dict.fromkeys(violations))
