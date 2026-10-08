"""marker's tables and page from the text layer alone (specs 15 and 18).

Its models are loaded before the first document's clock starts.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.renderers.json import JSONRenderer
from marker.renderers.markdown import MarkdownRenderer

from inkgrid_bench.adapters._cli import batch
from inkgrid_bench.heavy import marker_tables
from inkgrid_bench.tables import NPage, Output

OPTIONS: dict[str, object] = {
    "output_format": "json",
    "disable_ocr": True,
    "disable_image_extraction": True,
    "disable_tqdm": True,
}


def converter() -> PdfConverter:
    """Marker's converter on the text layer, its models loaded; Markdown keeps tables as HTML."""
    parser = ConfigParser(OPTIONS)
    return PdfConverter(
        config={**parser.generate_config_dict(), "html_tables_in_markdown": True},
        artifact_dict=create_model_dict(),
        processor_list=parser.get_processors(),
        renderer=parser.get_renderer(),
    )


def reader(conv: PdfConverter) -> Callable[[Path, Sequence[NPage]], Output]:
    """One document's tables and Markdown by `conv`, both rendered from one built document.

    marker's Markdown renderer leaves out page headers and footers by default.
    """

    def read(pdf: Path, frames: Sequence[NPage]) -> Output:
        document = conv.build_document(str(pdf))
        tables = marker_tables(
            conv.resolve_dependencies(JSONRenderer)(document).model_dump(), frames
        )
        markdown = conv.resolve_dependencies(MarkdownRenderer)(document).markdown
        return Output(tuple(tables), markdown)

    return read


if __name__ == "__main__":
    raise SystemExit(batch(reader(converter())))
