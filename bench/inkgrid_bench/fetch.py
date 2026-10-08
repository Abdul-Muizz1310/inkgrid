"""Fetch a pinned source into the cache, verified by SHA-256 (spec 12 section 1)."""

import hashlib
import shutil
import tomllib
import urllib.request
from dataclasses import dataclass
from pathlib import Path

CACHE = Path.home() / ".cache" / "inkgrid-bench"
MICROMAMBA = CACHE / "tools" / "micromamba" / "bin" / "micromamba"
TESSERACT = CACHE / "tools" / "tesseract"  # the conda prefix: bin/tesseract, share/tessdata
SOURCES = Path(__file__).resolve().parents[1] / "sources.toml"


class FetchError(Exception):
    """A download that failed, or whose bytes are not the pinned ones."""


@dataclass(frozen=True, slots=True)
class Source:
    """One pinned file: where it comes from, its SHA-256, and where it lives in the cache."""

    name: str
    url: str
    sha256: str
    file: str


def sources(path: Path = SOURCES) -> dict[str, Source]:
    """Every pinned source in `sources.toml`, by name."""
    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return {name: Source(name=name, **entry) for name, entry in data["source"].items()}


def digest(path: Path) -> str:
    """A file's SHA-256, in hex."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(source: Source, cache: Path = CACHE) -> Path:
    """The source's file in the cache, downloaded once and verified each time it is fetched.

    Raises:
        FetchError: the download failed, or its SHA-256 is not the pinned one (the file is deleted).
    """
    target = cache / source.file
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        part = target.with_suffix(target.suffix + ".part")
        try:
            # The URLs are pinned in sources.toml, and every byte is checked against its hash.
            response = urllib.request.urlopen(source.url, timeout=600)  # noqa: S310
            with response, part.open("wb") as out:
                shutil.copyfileobj(response, out)
        except OSError as exc:
            part.unlink(missing_ok=True)
            msg = f"{source.name}: cannot download {source.url}: {exc}"
            raise FetchError(msg) from exc
        part.replace(target)
    found = digest(target)
    if found != source.sha256:
        target.unlink()
        msg = f"{source.name}: SHA-256 {found} is not the pinned {source.sha256}"
        raise FetchError(msg)
    return target


def fetch_manifest(base_url: str, listing: Path, root: str, cache: Path = CACHE) -> list[Path]:
    """Every file a `sha256sum`-style listing names, fetched from `base_url` into `cache/root`.

    Raises:
        FetchError: as `fetch`, for the first file that fails.
    """
    out = []
    for line in listing.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        pinned, relative = line.split(maxsplit=1)
        name = f"{root}/{relative}"
        out.append(fetch(Source(name, base_url + relative, pinned, name), cache))
    return out
