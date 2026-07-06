from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pages_workflow_is_valid_yaml():
    workflow = yaml.safe_load(
        (REPO_ROOT / ".github" / "workflows" / "pages.yml").read_text(encoding="utf-8")
    )
    assert "jobs" in workflow
    assert workflow["jobs"]["build-and-deploy"]["runs-on"] == "ubuntu-latest"


def test_readme_states_thesis_and_data_policy():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    assert "inference under partial transparency" in readme
    assert "All data on this site is synthetic or public." in readme


def test_license_is_mit():
    assert "MIT License" in (REPO_ROOT / "LICENSE").read_text(encoding="utf-8")
