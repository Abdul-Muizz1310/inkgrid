from pathlib import Path

from docling.datamodel.base_models import ConversionStatus, InputFormat

class DoclingDocument:
    def export_to_dict(self) -> dict[str, object]: ...

class ConversionResult:
    status: ConversionStatus
    document: DoclingDocument

class DocumentConverter:
    def __init__(self) -> None: ...
    def initialize_pipeline(self, format: InputFormat) -> None: ...
    def convert(self, source: Path | str) -> ConversionResult: ...
