import json
import re
import shutil
import subprocess
from html.parser import HTMLParser

import yaml
import pytest

from pathlib import Path

from quant_allocator.site.build import build

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
        self.exclusion_stack: list[str] = []
        self.text_nodes: list[str] = []

    def handle_starttag(self, tag, attrs):
        classes = dict(attrs).get("class", "").split()
        starts_exclusion = tag in {"pre", "code"} or "escaped-dollar" in classes
        if starts_exclusion:
            self.exclusion_stack.append(tag)
            self.excluded_depth += 1

    def handle_endtag(self, tag):
        if self.exclusion_stack and self.exclusion_stack[-1] == tag:
            self.exclusion_stack.pop()
            self.excluded_depth -= 1

    def handle_data(self, data):
        if not self.excluded_depth:
            self.text_nodes.append(data)


def _test_preceding_backslashes(text: str, index: int) -> int:
    count = 0
    while index > count and text[index - count - 1] == "\\":
        count += 1
    return count


def _scan_math_text(
    text: str, *, opening_uses_parity: bool = True
) -> tuple[list[str], list[int]]:
    """Return recognized expressions and active dollar signs outside any valid range."""
    expressions = []
    covered_dollars: set[int] = set()
    index = 0
    while index < len(text):
        escaped_opening = opening_uses_parity and _test_preceding_backslashes(text, index) % 2
        if text[index] != "$" or escaped_opening:
            index += 1
            continue
        delimiter = "$$" if text.startswith("$$", index) else "$"
        if delimiter == "$" and index > 0 and text[index - 1] == "$":
            index += 1
            continue
        content_start = index + len(delimiter)
        close = content_start
        while close < len(text):
            if delimiter == "$" and text[close] == "\n":
                close = -1
                break
            if (
                text.startswith(delimiter, close)
                and _test_preceding_backslashes(text, close) % 2 == 0
            ):
                if delimiter == "$" and close + 1 < len(text) and text[close + 1] == "$":
                    close += 1
                    continue
                break
            close += 1
        if close < 0 or close >= len(text):
            index = content_start
            continue
        expressions.append(text[content_start:close])
        covered_dollars.update(
            offset
            for offset in range(index, close + len(delimiter))
            if text[offset] == "$"
        )
        index = close + len(delimiter)
    active_dollars = {
        offset
        for offset, character in enumerate(text)
        if character == "$"
        and (
            not opening_uses_parity
            or _test_preceding_backslashes(text, offset) % 2 == 0
        )
    }
    return expressions, sorted(active_dollars - covered_dollars)


def _expressions_in_text(text: str, *, opening_uses_parity: bool = True) -> list[str]:
    """Independent delimiter scanner; intentionally does not reuse the production regex."""
    return _scan_math_text(text, opening_uses_parity=opening_uses_parity)[0]


def _assert_balanced_math_text(
    text: str,
    *,
    spec_id: str,
    location: str,
    opening_uses_parity: bool = True,
) -> None:
    _, unmatched = _scan_math_text(text, opening_uses_parity=opening_uses_parity)
    if not unmatched:
        return
    offset = unmatched[0]
    line = text.count("\n", 0, offset) + 1
    line_start = text.rfind("\n", 0, offset) + 1
    line_end = text.find("\n", offset)
    if line_end < 0:
        line_end = len(text)
    column = offset - line_start + 1
    excerpt = text[line_start:line_end].strip()
    raise AssertionError(
        f"{spec_id}: unmatched math delimiter at {location}, line {line}, "
        f"column {column}: {excerpt!r}"
    )


def _math_expressions(rendered_body: str) -> list[str]:
    collector = _MathTextCollector()
    collector.feed(rendered_body)
    return [
        expression
        for text in collector.text_nodes
        for expression in _expressions_in_text(text, opening_uses_parity=False)
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


def _katex_result(expression_rows: list[dict]) -> subprocess.CompletedProcess:
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
    return subprocess.run(
        ["node", "-e", script, str(katex_path)],
        input=json.dumps(expression_rows),
        text=True,
        capture_output=True,
        check=False,
    )


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
        r"Inline $x_i + \texttt{min\_tier} + \# + \{a\} + escaped\_name + \$$ and "
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
    inline_expression = r"x_i + \texttt{min\_tier} + \# + \{a\} + escaped\_name + \$"
    assert f"${inline_expression}$" in rendered
    assert "<em>outside emphasis</em>" in rendered
    assert "<code>$not_math$</code>" in rendered
    assert "$fenced_not_math$" in rendered
    assert 'escaped currency: <span class="escaped-dollar">$</span>25' in rendered
    assert _math_expressions(body) == [
        inline_expression,
        "\n" + r"w_i = \frac{\alpha_i}{\sigma_i^2}" + "\n",
    ]
    result = _katex_result(
        [{"spec": "t1", "index": 1, "expression": inline_expression}]
    )
    assert result.returncode == 0, result.stderr


def test_math_delimiters_use_even_odd_backslash_parity(tmp_path):
    site = _fixture_site(tmp_path)
    spec = tmp_path / "docs" / "ideas" / "specs" / "t1.md"
    source = (
        "# Parity\n\n"
        r"Even opening \\$x_i$; even inline close $y_i\\$."
        "\n\n"
        r"Even display opening \\$$z_i\\$$."
    )
    spec.write_text(source, encoding="utf-8")

    build(site, tmp_path / "out")

    body = _rendered_spec_bodies(tmp_path / "out")["t1"]
    active = ["x_i", r"y_i\\", r"z_i\\"]
    assert _source_math_expressions(source) == active
    assert _math_expressions(body) == active
    assert r"Even opening \$x_i$" in body
    assert r"Even display opening \$$z_i\\$$" in body
    result = _katex_result(
        [
            {"spec": "t1", "index": index, "expression": expression}
            for index, expression in enumerate(active, start=1)
        ]
    )
    assert result.returncode == 0, result.stderr

    escaped_source = (
        "# Escaped parity\n\n"
        r"Odd inline opening and close: \$not_math\$."
        "\n\n"
        r"Odd display-token opening and close: \$$not_display\$$."
        "\n\n"
        r"Three-slash inline tokens: \\\$not_math_three\\\$."
        "\n\n"
        r"Three-slash display tokens: \\\$$not_display_three\\\$$."
    )
    spec.write_text(escaped_source, encoding="utf-8")
    build(site, tmp_path / "escaped-out")
    escaped_body = _rendered_spec_bodies(tmp_path / "escaped-out")["t1"]
    assert _source_math_expressions(escaped_source) == []
    assert _math_expressions(escaped_body) == []
    assert escaped_body.count('class="escaped-dollar"') == 8
    assert escaped_body.count('<span class="escaped-dollar">$$</span>') == 2
    assert escaped_body.count('<span class="escaped-dollar">\\$</span>') == 2
    assert escaped_body.count('<span class="escaped-dollar">\\$$</span>') == 2


def test_unmatched_even_run_openers_survive_as_raw_and_keep_error_default(tmp_path):
    site = _fixture_site(tmp_path)
    spec = tmp_path / "docs" / "ideas" / "specs" / "t1.md"
    spec.write_text(
        "# Unmatched\n\n" + r"Even inline \\$unclosed." + "\n\n" + r"Even display \\$$unclosed.",
        encoding="utf-8",
    )

    build(site, tmp_path / "out")

    rendered = (tmp_path / "out" / "specs" / "t1.html").read_text(encoding="utf-8")
    body = _rendered_spec_bodies(tmp_path / "out")["t1"]
    assert 'data-math-render-status="error"' in rendered
    assert r"Even inline \$unclosed" in body
    assert r"Even display \$$unclosed" in body
    assert 'class="escaped-dollar"' not in body


def test_balanced_math_audit_handles_currency_and_multiline_fixtures(tmp_path):
    site = _fixture_site(tmp_path)
    spec = tmp_path / "docs" / "ideas" / "specs" / "t1.md"
    spec.write_text(
        "# Currency and display math\n\n"
        r"Coverage exceeds \$1trn; the comparison portfolio is ~\$570m."
        "\n\n$$\n"
        r"x_i = \alpha_i + \varepsilon_i"
        "\n$$\n",
        encoding="utf-8",
    )
    build(site, tmp_path / "out")

    body = _rendered_spec_bodies(tmp_path / "out")["t1"]
    collector = _MathTextCollector()
    collector.feed(body)
    assert body.count('class="escaped-dollar"') == 2
    for node_index, text in enumerate(collector.text_nodes, start=1):
        _assert_balanced_math_text(
            text,
            spec_id="t1",
            location=f"rendered text node {node_index}",
            opening_uses_parity=False,
        )

    with pytest.raises(
        AssertionError,
        match=r"t1: unmatched math delimiter at source fixture, line 1, column 8",
    ):
        _assert_balanced_math_text(
            "broken $x_i\n+ y_i$",
            spec_id="t1",
            location="source fixture",
        )


def test_all_live_specs_have_no_unmatched_math_dollars_before_javascript(tmp_path):
    build(REPO_ROOT / "site", tmp_path / "out")
    for spec_id, body in _rendered_spec_bodies(tmp_path / "out").items():
        collector = _MathTextCollector()
        collector.feed(body)
        for node_index, text in enumerate(collector.text_nodes, start=1):
            _assert_balanced_math_text(
                text,
                spec_id=spec_id,
                location=f"rendered text node {node_index}",
                opening_uses_parity=False,
            )


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

    result = _katex_result(expression_rows)
    assert result.returncode == 0, result.stderr


def test_reviewed_live_specs_do_not_claim_pending_method_review(tmp_path):
    build(REPO_ROOT / "site", tmp_path / "out")
    for spec_id in ("m1", "m2", "e2"):
        rendered = (tmp_path / "out" / "specs" / f"{spec_id}.html").read_text(encoding="utf-8")
        assert "pending method review" not in rendered.lower()


def test_spec_template_math_status_behaves_for_success_and_failure():
    template = (REPO_ROOT / "site" / "templates" / "spec.html.j2").read_text(encoding="utf-8")
    inline_script = re.findall(r"<script>\s*(.*?)\s*</script>", template, re.DOTALL)
    assert len(inline_script) == 1
    harness = r"""
const fs = require("fs"), vm = require("vm");
const source = JSON.parse(fs.readFileSync(0, "utf8"));
function text(value) {
  return {nodeType: 3, nodeValue: value, childNodes: []};
}
function element(tag, classes, children) {
  return {
    nodeType: 1, tag, classes, childNodes: children || [], attrs: {},
    matches(selector) {
      return selector.split(",").some(part => {
        part = part.trim();
        return part[0] === "." ? this.classes.includes(part.slice(1)) : this.tag === part;
      });
    },
    setAttribute(k, v) { this.attrs[k] = v; }
  };
}
function run(mode) {
  let callback, thrown = null, renderedTarget = null;
  const consoleErrors = [];
  const body = element("div", [], [text("$x_i$")]);
  body.attrs["data-math-render-status"] = "error";
  const outside = {attrs: {"data-math-render-status": "untouched"}};
  const context = {
    window: {addEventListener(name, fn) { if (name === "DOMContentLoaded") callback = fn; }},
    document: {querySelector(selector) {
      if (selector !== ".spec-page__body") throw new Error("renderer escaped spec body");
      return body;
    }},
    console: {error(message) { consoleErrors.push(String(message)); }},
    renderMathInElement(target, options) {
      renderedTarget = target;
      if (mode === "invalid") {
        options.errorCallback("deliberate parse failure", new Error("bad TeX"));
      } else if (mode === "rawInline") {
        target.childNodes = [text("\\$unclosed")];
      } else if (mode === "rawDisplay") {
        target.childNodes = [text("\\$$unclosed")];
      } else if (mode === "escaped") {
        target.childNodes = [element("span", ["escaped-dollar"], [text("$$")])];
      } else {
        target.childNodes = [element("span", ["katex"], [text("rendered x_i")])];
      }
    }
  };
  vm.runInNewContext(source, context);
  try { callback(); } catch (error) { thrown = error; }
  return {body, outside, thrown, renderedTarget, consoleErrors};
}
const valid = run("valid"), invalid = run("invalid");
const rawInline = run("rawInline"), rawDisplay = run("rawDisplay"), escaped = run("escaped");
const checks = [
  valid.renderedTarget === valid.body,
  valid.body.attrs["data-math-render-status"] === "ok",
  valid.consoleErrors.length === 0,
  valid.thrown === null,
  invalid.renderedTarget === invalid.body,
  invalid.body.attrs["data-math-render-status"] === "error",
  invalid.consoleErrors.length >= 1,
  invalid.thrown && invalid.thrown.message.includes("Spec math rendering failed"),
  invalid.outside.attrs["data-math-render-status"] === "untouched",
  rawInline.renderedTarget === rawInline.body,
  rawInline.body.attrs["data-math-render-status"] === "error",
  rawInline.consoleErrors.length === 1,
  rawInline.thrown && rawInline.thrown.message.includes("active raw delimiter"),
  rawInline.outside.attrs["data-math-render-status"] === "untouched",
  rawDisplay.renderedTarget === rawDisplay.body,
  rawDisplay.body.attrs["data-math-render-status"] === "error",
  rawDisplay.consoleErrors.length === 1,
  rawDisplay.thrown && rawDisplay.thrown.message.includes("active raw delimiter"),
  rawDisplay.outside.attrs["data-math-render-status"] === "untouched",
  escaped.body.attrs["data-math-render-status"] === "ok",
  escaped.consoleErrors.length === 0,
  escaped.thrown === null
];
if (checks.some(value => !value)) { console.error(checks); process.exit(1); }
"""
    result = subprocess.run(
        ["node", "-e", harness],
        input=json.dumps(inline_script[0]),
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
