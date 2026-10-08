import json
from pathlib import Path

import pytest

from inkgrid_bench.scores import dpbench, olmocr_pages, omnidocbench, parsebench
from inkgrid_bench.scores.metrics import mean_of


def test_SC1_every_scored_pdf_gets_a_page_and_its_tests_are_counted(tmp_path: Path) -> None:
    folder = tmp_path / "candidate"
    ids = ["headers_footers/a.pdf", "tables/b.pdf", "multi_column/c.pdf"]
    olmocr_pages.write_candidate(folder, ids, {"headers_footers/a.pdf": "A", "tables/b.pdf": ""})
    assert (folder / "headers_footers" / "a_pg1_repeat1.md").read_text() == "A"
    assert (folder / "tables" / "b_pg1_repeat1.md").read_text() == ""
    assert (folder / "multi_column" / "c_pg1_repeat1.md").read_text() == ""  # no reading: empty
    results = {
        "h1": {"pdf": "headers_footers/a.pdf", "group": "headers_footers", "passed": True},
        "h2": {"pdf": "headers_footers/a.pdf", "group": "headers_footers", "passed": False},
        "headers_footers/a.pdf_baseline": {
            "pdf": "headers_footers/a.pdf",
            "group": "baseline",
            "passed": True,
        },
        "t1": {"pdf": "tables/b.pdf", "group": "tables", "passed": False},
        "multi_column/c.pdf_baseline": {
            "pdf": "multi_column/c.pdf",
            "group": "baseline",
            "passed": False,
        },
    }
    counts = olmocr_pages.pdf_counts(results, ids)
    assert counts["headers_footers/a.pdf"] == {
        "olm_headers_footers_tests": 2,
        "olm_headers_footers_passed": 1,
        "olm_baseline_tests": 1,
        "olm_baseline_passed": 1,
    }
    assert counts["tables/b.pdf"] == {"olm_tables_tests": 1, "olm_tables_passed": 0}
    with pytest.raises(ValueError, match=r"multi_column/d\.pdf"):
        olmocr_pages.pdf_counts(results, [*ids, "multi_column/d.pdf"])


def sample(page: str, edit: int, length: int, **extra: object) -> dict[str, object]:
    return {"image_name": page, "Edit_num": edit, "upper_len": length, **extra}


def test_SC2_omnidocbench_pages_reproduce_its_own_aggregates(tmp_path: Path) -> None:
    result = tmp_path / "result"
    result.mkdir()
    name = "pred_quick_match"
    text = [sample("p1.jpg", 1, 10), sample("p1.jpg", 1, 10), sample("p2.jpg", 6, 12)]
    tables = [
        sample("p1", 2, 20, metric={"TEDS": 0.9, "TEDS_structure_only": 1.0}),
        sample("p1", 0, 0, metric={"TEDS": 0.5, "TEDS_structure_only": 0.5}),
        sample("p2", 5, 10, metric={"TEDS": 0.1, "TEDS_structure_only": 0.2}),
    ]
    order = [sample("p1.jpg", 1, 4), sample("p2.jpg", 0, 3)]
    for element, rows in (("text_block", text), ("table", tables), ("reading_order", order)):
        (result / f"{name}_{element}_result.json").write_text(json.dumps(rows))
    pages = omnidocbench.page_counts(result, name, ["p1", "p2", "p3"])
    assert pages["p1"]["omni_text_edit"] == 2
    assert pages["p1"]["omni_text_len"] == 20
    assert pages["p3"] == dict.fromkeys(omnidocbench.KEYS, 0)  # nothing matched: no value
    docs = list(pages.values())
    assert mean_of("omni_text_edit", "omni_text_len")(docs) == pytest.approx((0.1 + 0.5) / 2)
    assert mean_of("omni_teds_sum", "omni_teds_n")(docs) == pytest.approx((0.7 + 0.1) / 2)
    assert mean_of("omni_order_edit", "omni_order_len")(docs) == pytest.approx((0.25 + 0) / 2)
    gt = [{"page_info": {"image_path": f"images/{p}.jpg"}} for p in ("p1", "p2", "p3")]
    assert [p["page_info"]["image_path"] for p in omnidocbench.subset(gt, {"p2"})] == [
        "images/p2.jpg"
    ]


def scorer_result(text: float, teds: float, english: float) -> dict[str, object]:
    by_language = {"language: english": english, "language: simplified_chinese": 0.3}
    return {
        "text_block": {
            "all": {"Edit_dist": {"ALL_page_avg": text}},
            "page": {"Edit_dist": {"ALL": text, **by_language}},
        },
        "table": {
            "all": {"Edit_dist": {"ALL_page_avg": 0.25}, "TEDS": {"all": 0.5}},
            "page": {"TEDS": {"ALL": teds}},
        },
        "reading_order": {"all": {"Edit_dist": {"ALL_page_avg": "NaN"}}},
    }


def test_SC2_the_pages_reproduce_the_scorers_own_page_averages() -> None:
    zero = dict.fromkeys(omnidocbench.KEYS, 0.0)
    pages = {
        "p1": zero
        | {"omni_text_edit": 1, "omni_text_len": 10, "omni_teds_sum": 1.4, "omni_teds_n": 2},
        "p2": zero | {"omni_text_edit": 3, "omni_text_len": 10, "omni_table_edit": 1},
        "p3": zero
        | {"omni_table_edit": 1, "omni_table_len": 4, "omni_teds_sum": 0.1, "omni_teds_n": 1},
    }
    pages["p2"]["omni_table_len"] = 4
    languages = {"p1": "english", "p2": "simplified_chinese", "p3": "english"}
    assert omnidocbench.check(pages, languages, scorer_result(0.2, 0.4, 0.1)) == []
    problems = omnidocbench.check(pages, languages, scorer_result(0.2, 0.5, 0.3))
    assert len(problems) == 2
    assert "table TEDS" in problems[0]
    assert "english" in problems[1]


def test_SC4_dpbench_scores_each_document_and_refuses_a_dropped_one() -> None:
    evaluation = {
        "documents": [
            {"document_id": "01", "scores": {"nid": 0.9, "teds": None, "mhs": 0.5}},
            {"document_id": "02", "scores": {"nid": 0.7, "teds": 0.8, "mhs": None}},
        ]
    }
    scores = dpbench.document_scores(evaluation, ["01", "02"])
    assert scores["01"] == {
        "dp_nid": 0.9,
        "dp_nid_n": 1,
        "dp_teds": 0.0,
        "dp_teds_n": 0,
        "dp_mhs": 0.5,
        "dp_mhs_n": 1,
    }
    docs = list(scores.values())
    assert mean_of("dp_nid", "dp_nid_n")(docs) == pytest.approx(0.8)
    assert mean_of("dp_teds", "dp_teds_n")(docs) == pytest.approx(0.8)
    with pytest.raises(ValueError, match="03"):
        dpbench.document_scores(evaluation, ["01", "02", "03"])


def test_SC3_parsebench_reads_saved_markdown_with_html_tables_and_scores_back(
    tmp_path: Path,
) -> None:
    saved = tmp_path / "saved"
    md = {"table/a": "Intro\n\n| X | Y |\n| --- | --- |\n| 1 | 2 |", "text/b": "Plain text."}
    parsebench.write_saved(saved, ["table/a", "text/b", "text/c"], md)
    assert (saved / "table__a.md").read_text().startswith("Intro\n\n<table><thead>")
    assert (saved / "text__b.md").read_text() == "Plain text."
    assert (saved / "text__c.md").read_text() == ""
    report = {
        "per_example_results": [
            {
                "test_id": "text/b",
                "success": True,
                "metrics": [
                    {"metric_name": "content_faithfulness", "value": 0.75},
                    {"metric_name": "normalized_order", "value": 0.5},
                    {"metric_name": "normalized_text_correctness", "value": 0.875},
                ],
            },
            {"test_id": "text/z", "success": True, "metrics": []},
        ]
    }
    scores = parsebench.document_scores(report, ["text/b"], parsebench.TEXT_METRICS)
    assert scores == {
        "text/b": {
            "pb_content_faithfulness": 0.75,
            "pb_content_faithfulness_n": 1,
            "pb_normalized_order": 0.5,
            "pb_normalized_order_n": 1,
            "pb_normalized_text_correctness": 0.875,
            "pb_normalized_text_correctness_n": 1,
        }
    }
    with pytest.raises(ValueError, match="text/c"):
        parsebench.document_scores(report, ["text/b", "text/c"], parsebench.TEXT_METRICS)
    failed = {"per_example_results": [{"test_id": "text/b", "success": False, "metrics": []}]}
    with pytest.raises(ValueError, match="text/b"):
        parsebench.document_scores(failed, ["text/b"], parsebench.TEXT_METRICS)
