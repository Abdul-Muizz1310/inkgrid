import hashlib
from pathlib import Path

import pytest

from inkgrid_bench.fetch import FetchError, Source, fetch, fetch_manifest


def source(tmp_path: Path, digest: str) -> Source:
    served = tmp_path / "served.bin"
    served.write_bytes(b"inkgrid bench")
    return Source(name="probe", url=served.as_uri(), sha256=digest, file="probe/served.bin")


def test_fetch_keeps_a_file_whose_hash_matches(tmp_path: Path) -> None:
    digest = hashlib.sha256(b"inkgrid bench").hexdigest()
    path = fetch(source(tmp_path, digest), tmp_path / "cache")
    assert path.read_bytes() == b"inkgrid bench"
    assert fetch(source(tmp_path, digest), tmp_path / "cache") == path  # cached: no second download


def test_fetch_refuses_and_deletes_a_file_whose_hash_differs(tmp_path: Path) -> None:
    with pytest.raises(FetchError, match="SHA-256"):
        fetch(source(tmp_path, "0" * 64), tmp_path / "cache")
    assert not (tmp_path / "cache" / "probe" / "served.bin").exists()


def test_a_manifest_fetches_every_listed_file(tmp_path: Path) -> None:
    served = tmp_path / "served"
    (served / "pdfs").mkdir(parents=True)
    listing = []
    for name in ("a.pdf", "b.pdf"):
        data = name.encode()
        (served / "pdfs" / name).write_bytes(data)
        listing.append(f"{hashlib.sha256(data).hexdigest()}  pdfs/{name}")
    (tmp_path / "list.sha256").write_text("\n".join(listing) + "\n")
    paths = fetch_manifest(
        served.as_uri() + "/", tmp_path / "list.sha256", "set", tmp_path / "cache"
    )
    assert [p.read_bytes() for p in paths] == [b"a.pdf", b"b.pdf"]
    assert paths[0] == tmp_path / "cache" / "set" / "pdfs" / "a.pdf"
