"""The heavy competitors' outputs as normalized tables (docs/specs/15-heavy-competitors.md s. 2.2).

Pure: each conversion takes a tool's own export and its pages' frames. The export is parsed field
by field, so a field that is missing or out of range (`ValueError`) or of the wrong type
(`TypeError`) is the document's error, never a guess. Every tool reports a turned page as it
displays, so each box is turned back into the unrotated page (spec 12 s. 3.1).
"""

import re
from collections.abc import Iterator, Mapping, Sequence

from inkgrid_bench.html_tables import cells_from_html
from inkgrid_bench.tables import Box, NCell, NPage, NTable

_MARKER_PAGE = re.compile(r"/page/(\d+)/")  # a marker block id: /page/N/Kind/M, N from 0


def _field(data: object, key: str) -> object:
    if not isinstance(data, Mapping) or key not in data:
        msg = f"missing field {key!r}"
        raise ValueError(msg)
    return data[key]


def _number(value: object, what: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        msg = f"{what} is not a number: {value!r}"
        raise TypeError(msg)
    return float(value)


def _num(data: object, key: str) -> float:
    return _number(_field(data, key), f"field {key!r}")


def _int(data: object, key: str) -> int:
    value = _field(data, key)
    if isinstance(value, bool) or not isinstance(value, int):
        msg = f"field {key!r} is not an integer: {value!r}"
        raise TypeError(msg)
    return value


def _span(data: object, key: str) -> int:
    value = _int(data, key)
    if value < 1:
        msg = f"field {key!r} spans {value}"
        raise ValueError(msg)
    return value


def _str(data: object, key: str) -> str:
    value = _field(data, key)
    if not isinstance(value, str):
        msg = f"field {key!r} is not text: {value!r}"
        raise TypeError(msg)
    return value


def _list(data: object, key: str) -> Sequence[object]:
    value = _field(data, key)
    if not isinstance(value, list | tuple):
        msg = f"field {key!r} is not a list: {value!r}"
        raise TypeError(msg)
    return value


def _frame(frames: Sequence[NPage], page: int) -> NPage:
    if not 1 <= page <= len(frames):
        msg = f"a table on page {page} of {len(frames)}"
        raise ValueError(msg)
    return frames[page - 1]


def _turned_back(frame: NPage, x0: float, y0: float, x1: float, y1: float) -> Box:
    """A box of the displayed top-left frame, placed in the unrotated top-left frame."""
    ax, ay = frame.from_shown(x0, y0)
    bx, by = frame.from_shown(x1, y1)
    return (min(ax, bx), min(ay, by), max(ax, bx), max(ay, by))


def docling_tables(doc: Mapping[str, object], frames: Sequence[NPage]) -> list[NTable]:
    """Docling's `export_to_dict()`: each table's cells, on its first provenance's page."""
    pages = _field(doc, "pages")
    out: list[NTable] = []
    for table in _list(doc, "tables"):
        provenance = _list(table, "prov")
        if not provenance:
            continue  # a table placed on no page
        prov = provenance[0]
        page = _int(prov, "page_no")
        box = _field(prov, "bbox")
        left, top, right, bottom = (_num(box, k) for k in ("l", "t", "r", "b"))
        origin = _str(box, "coord_origin")
        if origin == "BOTTOMLEFT":
            height = _num(_field(_field(pages, str(page)), "size"), "height")
            top, bottom = height - top, height - bottom
        elif origin != "TOPLEFT":
            msg = f"a box whose origin is {origin}"
            raise ValueError(msg)
        cells = [
            NCell(
                _int(c, "start_row_offset_idx"),
                _int(c, "start_col_offset_idx"),
                _span(c, "row_span"),
                _span(c, "col_span"),
                _str(c, "text"),
                header=_field(c, "column_header") is True,
            )
            for c in _list(_field(table, "data"), "table_cells")
        ]
        if cells:
            bbox = _turned_back(_frame(frames, page), left, top, right, bottom)
            out.append(NTable.filled(page=page, bbox=bbox, cells=cells))
    return out


def _blocks(block: object) -> Iterator[object]:
    """A marker block and every block under it, in document order."""
    yield block
    children = block.get("children") if isinstance(block, Mapping) else None
    if children is None:
        return
    if not isinstance(children, list | tuple):
        msg = f"children that are not a list: {children!r}"
        raise TypeError(msg)
    for child in children:
        yield from _blocks(child)


def marker_tables(rendered: Mapping[str, object], frames: Sequence[NPage]) -> list[NTable]:
    """Marker's JSON output: each `Table` block's HTML, on the page its id names."""
    out: list[NTable] = []
    for block in _blocks(rendered):
        if not isinstance(block, Mapping) or block.get("block_type") != "Table":
            continue
        ident = _str(block, "id")
        found = _MARKER_PAGE.match(ident)
        if found is None:
            msg = f"a table id with no page: {ident!r}"
            raise ValueError(msg)
        page = int(found[1]) + 1
        corners = _list(block, "bbox")
        if len(corners) != 4:  # noqa: PLR2004 - x0, y0, x1, y1
            msg = f"a table box of {len(corners)} numbers"
            raise ValueError(msg)
        x0, y0, x1, y1 = (_number(v, "a box corner") for v in corners)
        cells = cells_from_html(_str(block, "html"))
        if cells:
            bbox = _turned_back(_frame(frames, page), x0, y0, x1, y1)
            out.append(NTable.filled(page=page, bbox=bbox, cells=cells))
    return out


def unstructured_tables(
    elements: Sequence[Mapping[str, object]], frames: Sequence[NPage]
) -> list[NTable]:
    """Unstructured's `Element.to_dict()`s: each `Table`'s HTML, its box scaled from pixels."""
    out: list[NTable] = []
    for element in elements:
        if _str(element, "type") != "Table":
            continue
        meta = _field(element, "metadata")
        html = meta.get("text_as_html") if isinstance(meta, Mapping) else None
        if html is None:
            continue  # its structure was not inferred
        if not isinstance(html, str):
            msg = f"field 'text_as_html' is not text: {html!r}"
            raise TypeError(msg)
        page = _int(meta, "page_number")
        coords = _field(meta, "coordinates")
        if _str(coords, "system") != "PixelSpace":
            msg = f"coordinates in {_str(coords, 'system')}"
            raise ValueError(msg)
        width, height = _num(coords, "layout_width"), _num(coords, "layout_height")
        points = [p for p in _list(coords, "points") if isinstance(p, list | tuple) and len(p) == 2]  # noqa: PLR2004
        if not points:
            msg = "a table with no coordinate points"
            raise ValueError(msg)
        frame = _frame(frames, page)
        shown_w, shown_h = frame.shown_size
        xs = [_number(p[0], "a point") * shown_w / width for p in points]
        ys = [_number(p[1], "a point") * shown_h / height for p in points]
        cells = cells_from_html(html)
        if cells:
            bbox = _turned_back(frame, min(xs), min(ys), max(xs), max(ys))
            out.append(NTable.filled(page=page, bbox=bbox, cells=cells))
    return out
