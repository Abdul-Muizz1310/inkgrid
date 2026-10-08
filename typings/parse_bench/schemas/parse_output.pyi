class PageIR:
    def __init__(self, *, page_index: int, markdown: str) -> None: ...

class ParseOutput:
    def __init__(
        self,
        *,
        task_type: str,
        example_id: str,
        pipeline_name: str,
        pages: list[PageIR],
        markdown: str,
    ) -> None: ...
