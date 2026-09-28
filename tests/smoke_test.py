"""Smoke-test an installed inkgrid distribution. Not collected by pytest: run it as a script.

Usage: uv run --isolated --no-project --with dist/inkgrid-*.whl tests/smoke_test.py
"""

import pymupdf

import inkgrid

doc = pymupdf.open()
doc.new_page().insert_text((72, 100), "smoke", fontsize=10)
reading = inkgrid.read_pages(doc.tobytes())
words = [w.text for w in reading.words()]
assert words == ["smoke"], words
assert reading.reader.inkgrid == inkgrid.__version__
data = doc.tobytes()
report = inkgrid.verify(inkgrid.read(data), data)  # PDFium must come with the distribution
assert report.ok, report.defects
assert report.pages[0].owned_chars == len("smoke"), report.pages
print(f"smoke test passed: inkgrid {inkgrid.__version__} read and verified {words}")
