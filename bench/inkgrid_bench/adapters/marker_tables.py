"""marker's tables from the text layer alone (docs/specs/15-heavy-competitors.md section 1).

Its models are loaded before the first document's clock starts.
"""

from collections.abc import Callable, Sequence
from pathlib import Path

from marker.config.parser import ConfigParser
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict

from inkgrid_bench.adapters._cli import batch
from inkgrid_bench.heavy import marker_tables
from inkgrid_bench.tables import NPage, NTable

OPTIONS: dict[str, object] = {
    "output_format": "json",
    "disable_ocr": True,
    "disable_image_extraction": True,
    "disable_tqdm": True,
}


def converter() -> PdfConverter:
    """Marker's converter on the text layer, JSON out, its models loaded."""
    parser = ConfigParser(OPTIONS)
    return PdfConverter(
        config=parser.generate_config_dict(),
        artifact_dict=create_model_dict(),
        processor_list=parser.get_processors(),
        renderer=parser.get_renderer(),
    )


def reader(conv: PdfConverter) -> Callable[[Path, Sequence[NPage]], list[NTable]]:
    """One document's tables by `conv`."""

    def read(pdf: Path, frames: Sequence[NPage]) -> list[NTable]:
        return marker_tables(conv(str(pdf)).model_dump(), frames)

    return read


if __name__ == "__main__":
    raise SystemExit(batch(reader(converter())))
