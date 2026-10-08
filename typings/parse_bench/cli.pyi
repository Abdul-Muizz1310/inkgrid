class BenchCLI:
    def __init__(self) -> None: ...
    def run(
        self,
        pipeline: str,
        input_dir: str | None = ...,
        output_dir: str | None = ...,
        group: str | None = ...,
        open_report: bool = ...,
        max_concurrent: int = ...,
    ) -> int: ...
