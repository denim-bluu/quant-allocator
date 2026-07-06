import subprocess

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_publication_check_runs_and_reports():
    result = subprocess.run(
        ["bash", "tools/publication_check.sh"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "Publication readiness scan" in result.stdout
    assert "Scan complete." in result.stdout
