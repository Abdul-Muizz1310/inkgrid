import math
from pathlib import Path

import pytest

from inkgrid_bench.scores import binding, icdar, metrics, olmocr, soric
from inkgrid_bench.scores.binding import AccessPath, Binding
from inkgrid_bench.tables import NCell, NDocument, NPage, NTable

DATA = Path(__file__).parent / "data"

# The competition jar's output for eu-001's structure scored against itself (spec 12 section 0),
# a document with one table found, and region mode with eu-001's first table split (measured).
EU001_SELF = (DATA / "jar-str-eu-001-self.txt").read_text(encoding="ascii")
EU001_SIZES = {1: 46, 2: 81, 3: 60, 4: 158, 5: 151, 6: 116, 7: 53}
ONE_FOUND = (DATA / "jar-str-one-found.txt").read_text(encoding="ascii")
REG_SPLIT = (DATA / "jar-reg-eu-001-split.txt").read_text(encoding="ascii")
PORTRAIT = NPage(box=(0.0, 0.0, 595.0, 842.0), rotation=0)


def test_SC1_the_jars_output_parses_to_per_table_counts() -> None:
    assert icdar.gt_sizes(EU001_SELF) == EU001_SIZES
    counts = icdar.structure_counts(EU001_SELF, EU001_SIZES)
    assert counts == {"correct": 665, "detected": 665, "gt": 665}
    assert metrics.mean_of("correct", "detected")([counts]) == 1.0
    assert metrics.mean_of("correct", "gt")([counts]) == 1.0


def test_SC1_a_warning_without_a_newline_does_not_hide_a_table() -> None:
    # practice eu-014 against itself (measured): the jar's GT warning runs into the table line
    out = (DATA / "jar-str-eu-014-self.txt").read_text(encoding="ascii")
    assert icdar.gt_sizes(out) == {1: 130}
    with pytest.raises(ValueError, match="twice"):
        icdar.structure_counts(out + out, {1: 130})


def test_SC1_an_unmatched_table_counts_its_ground_truth_only() -> None:
    counts = icdar.structure_counts(ONE_FOUND, {1: 46, 2: 81})
    assert counts == {"correct": 30, "detected": 40, "gt": 127}


def test_SC1_false_positive_tables_count_as_detected_relations() -> None:
    # inkgrid on practice eu-012 (measured): two tables matched, two more matching none
    out = (DATA / "jar-str-eu-012-inkgrid.txt").read_text(encoding="ascii")
    assert icdar.structure_counts(out, {1: 103, 2: 103}) == {
        "correct": 2, "detected": 4 + 4 + 4 + 4, "gt": 206,
    }  # fmt: skip
    with pytest.raises(ValueError, match="FALSE POSITIVE"):
        icdar.structure_counts(out.replace("2 FALSE", "3 FALSE"), {1: 103, 2: 103})


def test_SC1_a_table_the_jar_did_not_report_is_an_error() -> None:
    with pytest.raises(ValueError, match="table 3"):
        icdar.structure_counts(ONE_FOUND, {1: 46, 2: 81, 3: 10})
    with pytest.raises(ValueError, match="GT size"):
        icdar.structure_counts(ONE_FOUND, {1: 45, 2: 81})


def test_SC1_regions_count_items_and_false_positives_as_detected() -> None:
    counts = icdar.region_counts(REG_SPLIT)
    assert counts == {"correct": 129, "detected": 129 + 89, "gt": 218 + 395}
    with pytest.raises(ValueError, match="GT Regions"):
        icdar.region_counts(REG_SPLIT.replace("GT Regions: 2", "GT Regions: 3"))


def test_SC1_several_false_positive_regions_share_one_line_and_a_total() -> None:
    # pdfplumber on eu-011 (measured): seven FP regions on one line, then their total
    counts = icdar.region_counts((DATA / "jar-reg-eu-011-pdfplumber.txt").read_text())
    assert counts == {"correct": 183, "detected": 183 + 3082, "gt": 183}
    broken = (DATA / "jar-reg-eu-011-pdfplumber.txt").read_text().replace("3082", "3081")
    with pytest.raises(ValueError, match="FP items"):
        icdar.region_counts(broken)


def test_SC1_the_jar_runs_with_the_sort_it_was_written_for() -> None:
    # Java 7's TimSort rejects the jar's comparator on practice eu-014 (measured)
    cmd = icdar.command(
        Path("java"), Path("t"), "-reg", gt=Path("a-reg.xml"), result=Path("b"), pdf=Path("a.pdf")
    )
    assert cmd[:2] == ["java", "-Djava.util.Arrays.useLegacyMergeSort=true"]
    assert cmd[-4:] == ["-reg", "a-reg.xml", "b", "a.pdf"]
    assert "t/fontbox-1.8.2.jar" in cmd[3]


def test_SC2_a_document_with_nothing_detected_has_no_precision_and_zero_recall() -> None:
    docs = [{"correct": 3, "detected": 4, "gt": 6}, {"correct": 0, "detected": 0, "gt": 5}]
    precision = metrics.mean_of("correct", "detected")(docs)
    recall = metrics.mean_of("correct", "gt")(docs)
    assert precision == 0.75
    assert recall == 0.25
    assert metrics.harmonic(
        metrics.mean_of("correct", "detected"), metrics.mean_of("correct", "gt")
    )(docs) == pytest.approx(2 * 0.75 * 0.25 / 1.0)
    assert metrics.pooled("correct", "detected")(docs) == 0.75
    assert metrics.pooled("correct", "gt")(docs) == 3 / 11
    assert math.isnan(metrics.mean_of("correct", "detected")([docs[1]]))


def test_SC2_the_dice_form_is_twice_the_matches_over_both_counts() -> None:
    docs = [{"tp": 2, "pred": 3, "gt": 2}, {"tp": 0, "pred": 0, "gt": 1}]
    assert metrics.dice("tp", "pred", "gt")(docs) == 4 / 6


def grid(value_row: int = 2, *, country: bool = True) -> NTable:
    # Country        | Gross sample * (2 cols)
    #                | Number | Percent
    # AT             | 848    | 3,6        (848 at value_row)
    cells = [
        NCell(0, 1, cols=2, text="Gross sample *", header=True),
        NCell(1, 1, text="Number"),
        NCell(1, 2, text="Percent"),
        NCell(2, 0, text="AT"),
        NCell(value_row, 1, text="848"),
        NCell(2, 2, text="3,6"),
    ]
    if country:
        cells.append(NCell(0, 0, text="Country"))
    return NTable.filled(page=1, bbox=(0.0, 0.0, 300.0, 60.0), cells=cells)


PATH = AccessPath(value="848", dimensions=(("Country", "AT"), ("Gross sample *", "Number")))


def test_BD1_a_path_along_the_grid_is_bound() -> None:
    assert binding.binds(grid(), PATH) == Binding(value=True, leaf=True, strict=True)


def test_BD2_a_value_off_its_row_is_neither_bound_nor_leaf_bound() -> None:
    assert binding.binds(grid(value_row=3), PATH) == Binding(value=True, leaf=False, strict=False)


def test_BD3_a_missing_upper_label_is_leaf_bound_only() -> None:
    assert binding.binds(grid(country=False), PATH) == Binding(value=True, leaf=True, strict=False)


def test_BD4_a_value_found_twice_binds_through_the_aligned_one() -> None:
    table = grid()
    stray = NTable.filled(
        page=1,
        bbox=table.bbox,
        cells=[*[c for c in table.cells if c.text], NCell(4, 2, text="848")],
    )
    assert binding.binds(stray, PATH) == Binding(value=True, leaf=True, strict=True)


def test_BD_texts_compare_after_nfkc_casefold_and_whitespace() -> None:
    path = AccessPath(
        value="8 4 8", dimensions=(("country", "\uff21T"), ("GROSS  sample*", "number"))
    )
    assert binding.binds(grid(), path).strict


def test_BD_a_later_label_binds_only_through_a_cell_on_the_leafs_chain() -> None:
    # "Number" sits under both samples; the path names Net sample, so Gross sample must not bind it
    cells = [
        NCell(0, 1, text="Gross sample *"),
        NCell(0, 2, text="Net sample **"),
        NCell(1, 1, text="Number"),
        NCell(1, 2, text="Number"),
        NCell(2, 0, text="AT"),
        NCell(2, 1, text="848"),
        NCell(2, 2, text="639"),
    ]
    table = NTable.filled(page=1, bbox=(0, 0, 1, 1), cells=cells)
    wrong = AccessPath(value="639", dimensions=(("AT",), ("Gross sample *", "Number")))
    assert binding.binds(table, wrong) == Binding(value=True, leaf=True, strict=False)


def test_BD_access_paths_parse_by_table_with_dimensions_split_on_empty_fields() -> None:
    text = (
        '"1",,,,,,\n'
        '"Country","AT",,"Gross sample *","Number",,"848"\n'
        '"Country","AT",,"Return rate",,"72,6",\n'
        '"2",,,\n'
        '"A",,"5"\n'
    )
    assert binding.parse_fnc(text) == [
        [PATH, AccessPath(value="72,6", dimensions=(("Country", "AT"), ("Return rate",)))],
        [AccessPath(value="5", dimensions=(("A",),))],
    ]


STR_XML = (DATA / "icdar-str-two-cells.xml").read_text(encoding="ascii")


def test_BD_ground_truth_regions_come_from_the_cells_in_the_top_left_frame() -> None:
    (gt,) = binding.gt_tables(STR_XML, [PORTRAIT])
    assert gt.regions == ((1, (100.0, 100.0, 300.0, 152.0)),)
    assert gt.texts == frozenset({"fee", "0.30bp"})


def test_BD_a_ground_truth_table_matches_the_tool_table_it_overlaps_most() -> None:
    near = NTable.filled(page=1, bbox=(90.0, 90.0, 250.0, 160.0), cells=[NCell(0, 0)])
    most = NTable.filled(page=1, bbox=(120.0, 95.0, 320.0, 160.0), cells=[NCell(0, 0)])
    other_page = NTable.filled(page=2, bbox=(100.0, 100.0, 300.0, 152.0), cells=[NCell(0, 0)])
    region = (100.0, 100.0, 300.0, 152.0)
    assert binding.match([near, most, other_page], 1, region) is most
    assert binding.match([other_page], 1, region) is None


def test_BD_a_documents_counts_cover_its_evaluable_paths_only() -> None:
    gt = binding.gt_tables(STR_XML, [PORTRAIT])
    tool = NTable.filled(
        page=1,
        bbox=(100.0, 100.0, 300.0, 152.0),
        cells=[NCell(0, 0, text="Fee"), NCell(0, 1, text="0.30 bp")],
    )
    paths = [
        [
            AccessPath(value="0.30bp", dimensions=(("Fee",),)),
            AccessPath(
                value="0,30", dimensions=(("Fee",),)
            ),  # not in the ground truth: not evaluable
        ]
    ]
    counts = binding.binding_counts(gt, paths, [tool])
    assert counts == {"paths": 1, "value": 1, "leaf": 1, "bound": 1}
    assert binding.binding_counts(gt, paths, []) == {"paths": 1, "value": 0, "leaf": 0, "bound": 0}


def two_page_doc() -> NDocument:
    table = NTable.filled(
        page=2,
        bbox=(100.0, 299.0, 482.0, 391.0),
        cells=[NCell(0, 0, text="Fee", header=True), NCell(1, 0, text="0.30")],
    )
    return NDocument(
        tool="t",
        version="1",
        pdf_sha256="0" * 64,
        pages=(PORTRAIT, PORTRAIT),
        tables=(table,),
    )


def test_soric_predictions_are_keyed_by_page_image_without_header_markup() -> None:
    preds = soric.predictions({"eu-001": two_page_doc()})
    assert list(preds) == ["eu-001_1.jpg"]
    (box,) = preds["eu-001_1.jpg"]["boxes"]
    assert [round(v) for v in box] == [119, 355, 572, 464]
    ((html,),) = preds["eu-001_1.jpg"]["html"]
    assert html.startswith("<table><tbody><tr><td>Fee</td>")


def test_soric_results_count_per_document_matches_at_half_iou() -> None:
    results = {
        "all": {
            "iou": [0.9, 0.4, 0.0, 0.7],
            "top": [0.8, 0.9, 0.0, 0.5],
            "con": [0.7, 0.9, 0.0, 0.4],
            "teds": [0.6, 0.9, 0.0, 0.3],
            "img_name": [["a_0.jpg", "a_1.jpg", "b_0.jpg", "a_0.jpg"]],
        },
        "ground_truths": 4,
    }
    counts = soric.result_counts(results, {"a": 2, "b": 1, "c": 1})
    assert counts["a"] == pytest.approx(
        {"pred": 3, "gt": 2, "tp": 2, "top": 1.3, "con": 1.1, "teds": 0.9}
    )
    assert counts["b"] == {"pred": 1, "gt": 1, "tp": 0, "top": 0, "con": 0, "teds": 0}
    assert counts["c"] == {"pred": 0, "gt": 1, "tp": 0, "top": 0, "con": 0, "teds": 0}
    with pytest.raises(ValueError, match="ground truths"):
        soric.result_counts(results, {"a": 2, "b": 1})
    empty = soric.result_counts({"all": {}, "ground_truths": 4}, {"a": 2, "b": 1, "c": 1})
    assert empty["a"]["pred"] == 0


def test_soric_ground_truth_counts_pair_boxes_with_html_on_imaged_pages(tmp_path: Path) -> None:
    for d in ("test", "html", "images"):
        (tmp_path / d).mkdir()
    box = "<object><name>table</name></object>"
    (tmp_path / "test" / "a_0.xml").write_text(f"<annotation>{box}{box}</annotation>")
    (tmp_path / "test" / "b_1.xml").write_text(f"<annotation>{box}</annotation>")
    (tmp_path / "test" / "bb_0.xml").write_text(f"<annotation>{box}</annotation>")  # no image
    for name in ("a_0_0", "b_1_0", "b_1_1", "bb_0_0"):
        (tmp_path / "html" / f"{name}.html").write_text("<table></table>")
    for name in ("a_0", "a_1", "b_0", "b_1"):
        (tmp_path / "images" / f"{name}.jpg").write_bytes(b"")
    assert soric.gt_counts(tmp_path) == {"a": 1, "b": 1}


def test_olmocr_pages_hold_every_table_as_html_with_header_rows() -> None:
    page = olmocr.page_markdown(two_page_doc())
    assert page.startswith("<table><thead><tr><th>Fee</th></tr></thead>")
    assert olmocr.page_markdown(NDocument("t", "1", "0" * 64, (PORTRAIT,), ())) == ""
    assert olmocr.candidate_path("tables/abc_pg4.pdf") == "tables/abc_pg4_pg1_repeat1.md"


def test_olmocr_results_split_heading_and_neighbour_tests_per_pdf() -> None:
    tests = [
        {
            "id": "1",
            "pdf": "tables/a.pdf",
            "type": "table",
            "top_heading": "Fee",
            "left_heading": None,
        },
        {"id": "2", "pdf": "tables/a.pdf", "type": "table", "up": "x"},
        {"id": "3", "pdf": "tables/b.pdf", "type": "table", "left_heading": "Row"},
        {"id": "4", "pdf": "tables/b.pdf", "type": "baseline"},
    ]
    counts = olmocr.result_counts(tests, {"1": True, "2": False, "3": False})
    assert counts["tables/a.pdf"] == {
        "tests": 2, "passed": 1, "heading": 1, "heading_passed": 1,
        "neighbour": 1, "neighbour_passed": 0,
    }  # fmt: skip
    assert counts["tables/b.pdf"]["heading"] == 1
    with pytest.raises(ValueError, match="no result"):
        olmocr.result_counts(tests, {"1": True, "2": False})
