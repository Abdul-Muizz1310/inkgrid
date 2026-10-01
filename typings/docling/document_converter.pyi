from pathlib import Path

from docling.datamodel.base_models import ConversionStatus, InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

class DoclingDocument:
    def export_to_dict(self) -> dict[str, object]: ...

class ConversionResult:
    status: ConversionStatus
    document: DoclingDocument

class PdfFormatOption:
    def __init__(self, *, pipeline_options: PdfPipelineOptions) -> None: ...

class DocumentConverter:
    def __init__(
        self, format_options: dict[InputFormat, PdfFormatOption] | None = None
    ) -> None: ...
    def initialize_pipeline(self, format: InputFormat) -> None: ...
    def convert(self, source: Path | str) -> ConversionResult: ...
