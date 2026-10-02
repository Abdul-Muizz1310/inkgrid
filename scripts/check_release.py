"""Refuse a release tag that must not publish (docs/specs/17-release.md section 2).

`python scripts/check_release.py v0.1.0` prints every problem and exits 1, or exits 0 when the tag
is a final version, it is the project's version, and the changelog and README are ready for it.
Stdlib only.

Exit codes: 0 the tag may publish, 1 it must not, 2 no tag given.
"""

from __future__ import annotations

import datetime
import re
import sys
import tomllib
from collections.abc import Sequence
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPOSITORY = "https://github.com/Abdul-Muizz1310/inkgrid"
FINAL_TAG = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)")
# A Markdown or HTML link target that is not absolute or in-page; PyPI cannot follow one.
RELATIVE = re.compile(
    r'\]\((?!https?://|mailto:|#)([^)\s]+)\)|(?:href|src)="(?!https?://|mailto:|#)([^"]+)"'
)


def _section(text: str, heading: str) -> str | None:
    """The text under a `## ` heading, up to the next one; None when there is no such heading."""
    at = re.search(rf"^{re.escape(heading)}$", text, flags=re.MULTILINE)
    if at is None:
        return None
    rest = text[at.end() :]
    end = re.search(r"^## ", rest, flags=re.MULTILINE)
    return rest if end is None else rest[: end.start()]


def _dated(changelog: str, version: str) -> bool:
    """Whether the changelog has the version's section, dated with a real date."""
    pattern = rf"^## \[{re.escape(version)}\] - (\d{{4}}-\d{{2}}-\d{{2}})$"
    found = re.search(pattern, changelog, flags=re.MULTILINE)
    if found is None:
        return False
    try:
        datetime.date.fromisoformat(found.group(1))
    except ValueError:
        return False
    return True


def problems(tag: str, *, version: str, changelog: str, readme: str) -> list[str]:
    """Every reason the tag must not publish; none when it may."""
    out = []
    if FINAL_TAG.fullmatch(tag) is None:
        out.append(f"{tag!r} is not a final version tag (vX.Y.Z)")
    elif tag[1:] != version:
        out.append(f"the tag {tag} is not the project's version {version}")
    if not _dated(changelog, version):
        out.append(f"CHANGELOG.md has no section '## [{version}] - YYYY-MM-DD' with a real date")
    link = f"[{version}]: {REPOSITORY}/releases/tag/v{version}"
    if re.search(rf"^{re.escape(link)}$", changelog, flags=re.MULTILINE) is None:
        out.append(f"CHANGELOG.md has no link reference '{link}'")
    unreleased = _section(changelog, "## [Unreleased]")
    if unreleased is not None and unreleased.strip():
        out.append("CHANGELOG.md's [Unreleased] section still holds entries")
    if "not on PyPI" in readme:
        out.append("README.md still says inkgrid is not on PyPI")
    relative = sorted({a or b for a, b in RELATIVE.findall(readme)})
    if relative:
        out.append(f"README.md links relatively, which PyPI cannot follow: {', '.join(relative)}")
    quick_start = _section(readme, "## Quick start") or ""
    if "pip install inkgrid" not in quick_start:
        out.append("README.md's Quick start has no `pip install inkgrid`")
    return out


def main(argv: Sequence[str] = sys.argv[1:], *, root: Path = ROOT) -> int:
    """Check the tag against the project in `root`."""
    if len(argv) != 1:
        sys.stderr.write("usage: check_release.py TAG\n")
        return 2
    with (root / "pyproject.toml").open("rb") as f:
        version = str(tomllib.load(f)["project"]["version"])
    found = problems(
        argv[0],
        version=version,
        changelog=(root / "CHANGELOG.md").read_text(encoding="utf-8"),
        readme=(root / "README.md").read_text(encoding="utf-8"),
    )
    for problem in found:
        sys.stderr.write(f"release refused: {problem}\n")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
