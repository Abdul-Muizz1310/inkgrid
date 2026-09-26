import pytest

import inkgrid
import pdf_factory
from inkgrid.model.document import Block, Definition, Footnote


def shown(blocks: tuple[Block, ...]) -> list[tuple[str, str]]:
    out = []
    for b in blocks:
        if b.kind == "furniture":
            continue
        if isinstance(b, Definition):
            out.append((b.kind, b.term))
        elif isinstance(b, Footnote):
            out.append((b.kind, b.label))
        else:
            out.append((b.kind, b.text.split()[0]))
    return out


def test_GP1_a_definitions_section_reads_as_definitions() -> None:
    doc = inkgrid.read(pdf_factory.definitions_section())
    assert shown(doc.blocks) == [
        ("heading", "Definitions"),
        ("definition", "\u201cABBO\u201d"),
        ("definition", "Admission Fee:"),
        ("definition", "Access"),
        ("definition", "Aggressor"),
        ("definition", "bp"),
        ("heading", "Fees"),
        ("paragraph", "\u201cFee\u201d"),
    ]


def test_NL9_a_legend_grid_reads_as_a_heading_a_definition_and_a_note() -> None:
    doc = inkgrid.read(pdf_factory.legend_grid())
    assert shown(doc.blocks) == [
        ("table", "Connection"),
        ("heading", "Legend"),
        ("definition", "Tier A"),
        ("footnote", "X2"),
    ]


@pytest.mark.parametrize("name", ["definitions_section", "legend_grid"])
def test_GP2_the_glossary_fixtures_read_into_valid_documents(name: str) -> None:
    assert name in pdf_factory.OPENABLE  # so RD1 and CP5 read them with every other fixture
    doc = inkgrid.read(pdf_factory.OPENABLE[name]())
    assert type(doc).model_validate_json(doc.model_dump_json()) == doc
