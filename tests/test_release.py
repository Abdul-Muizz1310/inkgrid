import importlib.util
import re
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_release.py"
WORKFLOWS = ROOT / ".github" / "workflows"
LINK = "[0.1.0]: https://github.com/Abdul-Muizz1310/inkgrid/releases/tag/v0.1.0"
CHANGELOG = f"""# Changelog

Notes.

## [Unreleased]

## [0.1.0] - 2026-10-02

### Added

- Everything.

[Unreleased]: https://github.com/Abdul-Muizz1310/inkgrid/compare/v0.1.0...HEAD
{LINK}
"""
README = "# inkgrid\n\n## Quick start\n\n```bash\npip install inkgrid\n```\n"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_release", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def problems(
    tag: str = "v0.1.0",
    *,
    version: str = "0.1.0",
    changelog: str = CHANGELOG,
    readme: str = README,
) -> list[str]:
    found: list[str] = load_script().problems(
        tag, version=version, changelog=changelog, readme=readme
    )
    return found


def test_RL1_a_final_tag_matching_its_version_and_changelog_passes() -> None:
    assert problems() == []


@pytest.mark.parametrize(
    "tag", ["0.1.0", "v0.1", "v0.1.0rc1", "v0.1.0.dev0", "v0.1.0.post1", "v0.1.0+local", "v0.1.0 "]
)
def test_RL2_only_a_final_version_tag_publishes(tag: str) -> None:
    (problem,) = problems(tag)
    assert "not a final version tag" in problem


def test_RL3_the_tag_must_be_the_projects_version() -> None:
    (problem,) = problems("v0.1.1")
    assert "0.1.1" in problem
    assert "0.1.0" in problem
    assert any("0.1.0.dev0" in p for p in problems(version="0.1.0.dev0"))


@pytest.mark.parametrize(
    ("changelog", "named"),
    [
        (CHANGELOG.replace("## [0.1.0] - 2026-10-02", "## [0.0.9] - 2026-10-02"), "no section"),
        (CHANGELOG.replace("2026-10-02", "2026-02-30"), "no section"),
        (CHANGELOG.replace("## [0.1.0] - 2026-10-02", "## [0.1.0]"), "no section"),
        (CHANGELOG.replace(LINK, ""), "link"),
        (CHANGELOG.replace("## [Unreleased]\n", "## [Unreleased]\n\n- A change.\n"), "Unreleased"),
    ],
)
def test_RL4_the_changelog_must_date_and_link_the_release(changelog: str, named: str) -> None:
    (problem,) = problems(changelog=changelog)
    assert named in problem


@pytest.mark.parametrize(
    "readme",
    [
        README + "\ninkgrid is not on PyPI yet. From a clone:\n",
        README.replace("pip install inkgrid", "uv sync --all-groups"),
    ],
)
def test_RL5_the_readme_must_install_from_pypi(readme: str) -> None:
    (problem,) = problems(readme=readme)
    assert "README" in problem


def write_root(root: Path, *, version: str) -> Path:
    root.mkdir()
    (root / "pyproject.toml").write_text(f'[project]\nname = "inkgrid"\nversion = "{version}"\n')
    (root / "CHANGELOG.md").write_text(CHANGELOG)
    (root / "README.md").write_text(README)
    return root


def test_RL6_the_command_prints_every_problem_and_exits_1(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    script = load_script()
    good = write_root(tmp_path / "good", version="0.1.0")
    assert script.main(["v0.1.0"], root=good) == 0
    bad = write_root(tmp_path / "bad", version="0.1.0.dev0")
    assert script.main(["v0.2"], root=bad) == 1
    err = capsys.readouterr().err
    assert "not a final version tag" in err
    assert "0.1.0.dev0" in err
    assert script.main([], root=good) == 2


def jobs(text: str) -> dict[str, str]:
    """Each job's lines, by its id: the two-space keys under `jobs:`."""
    body = text.split("\njobs:\n", 1)[1]
    parts = re.split(r"^  ([a-z][a-z0-9-]*):\n", body, flags=re.MULTILINE)
    return dict(zip(parts[1::2], parts[2::2], strict=True))


def test_RL7_a_tag_builds_once_then_publishes_to_testpypi_then_pypi() -> None:
    text = (WORKFLOWS / "release.yml").read_text(encoding="utf-8")
    assert re.search(r"^on:\n  push:\n    tags: \[\"v\*\"\]\n\n", text, flags=re.MULTILINE)
    assert "pull_request" not in text
    assert "workflow_dispatch" not in text
    assert re.search(r"^permissions: \{\}$", text, flags=re.MULTILINE)
    assert "secrets." not in text
    assert "password" not in text
    by_id = jobs(text)
    assert list(by_id) == ["build", "publish-testpypi", "publish-pypi"]
    build, testpypi, pypi = by_id["build"], by_id["publish-testpypi"], by_id["publish-pypi"]
    assert "id-token" not in build
    assert "contents: read" in build
    assert "persist-credentials: false" in build
    assert 'TAG: "${{ github.ref_name }}"' in build
    assert 'python scripts/check_release.py "$TAG"' in build
    assert "uv run pytest\n" in build
    assert "uv run pytest -m slow --no-cov" in build
    assert "uv build --no-sources" in build
    assert "needs: build" in testpypi
    assert "needs: publish-testpypi" in pypi
    for job, env in ((testpypi, "testpypi"), (pypi, "pypi")):
        assert re.search(rf"environment:\n      name: {env}\n", job)
        assert "id-token: write" in job
        assert "attestations: true" in job
        assert "actions/checkout" not in job
        assert "run:" not in job
    assert "repository-url: https://test.pypi.org/legacy/" in testpypi
    assert "skip-existing: true" in testpypi
    assert "repository-url" not in pypi
    assert "skip-existing" not in pypi
    assert text.count("id-token: write") == 2


def test_RL8_every_action_is_pinned_to_a_commit() -> None:
    files = sorted(WORKFLOWS.glob("*.yml"))
    assert {f.name for f in files} >= {"ci.yml", "release.yml"}
    for f in files:
        uses = re.findall(r"uses: (\S+)(.*)", f.read_text(encoding="utf-8"))
        assert uses, f.name
        for action, rest in uses:
            assert re.fullmatch(r"[\w.-]+/[\w./-]+@[0-9a-f]{40}", action), (f.name, action)
            assert re.fullmatch(r" # v\d+(\.\d+)*", rest), (f.name, action, rest)
