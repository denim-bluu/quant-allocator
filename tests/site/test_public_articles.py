import re
import shutil
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from quant_allocator.site.build import build


REPO_ROOT = Path(__file__).resolve().parents[2]
ARTICLES_DIR = REPO_ROOT / "docs" / "ideas" / "articles"
CARDS_PATH = REPO_ROOT / "site" / "cards.yaml"
HEADING_SEQUENCE = (
    "## The decision",
    "## Why the obvious answer fails",
    "## The intuition",
    "## A small numerical example",
    "## The method",
    "## What the evidence changes",
    "## What the allocator does next",
    "## Limits and go-live",
    "## Key takeaways",
    "## References",
)
OPENING_INTERNAL_MARKERS = (
    "**Date:**",
    "**Status:**",
    "**Card:**",
    "**Demo:**",
    "**Source:**",
    "Displayed field",
    "JSON field",
    "review ruling",
    "implementation docket",
)
HREF_RE = re.compile(r'href="([^"]+)"')
MARKDOWN_LINK_RE = re.compile(r"\[[^\]]+\]\(([^)]+)\)")
WORD_RE = re.compile(r"\b[\w][\w’'\-]*\b", re.UNICODE)


def _live_cards():
    cards = yaml.safe_load(CARDS_PATH.read_text(encoding="utf-8"))
    return [card for card in cards if card["status"] == "live"]


class _ArticleText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_body = False
        self.body_depth = 0
        self.excluded_depth = 0
        self.parts: list[str] = []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "").split()
        if "spec-page__body" in classes:
            self.in_body = True
            self.body_depth = 1
            return
        if not self.in_body:
            return
        self.body_depth += 1
        if tag in {"script", "style", "nav"}:
            self.excluded_depth += 1

    def handle_endtag(self, tag):
        if not self.in_body:
            return
        if tag in {"script", "style", "nav"} and self.excluded_depth:
            self.excluded_depth -= 1
        self.body_depth -= 1
        if self.body_depth == 0:
            self.in_body = False

    def handle_data(self, data):
        if self.in_body and not self.excluded_depth:
            self.parts.append(data)


def test_every_live_card_has_an_explicit_public_article_source():
    missing = []
    for card in _live_cards():
        article = card.get("article")
        if not article:
            missing.append(f'{card["id"]}: missing article field')
        elif not (ARTICLES_DIR / article).is_file():
            missing.append(f'{card["id"]}: missing {article}')

    assert missing == []


def test_public_article_sources_follow_the_reader_sequence():
    for card in _live_cards():
        article = card.get("article")
        if not article:
            continue
        source = (ARTICLES_DIR / article).read_text(encoding="utf-8")
        assert source.lstrip().startswith("## The decision"), card["id"]
        assert re.search(r"^#\s+", source, re.MULTILINE) is None, card["id"]
        positions = [source.index(heading) for heading in HEADING_SEQUENCE]
        assert positions == sorted(positions), card["id"]
        opening = "\n".join(source.splitlines()[:50])
        for marker in OPENING_INTERNAL_MARKERS:
            assert marker.lower() not in opening.lower(), f"{card['id']}: {marker}"


def test_public_article_markdown_links_are_public_and_resolve():
    for card in _live_cards():
        article = card.get("article")
        if not article:
            continue
        source_path = ARTICLES_DIR / article
        source = source_path.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK_RE.findall(source):
            parsed = urlsplit(target)
            if parsed.scheme in {"http", "https", "mailto"} or target.startswith("#"):
                continue
            resolved = (source_path.parent / parsed.path).resolve()
            assert resolved.is_file(), f"{card['id']}: unresolved article link {target}"
            assert REPO_ROOT not in resolved.parents or ARTICLES_DIR in resolved.parents


def test_rendered_public_articles_have_method_links_and_reader_word_counts(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)

    for card in _live_cards():
        if not card.get("article"):
            continue
        page = out / "specs" / f'{card["id"]}.html'
        html = page.read_text(encoding="utf-8")
        assert "Technical method and provenance" in html, card["id"]
        assert html.count("Open the paired exhibit") == 2, card["id"]
        parser = _ArticleText()
        parser.feed(html)
        word_count = len(WORD_RE.findall(unescape(" ".join(parser.parts))))
        assert 900 <= word_count <= 3500, f"{card['id']}: {word_count} rendered words"


def test_rendered_public_article_internal_links_resolve(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)

    for card in _live_cards():
        if not card.get("article"):
            continue
        page = out / "specs" / f'{card["id"]}.html'
        html = page.read_text(encoding="utf-8")
        for target in HREF_RE.findall(html):
            parsed = urlsplit(unescape(target))
            if parsed.scheme or target.startswith("#"):
                continue
            assert (page.parent / parsed.path).resolve().is_file(), (
                f"{card['id']}: unresolved rendered link {target}"
            )


def test_foundation_article_metadata_and_path_navigation_are_shared(tmp_path):
    repo = tmp_path / "repo"
    shutil.copytree(REPO_ROOT / "site", repo / "site")
    shutil.copytree(REPO_ROOT / "docs" / "ideas" / "specs", repo / "docs" / "ideas" / "specs")
    shutil.copytree(ARTICLES_DIR, repo / "docs" / "ideas" / "articles")
    manifest = repo / "site" / "cards.yaml"
    cards = yaml.safe_load(manifest.read_text(encoding="utf-8"))
    s1 = next(card for card in cards if card["id"] == "s1")
    s1["article"] = "s2-uncertainty-honest-tear-sheet.md"
    manifest.write_text(yaml.safe_dump(cards, sort_keys=False), encoding="utf-8")

    out = tmp_path / "out-foundation"
    build(repo / "site", out)
    html = (out / "specs" / "s1.html").read_text(encoding="utf-8")

    assert "Foundation · Step 2 of 3" in html
    assert "14 min read" in html
    assert "Intermediate" in html
    assert "Previous in this path" in html
    assert 'href="s2.html">Uncertainty-honest tear-sheet engine</a>' in html
    assert "Next in this path" in html
    assert 'href="m3.html">Simulation-calibrated drawdown alarms</a>' in html
