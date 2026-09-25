"""Checks on the built wheel and sdist. Slow: builds with uv, then installs into a fresh env."""

import email.parser
import shutil
import subprocess
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def dist(tmp_path_factory: pytest.TempPathFactory) -> Path:
    uv = shutil.which("uv")
    assert uv is not None, "uv is required to build distributions"
    out = tmp_path_factory.mktemp("dist")
    subprocess.run(
        [uv, "build", "--no-sources", "--out-dir", str(out)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=300,
    )
    return out


def wheel(dist: Path) -> Path:
    (found,) = dist.glob("inkgrid-*.whl")
    return found


def test_K1_wheel_contains_py_typed(dist: Path) -> None:
    names = zipfile.ZipFile(wheel(dist)).namelist()
    assert "inkgrid/py.typed" in names
    assert not any(name.startswith(("tests/", "typings/")) for name in names)


def test_K2_wheel_metadata(dist: Path) -> None:
    with zipfile.ZipFile(wheel(dist)) as archive:
        (meta_name,) = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
        meta = email.parser.Parser().parsestr(archive.read(meta_name).decode("utf-8"))
    assert meta["License-Expression"] == "MIT"
    assert not [c for c in meta.get_all("Classifier", []) if c.startswith("License ::")]
    assert meta["Requires-Python"] == ">=3.12"
    assert "pymupdf>=1.28.2,<2" in meta.get_all("Requires-Dist", [])


@pytest.mark.parametrize("kind", ["wheel", "sdist"])
def test_K3_smoke_test_passes_in_an_isolated_env(dist: Path, kind: str) -> None:
    uv = shutil.which("uv")
    assert uv is not None
    artifact = wheel(dist) if kind == "wheel" else next(dist.glob("inkgrid-*.tar.gz"))
    done = subprocess.run(
        [
            uv,
            "run",
            "--isolated",
            "--no-project",
            "--with",
            str(artifact),
            str(ROOT / "tests" / "smoke_test.py"),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=600,
    )
    assert done.returncode == 0, done.stderr
    assert "smoke test passed" in done.stdout
