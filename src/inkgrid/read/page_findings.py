"""Findings a page's own measurements imply (pure). `docs/specs/02-reader.md` section 6."""

from collections.abc import Sequence
from dataclasses import dataclass

from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.page import PageModel

OCR_HIDDEN_SHARE = 0.5
OCR_IMAGE_RATIO = 0.5
MAX_ENGINE_FINDINGS = 20


@dataclass(frozen=True, slots=True)
class PageSignals:
    """What the reader observed about a page beyond its words: drawn content and failures."""

    has_image: bool = False
    has_curves: bool = False
    type3_chars: int = 0
    warnings: tuple[str, ...] = ()
    extraction_error: str | None = None


def _no_words(page: PageModel, signals: PageSignals) -> Finding:
    drew = signals.has_image or signals.has_curves
    failed = bool(signals.warnings) or signals.extraction_error is not None
    if drew or failed:
        detail = "the page draws content but has no text layer; it is not read (no OCR)"
        if failed and not drew:
            detail = "the page's content could not be decoded, so none of its text can be read"
        return Finding.of(FindingCode.NO_TEXT_LAYER, detail, page=page.number)
    return Finding.of(FindingCode.BLANK_PAGE, "the page has no text", page=page.number)


def _hidden(page: PageModel) -> Finding:
    word_chars = sum(len(w.text) for w in page.words)
    is_ocr = (
        page.hidden_chars >= OCR_HIDDEN_SHARE * word_chars
        and page.image_area_ratio >= OCR_IMAGE_RATIO
    )
    if is_ocr:
        detail = (
            f"{page.hidden_chars} of {word_chars} characters are invisible text over an "
            "image: an OCR layer, not the document's own text"
        )
        return Finding.of(FindingCode.OCR_TEXT_LAYER, detail, page=page.number)
    detail = f"{page.hidden_chars} characters are in the text layer but never drawn"
    return Finding.of(FindingCode.HIDDEN_TEXT, detail, page=page.number)


def page_findings(page: PageModel, signals: PageSignals) -> tuple[Finding, ...]:
    """A page's findings, in the fixed order of the spec."""
    n = page.number
    out: list[Finding] = []
    if signals.extraction_error is not None:
        detail = f"the page's text could not be extracted: {signals.extraction_error}"
        out.append(Finding.of(FindingCode.UNREADABLE_PAGE, detail, page=n))
    if not page.words:
        out.append(_no_words(page, signals))
    if page.unmapped_chars:
        detail = f"{page.unmapped_chars} characters have no Unicode mapping; they read as U+FFFD"
        out.append(Finding.of(FindingCode.PARTIAL_TEXT_LAYER, detail, page=n))
    if page.hidden_chars:
        out.append(_hidden(page))
    if page.clipped_chars:
        detail = (
            f"{page.clipped_chars} characters are clipped, outside the CropBox, or off the page"
        )
        out.append(Finding.of(FindingCode.CLIPPED_TEXT, detail, page=n))
    if signals.type3_chars:
        detail = (
            f"{signals.type3_chars} characters are drawn in a Type 3 font; their Unicode mapping "
            "may be a guess from the raw character code"
        )
        out.append(Finding.of(FindingCode.TYPE3_FONT, detail, page=n))
    out.extend(engine_warning_findings(signals.warnings, page=n))
    return tuple(out)


def engine_warning_findings(
    messages: Sequence[str], *, page: int | None = None
) -> tuple[Finding, ...]:
    """One finding per distinct MuPDF warning line, first-seen order, capped with a summary."""
    distinct = list(dict.fromkeys(m.strip() for m in messages if m.strip()))
    out = [
        Finding.of(FindingCode.PDF_ENGINE_WARNING, m, page=page)
        for m in distinct[:MAX_ENGINE_FINDINGS]
    ]
    extra = len(distinct) - MAX_ENGINE_FINDINGS
    if extra > 0:
        detail = f"{extra} more distinct MuPDF warnings not listed"
        out.append(Finding.of(FindingCode.PDF_ENGINE_WARNING, detail, page=page))
    return tuple(out)
