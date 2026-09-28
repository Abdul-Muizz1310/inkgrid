"""The checks assembled into a report (docs/specs/10-verify.md sections 3.3, 3.4 and 6).

Each page either engine counts gets one status: verified (every check runs), declared (the reader
said it could not read it), or unverified (the engines cannot be compared on it).
"""

from collections import defaultdict
from dataclasses import dataclass

from inkgrid.model.document import Document, Table
from inkgrid.model.findings import FindingCode
from inkgrid.model.geometry import Rect
from inkgrid.model.page import PageInfo, Word
from inkgrid.model.verification import (
    Defect,
    DefectCode,
    PageCheck,
    VerificationReport,
    Verifier,
)
from inkgrid.verify.checks import Words, table_checks, value_checks
from inkgrid.verify.ink import Ink, InkChar, InkPage
from inkgrid.verify.ownership import PageOwnership, own_page

FRAME_TOL = 0.5
QUOTE_MAX = 80  # characters of a lost run quoted in its detail
CODE_ORDER = {code: i for i, code in enumerate(DefectCode)}


@dataclass
class _Page:
    """One page's check and the defects and advisories found on it."""

    check: PageCheck
    defects: list[Defect]
    advisories: list[Defect]


def _ink_count(page: InkPage | None) -> int:
    return 0 if page is None else sum(1 for ch in page.chars if ch.is_ink)


def _unverified(number: int, why: str) -> _Page:
    check = PageCheck(number=number, status="unverified", ink_chars=0)
    defect = Defect(code=DefectCode.UNVERIFIED, page=number, detail=why)
    return _Page(check, [defect], [])


def _quote(page: InkPage, run: tuple[InkChar, ...]) -> str:
    """The run as it reads on the page, spaces included, cut to QUOTE_MAX characters."""
    first, last = run[0].index, run[-1].index
    text = "".join(
        ch.char if ch.kind != "generated" else " " for ch in page.chars[first : last + 1]
    )
    return text if len(text) <= QUOTE_MAX else text[: QUOTE_MAX - 3] + "..."


def _character_defects(page: InkPage, owned: PageOwnership, words: Words) -> list[Defect]:
    out = [
        Defect(
            code=DefectCode.LOST,
            page=page.number,
            text="".join(ch.char for ch in run),
            bbox=Rect.union_all(ch.box for ch in run),
            detail=f"no word holds {len(run)} ink characters: {_quote(page, run)!r}",
        )
        for run in owned.lost
    ]
    for code, gaps, why in (
        (DefectCode.DOUBLED, owned.doubled, "is ink another word already owns"),
        (DefectCode.INVENTED, owned.invented, "is not on the page"),
    ):
        out += [
            Defect(
                code=code,
                page=page.number,
                block=words.homes[gap.word.id][0],
                text=gap.missing,
                bbox=gap.word.bbox,
                detail=f"{gap.missing!r} of the word {gap.word.text!r} {why}",
            )
            for gap in gaps
        ]
    return out


def _verified(
    page: InkPage,
    info: PageInfo | None,
    words: list[Word],
    tables: list[Table],
    index: Words,
) -> _Page:
    owned = own_page(
        page,
        words,
        clipped_chars=0 if info is None else info.clipped_chars,
        invisible_chars=0 if info is None else info.invisible_chars,
    )
    defects = _character_defects(page, owned, index)
    advisories: list[Defect] = []
    overflow = 0
    for table in tables:
        result = table_checks(table, page, owned.owner, index)
        defects += result.defects
        advisories += result.advisories
        overflow += result.overflow
    defects += value_checks(page, owned.owner, index)
    check = PageCheck(
        number=page.number,
        status="verified",
        ink_chars=_ink_count(page),
        owned_chars=owned.owned,
        lost_chars=sum(len(run) for run in owned.lost),
        outside_chars=owned.outside,
        clipped_chars=owned.clipped,
        soft_hyphens=owned.soft_hyphens,
        unmapped_chars=owned.unmapped,
        overflow_chars=overflow,
        rules=len(page.rules),
    )
    return _Page(check, defects, advisories)


def _why_unverified(
    number: int, page: InkPage | None, info: PageInfo | None, ink: Ink
) -> str | None:
    """Why the engines cannot be compared on the page, or None when they can."""
    if page is None:
        if ink.error is not None:
            return f"PDFium cannot open the PDF: {ink.error}"
        return f"PDFium counts {len(ink.pages)} pages, not page {number}"
    if page.error is not None:
        return f"PDFium cannot load page {number}: {page.error}"
    if info is not None and (
        abs(info.width - page.width) > FRAME_TOL or abs(info.height - page.height) > FRAME_TOL
    ):
        return (
            f"the engines disagree on the page's size: the document's is {info.width} x "
            f"{info.height}, PDFium's {page.width:.2f} x {page.height:.2f}"
        )
    return None


def _sort_key(defect: Defect) -> tuple[int, int, float, float, str]:
    box = defect.bbox or Rect(0, 0, 0, 0)
    return (defect.page, CODE_ORDER[defect.code], box.y0, box.x0, defect.text)


def verify_document(doc: Document, ink: Ink, *, inkgrid_version: str) -> VerificationReport:
    """Grade the document against its ink: every check of spec 10 on every page."""
    index = Words.of(doc)
    words: defaultdict[int, list[Word]] = defaultdict(list)
    for word in doc.words:
        words[word.page].append(word)
    tables: defaultdict[int, list[Table]] = defaultdict(list)
    for table in doc.tables():
        tables[table.regions[0].page].append(table)
    unreadable = {f.page for f in doc.findings if f.code is FindingCode.UNREADABLE_PAGE}
    ink_pages = {p.number: p for p in ink.pages}
    results: list[_Page] = []
    for number in range(1, max(len(doc.pages), len(ink.pages)) + 1):
        page = ink_pages.get(number)
        info = doc.pages[number - 1] if number <= len(doc.pages) else None
        if number in unreadable or (info is None and None in unreadable):
            count = 0 if page is None or page.error is not None else _ink_count(page)
            check = PageCheck(
                number=number, status="declared", ink_chars=count, declared_chars=count
            )
            results.append(_Page(check, [], []))
            continue
        why = _why_unverified(number, page, info, ink)
        if why is not None or page is None:
            results.append(_unverified(number, why or f"PDFium does not count page {number}"))
            continue
        results.append(_verified(page, info, words[number], tables[number], index))
    return VerificationReport(
        source=doc.source,
        verifier=Verifier(inkgrid=inkgrid_version, pypdfium2=ink.pypdfium2, pdfium=ink.pdfium),
        pages=tuple(r.check for r in results),
        defects=tuple(sorted((d for r in results for d in r.defects), key=_sort_key)),
        advisories=tuple(sorted((d for r in results for d in r.advisories), key=_sort_key)),
    )
