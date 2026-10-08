class JSONOutput:
    def model_dump(self) -> dict[str, object]: ...

class Document: ...  # marker's built document, opaque to the adapter

class PdfConverter:
    def __init__(
        self,
        artifact_dict: dict[str, object],
        processor_list: list[str] | None = None,
        renderer: str | None = None,
        llm_service: str | None = None,
        config: dict[str, object] | None = None,
    ) -> None: ...
    def __call__(self, filepath: str) -> JSONOutput: ...
    def build_document(self, filepath: str) -> Document: ...
    def resolve_dependencies[T](self, cls: type[T]) -> T: ...
