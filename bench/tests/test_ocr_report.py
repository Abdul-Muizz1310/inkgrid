import re

import pytest

from inkgrid_bench import ocr_report

GROUPS = ("headers_footers", "multi_column", "tables", "long_tiny_text", "baseline")


def info(group: str, half: str = "dev", *, primary: bool = True) -> dict[str, object]:
    return {"group": group, "half": half, "primary": primary}


def olm(group: str, passed: int, tests: int) -> dict[str, float]:
    counts = {f"olm_{g}_{k}": 0.0 for g in GROUPS for k in ("tests", "passed")}
    counts |= {f"olm_{group}_tests": tests, f"olm_{group}_passed": passed}
    return counts | {"olm_baseline_tests": 1, "olm_baseline_passed": 1}


def omni(edit: float, teds: tuple[float, int] = (0.5, 1)) -> dict[str, float]:
    return {
        "omni_text_edit": edit,
        "omni_text_len": 10,
        "omni_table_edit": 0,
        "omni_table_len": 0,
        "omni_order_edit": edit / 2,
        "omni_order_len": 10,
        "omni_teds_sum": teds[0],
        "omni_teds_n": teds[1],
    }


def pb(value: float) -> dict[str, float]:
    names = (*ocr_report.PARSEBENCH_TABLE, *ocr_report.PARSEBENCH_TEXT)
    return {f"pb_{m}": value for m in names} | {f"pb_{m}_n": 1 for m in names}


def dp(value: float) -> dict[str, float]:
    return {f"dp_{k}": value for k in ("nid", "teds", "mhs")} | {
        f"dp_{k}_n": 1 for k in ("nid", "teds", "mhs")
    }


DOCUMENTS = {
    "olmocr": {
        "headers_footers/1.pdf": info("headers_footers"),
        "headers_footers/2.pdf": info("headers_footers", "test"),
        "multi_column/1.pdf": info("multi_column", "test"),
        "tables/1.pdf": info("tables"),
        "long_tiny_text/1.pdf": info("long_tiny_text", "test"),
    },
    "omnidocbench": {
        "en1": info("english"),
        "zh1": info("simplified_chinese", "test"),
        "mx1": info("en_ch_mixed", "test", primary=False),
    },
    "parsebench": {
        "table/a": info("table"),
        "text/b": info("text_simple", "test"),
        "text/c": info("text_multilang"),
    },
    "dpbench": {"01": info("page"), "02": info("page", "test")},
}
SPEED = {"seconds": 1.0, "pages": 1, "crashed": 0}


def counts(shift: float) -> dict[str, dict[str, dict[str, float]]]:
    return {
        "olmocr": {
            "headers_footers/1.pdf": olm("headers_footers", 1, 2),
            "headers_footers/2.pdf": olm("headers_footers", 2, 2),
            "multi_column/1.pdf": olm("multi_column", 1, 1),
            "tables/1.pdf": olm("tables", 0, 1),
            "long_tiny_text/1.pdf": olm("long_tiny_text", 3, 4),
        },
        "omnidocbench": {
            "en1": omni(1 + shift, (1.4, 2)),
            "zh1": omni(2, (0.1, 1)),
            "mx1": omni(4),
        },
        "parsebench": {"table/a": pb(0.5), "text/b": pb(0.75), "text/c": pb(0.25)},
        "dpbench": {"01": dp(0.9), "02": dp(0.7 - shift / 10)},
    }


def data() -> dict[str, object]:
    tools = {"inkgrid": counts(0), "docling": counts(1)}
    return {
        "documents": DOCUMENTS,
        "counts": {
            b: {t: {d: c | SPEED for d, c in by_tool[b].items()} for t, by_tool in tools.items()}
            for b in DOCUMENTS
        },
        "census": {
            "olmocr": {"documents": 9, "classes": {"born_digital": 5, "no_text": 4}},
            "omnidocbench": {"documents": 4, "classes": {"born_digital": 3, "image_backed": 1}},
            "parsebench": {"documents": 5, "classes": {"born_digital": 4, "ocr_layer": 1}},
            "dpbench": {"documents": 2, "classes": {"born_digital": 2}},
        },
        "crashes": {"docling": {"dpbench": [["02", "timed out"]]}},
        "excluded": {
            "olmocr": {"no_text": ["tables/9.pdf", "tables/8.pdf"]},
            "parsebench": {"ocr_layer": ["text/s"], "group": ["text/h (text_handwritting)"]},
        },
    }


def report(label: ocr_report.OcrLabel = "baseline") -> str:
    return ocr_report.document(data(), head="abc1234", date="2026-10-09", label=label, resamples=50)


def section(text: str, heading: str) -> str:
    """The text from a heading that starts with `heading` to the next heading of its level."""
    level = heading.split(" ", 1)[0]
    start = text.index(heading)
    rest = text[start + len(heading) :]
    end = re.search(rf"^{level} ", rest, flags=re.MULTILINE)
    return text[start : start + len(heading) + (end.start() if end else len(rest))]


def cell(text: str, tool: str, column: str) -> str:
    """The point estimate of `tool`'s row in the first table under `text` with that column."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if cells[0] in {"Tool", "Difference"} and column in cells:
            col = cells.index(column)
            for row in lines[i + 2 :]:
                if not row.startswith("|"):
                    break
                parts = [c.strip() for c in row.strip("|").split("|")]
                if parts[0] == tool:
                    return parts[col].split(" ")[0]
    msg = f"no {column} for {tool}"
    raise AssertionError(msg)


def test_RP1_a_baseline_report_says_born_digital_text_and_tables_only_and_baseline() -> None:
    text = report()
    title, first = text.split("\n\n")[:2]
    assert title.startswith("# ")
    assert "born-digital" in title
    assert "baseline" in title
    assert "born-digital pages" in first
    assert "text and table tests" in first
    assert "baseline" in first
    assert "tuned" not in title
    for kept in (
        "5 of olmOCR-bench's 9",
        "3 of OmniDocBench's 4",
        "4 of ParseBench's 5 (3 of them",
    ):
        assert kept in first
    assert "overall" not in text.lower()


def test_RP1_the_report_lists_every_document_left_out_by_class() -> None:
    left_out = section(report(), "## Documents left out")
    assert "No text (2): tables/8.pdf, tables/9.pdf" in left_out
    assert "OCR layer (1): text/s" in left_out
    assert "Born-digital, in a group not scored (1): text/h (text_handwritting)" in left_out


def test_RP1_documents_a_scorer_could_not_score_as_usual_are_listed() -> None:
    marked = data()
    pb = marked["counts"]["parsebench"]["docling"]  # type: ignore[index]
    pb["text/b"] |= {"pb_unscored": 1}
    pb["table/a"] |= {"pb_failed": 1}
    marked["counts"]["omnidocbench"]["inkgrid"]["zh1"] |= {"omni_fallback": 1}  # type: ignore[index]
    text = ocr_report.document(marked, head="abc1234", date="2026-10-09", resamples=5)
    listed = section(text, "## Documents a scorer did not score as usual")
    assert (
        "| docling | ParseBench | left out of its means (an error of the scorer's) | text/b |"
        in listed
    )
    assert (
        "| docling | ParseBench | scored 0 (the scorer failed on its reading) | table/a |" in listed
    )
    assert "| inkgrid | OmniDocBench | text matched the simple way after 30 s | zh1 |" in listed
    assert "None." in section(report(), "## Documents a scorer did not score as usual")


def test_RP1_olmocr_reports_each_category_and_the_born_digital_macro_tiny_text_apart() -> None:
    olmocr = section(report(), "## olmOCR-bench")
    headline = section(olmocr, "### Pass rates")
    assert "(4 documents)" in headline
    assert cell(headline, "inkgrid", "Headers and footers") == "0.750"
    assert cell(headline, "inkgrid", "Tables") == "0.000"
    assert cell(headline, "inkgrid", "Born-digital macro") == "0.583"  # (0.75 + 1 + 0) / 3
    tiny = section(olmocr, "### Long tiny text")
    assert "(1 documents)" in tiny
    assert cell(tiny, "inkgrid", "Long tiny text") == "0.750"


def test_RP1_omnidocbench_reports_its_strata_and_its_text_by_language() -> None:
    text = report()
    primary = section(text, "## OmniDocBench v1.0, primary stratum")
    every = section(text, "## OmniDocBench v1.0, every born-digital page")
    assert "(2 documents)" in primary.splitlines()[0]
    assert "(3 documents)" in every.splitlines()[0]
    assert cell(section(primary, "### Text, English pages"), "inkgrid", "Text Edit distance") == (
        "0.100"
    )
    chinese = section(every, "### Text, Chinese pages")
    assert "(1 documents)" in chinese  # simplified Chinese only, as OmniDocBench reports it
    assert cell(chinese, "inkgrid", "Text Edit distance") == "0.200"
    tables = section(primary, "### Tables")
    assert cell(tables, "inkgrid", "Table TEDS") == "0.400"  # (1.4 / 2 + 0.1) / 2, page by page
    assert "lower is better" in section(primary, "### Text, English pages").lower()


def test_RP1_parsebench_reports_tables_text_and_multilingual_text_apart() -> None:
    parsebench = section(report(), "## ParseBench")
    assert cell(section(parsebench, "### Tables"), "inkgrid", "GTRM") == "0.500"
    assert cell(section(parsebench, "### Text ("), "inkgrid", "Content faithfulness") == "0.750"
    assert cell(
        section(parsebench, "### Text, multilingual"), "inkgrid", "Content faithfulness"
    ) == ("0.250")


def test_RP1_dpbench_differences_and_crashes_are_reported() -> None:
    text = report()
    dpbench = section(text, "## DP-Bench")
    assert cell(dpbench, "inkgrid", "NID") == "0.800"
    assert cell(dpbench, "inkgrid - docling", "NID") == "+0.050"
    crashes = section(text, "## Crashes and timeouts")
    assert "docling" in crashes
    assert "02 (timed out)" in crashes


def test_RP1_a_tuned_report_reports_dev_and_test_halves_apart() -> None:
    text = report("tuned")
    title, first = text.split("\n\n")[:2]
    assert "tuned" in title
    assert "baseline" not in title
    assert "test half" in first
    dev = section(text, "## DP-Bench, dev half")
    test = section(text, "## DP-Bench, test half")
    assert "(1 documents)" in dev.splitlines()[0]
    assert cell(dev, "inkgrid", "NID") == "0.900"
    assert cell(test, "inkgrid", "NID") == "0.700"


def test_RP1_a_part_without_documents_says_so() -> None:
    text = report("tuned")
    dev_tiny = section(section(text, "## olmOCR-bench, dev half"), "### Long tiny text")
    assert "No documents" in dev_tiny


def test_RP1_tools_covering_different_documents_are_refused() -> None:
    broken = data()
    del broken["counts"]["dpbench"]["docling"]["02"]  # type: ignore[index]
    with pytest.raises(ValueError, match="dpbench"):
        ocr_report.document(
            broken, head="abc1234", date="2026-10-09", label="baseline", resamples=5
        )
