import json
import re
import shutil
import subprocess
from html.parser import HTMLParser

import yaml

from pathlib import Path

from quant_allocator.site.build import build

MATH_PAIR_RE = re.compile(
    r"(?<!\\)\$\$(?P<display>.+?)(?<!\\)\$\$"
    r"|(?<![\\$])\$(?!\$)(?P<inline>[^\n]+?)(?<![\\$])\$(?!\$)",
    re.DOTALL,
)
FENCED_CODE_RE = re.compile(r"^```.*?^```[ \t]*$", re.MULTILINE | re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`]*`")
SPEC_BODY_RE = re.compile(
    r'<div class="spec-page__body"[^>]*>(?P<body>.*?)\n  </div>\n</article>',
    re.DOTALL,
)


class _MathTextCollector(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.excluded_depth = 0
        self.text_nodes: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag in {"pre", "code"}:
            self.excluded_depth += 1

    def handle_endtag(self, tag):
        if tag in {"pre", "code"}:
            self.excluded_depth -= 1

    def handle_data(self, data):
        if not self.excluded_depth:
            self.text_nodes.append(data)


def _expressions_in_text(text: str) -> list[str]:
    return [
        match.group("display") if match.group("display") is not None else match.group("inline")
        for match in MATH_PAIR_RE.finditer(text)
    ]


def _math_expressions(rendered_body: str) -> list[str]:
    collector = _MathTextCollector()
    collector.feed(rendered_body)
    return [
        expression for text in collector.text_nodes for expression in _expressions_in_text(text)
    ]


def _source_math_expressions(source: str) -> list[str]:
    without_code = INLINE_CODE_RE.sub("", FENCED_CODE_RE.sub("", source))
    return _expressions_in_text(without_code)


def _rendered_spec_bodies(out_dir: Path) -> dict[str, str]:
    bodies = {}
    for path in sorted((out_dir / "specs").glob("*.html")):
        rendered = path.read_text(encoding="utf-8")
        match = SPEC_BODY_RE.search(rendered)
        assert match, f"missing spec body in {path}"
        bodies[path.stem] = match.group("body")
    return bodies


REPO_ROOT = Path(__file__).resolve().parents[2]


def _fixture_site(tmp_path):
    site = tmp_path / "site"
    shutil.copytree(REPO_ROOT / "site" / "templates", site / "templates")
    shutil.copytree(REPO_ROOT / "site" / "assets", site / "assets")
    (site / "templates" / "pages").mkdir(exist_ok=True)
    (site / "templates" / "pages" / "t1.html.j2").write_text(
        "{% extends 'demo.html.j2' %}", encoding="utf-8"
    )
    (site / "data").mkdir()
    (site / "data" / "t1.json").write_text("{}", encoding="utf-8")
    specs = tmp_path / "docs" / "ideas" / "specs"
    specs.mkdir(parents=True)
    (specs / "t1.md").write_text(
        "# Spec\n\nInline math $\\alpha$ here.\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n",
        encoding="utf-8",
    )
    (site / "cards.yaml").write_text(
        yaml.safe_dump(
            [
                {
                    "id": "t1",
                    "title": "Test card",
                    "lane": "S",
                    "one_liner": "x",
                    "decisions": ["select"],
                    "tiers": ["R"],
                    "status": "live",
                    "demo": "pages/t1.html.j2",
                    "data": "t1.json",
                    "spec": "t1.md",
                    "golive": {"data_ask": "R", "sample": "36m", "effort": "S"},
                }
            ]
        ),
        encoding="utf-8",
    )
    return site


def test_spec_renders_math_untouched_and_table(tmp_path):
    site = _fixture_site(tmp_path)
    build(site, tmp_path / "out")
    html = (tmp_path / "out" / "specs" / "t1.html").read_text(encoding="utf-8")
    assert r"$\alpha$" in html
    assert "<table>" in html


def test_spec_markdown_protects_tex_before_inline_formatting(tmp_path):
    site = _fixture_site(tmp_path)
    spec = tmp_path / "docs" / "ideas" / "specs" / "t1.md"
    spec.write_text(
        "# Spec\n\n"
        r"Inline $x_i + \texttt{min_tier} + \# + \{a\} + escaped\_name$ and "
        "*outside emphasis*.\n\n"
        "$$\n"
        r"w_i = \frac{\alpha_i}{\sigma_i^2}"
        "\n$$\n\n"
        r"Inline code: `$not_math$`; escaped currency: \$25."
        "\n\n```text\n$fenced_not_math$\n```\n",
        encoding="utf-8",
    )

    build(site, tmp_path / "out")

    rendered = (tmp_path / "out" / "specs" / "t1.html").read_text(encoding="utf-8")
    body = _rendered_spec_bodies(tmp_path / "out")["t1"]
    assert r"$x_i + \texttt{min_tier} + \# + \{a\} + escaped\_name$" in rendered
    assert "<em>outside emphasis</em>" in rendered
    assert "<code>$not_math$</code>" in rendered
    assert "$fenced_not_math$" in rendered
    assert 'escaped currency: <span class="escaped-dollar">$</span>25' in rendered
    assert _math_expressions(body) == [
        r"x_i + \texttt{min_tier} + \# + \{a\} + escaped\_name",
        "\n" + r"w_i = \frac{\alpha_i}{\sigma_i^2}" + "\n",
    ]


def test_all_live_specs_have_contiguous_balanced_katex_parseable_math(tmp_path):
    build(REPO_ROOT / "site", tmp_path / "out")
    bodies = _rendered_spec_bodies(tmp_path / "out")
    assert len(bodies) == 20

    expression_rows = [
        {"spec": spec_id, "index": index, "expression": expression}
        for spec_id, body in bodies.items()
        for index, expression in enumerate(_math_expressions(body), start=1)
    ]
    assert expression_rows, "the live spec corpus unexpectedly contains no math"
    cards = yaml.safe_load((REPO_ROOT / "site" / "cards.yaml").read_text(encoding="utf-8"))
    for card in cards:
        source = (REPO_ROOT / "docs" / "ideas" / "specs" / card["spec"]).read_text(encoding="utf-8")
        expected_count = len(_source_math_expressions(source))
        actual_count = sum(row["spec"] == card["id"] for row in expression_rows)
        assert actual_count == expected_count, (
            f"{card['id']}: rendered {actual_count} of {expected_count} source expressions; "
            "a Markdown tag may have split a math range"
        )

    katex_path = REPO_ROOT / "site" / "assets" / "katex" / "katex.min.js"
    script = r"""
const fs = require("fs");
const katex = require(process.argv[1]);
const rows = JSON.parse(fs.readFileSync(0, "utf8"));
const failures = [];
for (const row of rows) {
  try {
    katex.renderToString(row.expression, {throwOnError: true, strict: "ignore"});
  } catch (error) {
    failures.push(`${row.spec} expression ${row.index}: ${error.message}`);
  }
}
if (failures.length) {
  process.stderr.write(failures.join("\n"));
  process.exit(1);
}
"""
    result = subprocess.run(
        ["node", "-e", script, str(katex_path)],
        input=json.dumps(expression_rows),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_reviewed_live_specs_do_not_claim_pending_method_review(tmp_path):
    build(REPO_ROOT / "site", tmp_path / "out")
    for spec_id in ("m1", "m2", "e2"):
        rendered = (tmp_path / "out" / "specs" / f"{spec_id}.html").read_text(encoding="utf-8")
        assert "pending method review" not in rendered.lower()


def test_spec_template_marks_math_render_status_and_scopes_renderer():
    template = (REPO_ROOT / "site" / "templates" / "spec.html.j2").read_text(encoding="utf-8")
    assert 'data-math-render-status="error"' in template
    assert 'querySelector(".spec-page__body")' in template
    assert 'setAttribute("data-math-render-status", "ok")' in template
    assert 'setAttribute("data-math-render-status", "error")' in template
    assert "mathErrors.push" in template
