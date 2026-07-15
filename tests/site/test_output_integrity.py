from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

from quant_allocator.site.build import build


REPO_ROOT = Path(__file__).resolve().parents[2]
EXTERNAL_SCHEMES = {"http", "https", "mailto", "tel"}


class _DocumentLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids: list[str] = []
        self.references: list[str] = []

    def handle_starttag(self, _tag, attrs):
        attributes = dict(attrs)
        if attributes.get("id"):
            self.ids.append(attributes["id"])
        for name in ("href", "src"):
            if attributes.get(name):
                self.references.append(attributes[name])


def _parse(path: Path) -> _DocumentLinks:
    parser = _DocumentLinks()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def test_every_generated_page_has_unique_ids_and_resolving_local_links(tmp_path):
    out = tmp_path / "out"
    build(REPO_ROOT / "site", out)
    pages = sorted(out.glob("*.html")) + sorted((out / "specs").glob("*.html"))
    parsed = {page.resolve(): _parse(page) for page in pages}

    assert len(pages) == 47
    for page, document in parsed.items():
        assert len(document.ids) == len(set(document.ids)), page.relative_to(out)
        source = page.read_text(encoding="utf-8")
        assert "/Users/" not in source
        assert "/private/" not in source

        for reference in document.references:
            split = urlsplit(reference)
            if split.scheme in EXTERNAL_SCHEMES or split.netloc:
                continue
            target = page if not split.path else (page.parent / unquote(split.path)).resolve()
            assert out.resolve() in (target, *target.parents), (page, reference)
            assert target.is_file(), (page.relative_to(out), reference)
            if split.fragment:
                target_document = parsed.get(target)
                assert target_document is not None, (page.relative_to(out), reference)
                assert target_document.ids.count(unquote(split.fragment)) == 1, (
                    page.relative_to(out),
                    reference,
                )
