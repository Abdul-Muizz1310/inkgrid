"""Write the published JSON Schemas of inkgrid's output contracts to docs/schema/.

Usage: uv run python scripts/export_schemas.py
"""

from __future__ import annotations

import json
from pathlib import Path

from inkgrid.model.page import Reading

OUT = Path(__file__).resolve().parents[1] / "docs" / "schema"


def schemas() -> dict[str, dict[str, object]]:
    """Map each schema file name to the JSON Schema of the output it describes."""
    return {"reading.schema.json": Reading.model_json_schema(mode="serialization")}


def main() -> int:
    """Write every schema; return 0."""
    OUT.mkdir(parents=True, exist_ok=True)
    for name, schema in schemas().items():
        text = json.dumps(schema, indent=2, sort_keys=True) + "\n"
        (OUT / name).write_text(text, encoding="utf-8")
        print(f"wrote docs/schema/{name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
