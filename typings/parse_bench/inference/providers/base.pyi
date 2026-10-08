from typing import Any

from parse_bench.schemas.pipeline import PipelineSpec
from parse_bench.schemas.pipeline_io import InferenceRequest, InferenceResult, RawInferenceResult

class Provider:
    base_config: dict[str, Any]
    def __init__(self, provider_name: str, base_config: dict[str, Any] | None = None) -> None: ...
    def run_inference(
        self, pipeline: PipelineSpec, request: InferenceRequest
    ) -> RawInferenceResult: ...
    def normalize(self, raw_result: RawInferenceResult) -> InferenceResult: ...
