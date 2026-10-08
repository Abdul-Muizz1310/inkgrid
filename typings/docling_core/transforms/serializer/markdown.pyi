from docling.document_converter import DoclingDocument
from docling_core.transforms.serializer.html import HTMLTableSerializer

class SerializationResult:
    text: str

class MarkdownDocSerializer:
    def __init__(self, *, doc: DoclingDocument, table_serializer: HTMLTableSerializer) -> None: ...
    def serialize(self) -> SerializationResult: ...
