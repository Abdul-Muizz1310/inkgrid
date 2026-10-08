from datetime import datetime
from typing import Any

from parse_bench.schemas.parse_output import ParseOutput
from parse_bench.schemas.pipeline import PipelineSpec

class InferenceRequest:
    example_id: str
    source_file_path: str
    product_type: str

class RawInferenceResult:
    request: InferenceRequest
    pipeline_name: str
    product_type: str
    raw_output: dict[str, Any]
    started_at: datetime
    completed_at: datetime
    latency_in_ms: int
    def __init__(
        self,
        *,
        request: InferenceRequest,
        pipeline: PipelineSpec,
        pipeline_name: str,
        product_type: str,
        raw_output: dict[str, Any],
        started_at: datetime,
        completed_at: datetime,
        latency_in_ms: int,
    ) -> None: ...

class InferenceResult:
    def __init__(
        self,
        *,
        request: InferenceRequest,
        pipeline_name: str,
        product_type: str,
        raw_output: dict[str, Any],
        output: ParseOutput,
        started_at: datetime,
        completed_at: datetime,
        latency_in_ms: int,
    ) -> None: ...
