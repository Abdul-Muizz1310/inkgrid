import importlib.util
import json
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "check_coverage_floors.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_coverage_floors", SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_report(path: Path, pct: float, *, branch: bool = True) -> Path:
    report = {
        "meta": {"branch_coverage": branch},
        "files": {"src/inkgrid/x.py": {"summary": {"percent_covered": pct}}},
        "totals": {"percent_covered": pct},
    }
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_K4_floor_script_flags_file_below_floor(tmp_path: Path) -> None:
    assert load_script().main(write_report(tmp_path / "c.json", 79.9)) == 1


def test_K4_floor_script_passes_at_floor(tmp_path: Path) -> None:
    assert load_script().main(write_report(tmp_path / "c.json", 80.0)) == 0


def test_K4_floor_script_requires_branch_data(tmp_path: Path) -> None:
    assert load_script().main(write_report(tmp_path / "c.json", 95.0, branch=False)) == 2


def test_K4_floor_script_ignores_files_outside_src(tmp_path: Path) -> None:
    report = {
        "meta": {"branch_coverage": True},
        "files": {
            "tests/test_x.py": {"summary": {"percent_covered": 10.0}},
            "src/inkgrid/y.py": {"summary": {"percent_covered": 90.0}},
        },
        "totals": {"percent_covered": 90.0},
    }
    path = tmp_path / "c.json"
    path.write_text(json.dumps(report), encoding="utf-8")
    assert load_script().main(path) == 0
