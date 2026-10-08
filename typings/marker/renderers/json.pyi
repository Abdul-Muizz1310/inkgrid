from marker.converters.pdf import Document, JSONOutput

class JSONRenderer:
    def __call__(self, document: Document) -> JSONOutput: ...
