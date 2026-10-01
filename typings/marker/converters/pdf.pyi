class JSONOutput:
    def model_dump(self) -> dict[str, object]: ...

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
