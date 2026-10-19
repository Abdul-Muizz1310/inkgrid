"""Spec 03 section 4, case K7: the uv constraints admit Dependabot's uv and the release pin."""

import re
import tomllib
from pathlib import Path

from packaging.requirements import Requirement
from packaging.specifiers import SpecifierSet

ROOT = Path(__file__).resolve().parents[1]
DEPENDABOT_UV = "0.12.18"
RELEASE_WORKFLOW = ROOT / ".github" / "workflows" / "release.yml"


def pyproject() -> dict[str, object]:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        return tomllib.load(handle)


def required_version() -> SpecifierSet:
    tool = pyproject()["tool"]
    assert isinstance(tool, dict)
    return SpecifierSet(tool["uv"]["required-version"])


def build_backend() -> SpecifierSet:
    build = pyproject()["build-system"]
    assert isinstance(build, dict)
    (requirement,) = [Requirement(r) for r in build["requires"]]
    assert requirement.name in {"uv-build", "uv_build"}
    return requirement.specifier


def release_pin() -> str:
    pins = set(re.findall(r'version: "(\d+\.\d+\.\d+)"', RELEASE_WORKFLOW.read_text()))
    (pin,) = pins
    return pin


def test_K7_required_version_admits_dependabots_uv() -> None:
    assert required_version().contains(DEPENDABOT_UV)


def test_K7_build_backend_admits_dependabots_uv() -> None:
    assert build_backend().contains(DEPENDABOT_UV)


def test_K7_both_admit_the_release_workflows_pinned_uv() -> None:
    pin = release_pin()
    assert required_version().contains(pin)
    assert build_backend().contains(pin)


def test_K7_required_version_stays_inside_one_minor() -> None:
    # setup-uv installs the newest uv inside required-version: a new minor is a deliberate bump.
    assert not required_version().contains("0.13.0")
