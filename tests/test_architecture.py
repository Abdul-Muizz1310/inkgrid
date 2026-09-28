"""The layer table of docs/specs/03-cli-and-packaging.md section 3, enforced on the import graph."""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "src" / "inkgrid"

INTERNAL: dict[str, set[str]] = {
    "model": set(),
    "core": {"model"},
    "read": {"model"},
    "verify": {"model"},
    "render": {"model", "read"},
    "api": {"model", "core", "read", "verify"},
    "cli": {"api", "render", "model"},
    "__init__": {"api", "model"},
    "__main__": {"cli"},
    "errors": set(),
}
THIRD_PARTY: dict[str, set[str]] = {
    "model": {"pydantic", "pydantic_core"},
    "read": {"pymupdf", "camelot"},
    "verify": {"pypdfium2"},
}
# Inside read/, only the adapter modules may import their library.
ADAPTER = {
    "pymupdf": "read/pymupdf_reader.py",
    "camelot": "read/camelot_reader.py",
    "pypdfium2": "verify/pdfium_reader.py",
}
STDLIB = set(sys.stdlib_module_names) | {"__future__"}


def _layer(relative: Path) -> str:
    return relative.parts[0] if len(relative.parts) > 1 else relative.stem


def _targets(tree: ast.AST) -> list[str]:
    out: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            if node.module == "inkgrid":
                out.extend(f"inkgrid.{alias.name}" for alias in node.names)
            else:
                out.append(node.module)
    return out


def violations(root: Path) -> list[str]:
    """Every import in the package tree at `root` that breaks the layer table."""
    found: list[str] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        layer = _layer(relative)
        for target in _targets(ast.parse(path.read_text(encoding="utf-8"))):
            top = target.split(".")[0]
            if top in STDLIB:
                continue
            if top == "inkgrid":
                parts = target.split(".")
                other = parts[1] if len(parts) > 1 else "__init__"
                if other in {layer, "errors"} or other in INTERNAL.get(layer, set()):
                    continue
                found.append(f"{relative.as_posix()}: imports {target}")
                continue
            if top not in THIRD_PARTY.get(layer, set()):
                found.append(f"{relative.as_posix()}: imports third-party {target}")
            elif top in ADAPTER and relative.as_posix() != ADAPTER[top]:
                found.append(f"{relative.as_posix()}: only {ADAPTER[top]} may import {top}")
    return found


def write(root: Path, relative: str, source: str) -> None:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


def test_T1_real_tree_follows_the_layer_table() -> None:
    assert violations(PACKAGE) == []


def test_T2_model_may_not_import_core(tmp_path: Path) -> None:
    write(tmp_path, "model/x.py", "import inkgrid.core\n")
    assert violations(tmp_path) == ["model/x.py: imports inkgrid.core"]


def test_T3_verify_may_not_import_core(tmp_path: Path) -> None:
    write(tmp_path, "verify/x.py", "from inkgrid.core.lines import group\n")
    assert violations(tmp_path) == ["verify/x.py: imports inkgrid.core.lines"]


def test_T4_only_the_adapter_imports_pymupdf(tmp_path: Path) -> None:
    write(tmp_path, "read/words.py", "import pymupdf\n")
    write(tmp_path, "read/pymupdf_reader.py", "import pymupdf\n")
    assert violations(tmp_path) == ["read/words.py: only read/pymupdf_reader.py may import pymupdf"]


def test_AP4_only_the_adapter_imports_camelot(tmp_path: Path) -> None:
    write(tmp_path, "read/words.py", "import camelot\n")
    write(tmp_path, "read/camelot_reader.py", "import camelot\n")
    assert violations(tmp_path) == ["read/words.py: only read/camelot_reader.py may import camelot"]


def test_VR0_only_the_verifier_adapter_imports_pypdfium2(tmp_path: Path) -> None:
    write(tmp_path, "verify/checks.py", "import pypdfium2.raw\n")
    write(tmp_path, "verify/pdfium_reader.py", "import pypdfium2\n")
    assert violations(tmp_path) == [
        "verify/checks.py: only verify/pdfium_reader.py may import pypdfium2"
    ]


def test_T5_core_may_not_import_third_party(tmp_path: Path) -> None:
    write(tmp_path, "core/x.py", "import numpy as np\n")
    assert violations(tmp_path) == ["core/x.py: imports third-party numpy"]


def test_stdlib_errors_and_same_layer_imports_are_allowed(tmp_path: Path) -> None:
    write(
        tmp_path,
        "core/x.py",
        "import re\nfrom inkgrid.errors import InvariantError\nfrom inkgrid.core import y\n",
    )
    assert violations(tmp_path) == []


def test_sources_are_ascii() -> None:
    offenders = [
        path.relative_to(ROOT).as_posix()
        for folder in ("src", "tests", "scripts", "typings", "bench")
        for path in sorted((ROOT / folder).rglob("*.py*"))
        if path.suffix in {".py", ".pyi"} and not path.read_bytes().isascii()
    ]
    assert offenders == [], "use escape sequences for non-ASCII characters"
