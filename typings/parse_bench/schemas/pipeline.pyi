from typing import Any

class PipelineSpec:
    pipeline_name: str
    def __init__(
        self, *, pipeline_name: str, provider_name: str, product_type: str, config: dict[str, Any]
    ) -> None: ...
