import os
import subprocess
import sys

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(args, **kwargs):
    env = {**os.environ, "PYTHONPATH": "src"}
    return subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        **kwargs,
    )


def test_cli_build_smoke(tmp_path):
    out = tmp_path / "out"
    result = _run(["-m", "quant_allocator.site", "build", "--out", str(out)])
    assert result.returncode == 0, result.stderr
    assert (out / "index.html").exists()
    assert (out / "e1.html").exists()
    assert (out / "specs" / "e1.html").exists()


def test_site_build_import_isolation():
    result = _run(
        [
            "-c",
            "import quant_allocator.site.build, sys; "
            "sys.exit(0 if ('numpy' not in sys.modules and 'pandas' not in sys.modules) else 1)",
        ]
    )
    assert result.returncode == 0, result.stderr
