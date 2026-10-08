from marker.converters.pdf import Document

class MarkdownOutput:
    markdown: str

class MarkdownRenderer:
    def __call__(self, document: Document) -> MarkdownOutput: ...
