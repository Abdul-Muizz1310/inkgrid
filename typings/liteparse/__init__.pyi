"""Local type stub: only the parts of LiteParse 2.15.1 the benchmark's adapter calls (spec 18)."""

class ParsedPage:
    markdown: str

class ParseResult:
    pages: list[ParsedPage]

class LiteParse:
    def __init__(
        self,
        *,
        ocr_enabled: bool | None = ...,
        output_format: str | None = ...,
        quiet: bool | None = ...,
    ) -> None: ...
    def parse(self, file_data: str) -> ParseResult: ...
