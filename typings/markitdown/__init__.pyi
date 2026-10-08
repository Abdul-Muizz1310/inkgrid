"""Local type stub: only the parts of MarkItDown 0.1.8 the benchmark's adapter calls (spec 18)."""

class DocumentConverterResult:
    markdown: str

class MarkItDown:
    def __init__(self, *, enable_plugins: bool = ...) -> None: ...
    def convert(self, source: str) -> DocumentConverterResult: ...
