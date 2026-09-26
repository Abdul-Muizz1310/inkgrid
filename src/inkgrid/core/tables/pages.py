"""Which pages the lattice reader reads (docs/specs/06-ruled-tables.md section 3)."""

from inkgrid.model.page import Reading

MIN_RULES = 2  # each way: measured to select exactly Camelot's pages on 6 of 7 fee schedules


def lattice_pages(reading: Reading) -> tuple[int, ...]:
    """The pages with at least two horizontal and two vertical rules.

    Camelot renders every page it reads at 300 DPI and finds nothing on unruled tables (L13), so it
    reads nothing else.
    """
    return tuple(
        page.number
        for page in reading.pages
        if sum(1 for r in page.rules if r.axis == "h") >= MIN_RULES
        and sum(1 for r in page.rules if r.axis == "v") >= MIN_RULES
    )
