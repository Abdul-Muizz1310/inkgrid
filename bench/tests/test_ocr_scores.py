import json
from pathlib import Path

import pytest

from inkgrid_bench.scores import dpbench, olmocr_pages, omnidocbench
from inkgrid_bench.scores.metrics import mean_of, pooled


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
    assert pooled("omni_teds_sum", "omni_teds_n")(docs) == pytest.approx(1.5 / 3)
    assert mean_of("omni_order_edit", "omni_order_len")(docs) == pytest.approx((0.25 + 0) / 2)
    gt = [{"page_info": {"image_path": f"images/{p}.jpg"}} for p in ("p1", "p2", "p3")]
    assert [p["page_info"]["image_path"] for p in omnidocbench.subset(gt, {"p2"})] == [
        "images/p2.jpg"
    ]


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
