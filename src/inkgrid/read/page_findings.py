"""Findings a page's own measurements imply (pure). `docs/specs/02-reader.md` section 6."""

from collections.abc import Sequence

from inkgrid.model.findings import Finding, FindingCode
from inkgrid.model.page import PageModel

OCR_HIDDEN_SHARE = 0.5
OCR_IMAGE_RATIO = 0.5
MAX_ENGINE_FINDINGS = 20


def page_findings(page: PageModel, *, has_image: bool, has_curves: bool) -> tuple[Finding, ...]:
    """The findings for one page, in the fixed order: text layer, unmapped, hidden, clipped."""
    n = page.number
    out: list[Finding] = []
    if not page.words:
        if has_image or has_curves:
            detail = "the page draws content but has no text layer; it is not read (no OCR)"
            out.append(Finding.of(FindingCode.NO_TEXT_LAYER, detail, page=n))
        else:
            out.append(Finding.of(FindingCode.BLANK_PAGE, "the page has no text", page=n))
    if page.unmapped_chars:
        detail = f"{page.unmapped_chars} characters have no Unicode mapping; they read as U+FFFD"
        out.append(Finding.of(FindingCode.PARTIAL_TEXT_LAYER, detail, page=n))
    if page.hidden_chars:
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
            out.append(Finding.of(FindingCode.OCR_TEXT_LAYER, detail, page=n))
        else:
            detail = f"{page.hidden_chars} characters are in the text layer but never drawn"
            out.append(Finding.of(FindingCode.HIDDEN_TEXT, detail, page=n))
    if page.clipped_chars:
        detail = f"{page.clipped_chars} characters are clipped or off the page"
        out.append(Finding.of(FindingCode.CLIPPED_TEXT, detail, page=n))
    return tuple(out)


def engine_warning_findings(messages: Sequence[str]) -> tuple[Finding, ...]:
    """One finding per distinct MuPDF warning line, first-seen order, capped with a summary."""
    distinct = list(dict.fromkeys(m.strip() for m in messages if m.strip()))
    out = [Finding.of(FindingCode.PDF_ENGINE_WARNING, m) for m in distinct[:MAX_ENGINE_FINDINGS]]
    extra = len(distinct) - MAX_ENGINE_FINDINGS
    if extra > 0:
        detail = f"{extra} more distinct MuPDF warnings not listed"
        out.append(Finding.of(FindingCode.PDF_ENGINE_WARNING, detail))
    return tuple(out)
