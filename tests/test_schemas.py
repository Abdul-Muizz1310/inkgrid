import importlib.util
import json
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]


def load_exporter() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "export_schemas", ROOT / "scripts" / "export_schemas.py"
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_P16_reading_schema_is_committed() -> None:
    committed = json.loads((ROOT / "docs" / "schema" / "reading.schema.json").read_text("utf-8"))
    assert load_exporter().schemas()["reading.schema.json"] == committed
