"""ParseBench's own scoring of a tool's saved Markdown (docs/specs/18-ocr-benchmarks.md s. 4).

Runs inside parse-bench's pinned environment (1.0.4): `python -m
inkgrid_bench.scores.parsebench_driver DATA SAVED OUT GROUP PIPELINE`. It registers a provider that
returns, for each ParseBench example, the tool's Markdown saved as `SAVED/<example id, / as __>.md`
(an empty page when there is none), runs ParseBench's pipeline (inference, evaluation, report) on
the group, and leaves ParseBench's own evaluation report under OUT/PIPELINE.
"""

import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from parse_bench.cli import BenchCLI
from parse_bench.extensions import register_pipeline, register_provider
from parse_bench.inference.providers.base import Provider
from parse_bench.schemas.parse_output import PageIR, ParseOutput
from parse_bench.schemas.pipeline import PipelineSpec
from parse_bench.schemas.pipeline_io import InferenceRequest, InferenceResult, RawInferenceResult

from inkgrid_bench.scores.parsebench_names import saved_name


@register_provider("saved_markdown")
class SavedMarkdown(Provider):
    """The tool's page as the benchmark run saved it; nothing is parsed here."""

    def __init__(self, provider_name: str, base_config: dict[str, Any] | None = None) -> None:
        super().__init__(provider_name, base_config)
        self._folder = Path(str(self.base_config["folder"]))

    def run_inference(
        self, pipeline: PipelineSpec, request: InferenceRequest
    ) -> RawInferenceResult:
        """The saved page of the request's example, or an empty one."""
        started = datetime.now(UTC)
        path = self._folder / saved_name(request.example_id)
        text = path.read_text(encoding="utf-8") if path.is_file() else ""
        return RawInferenceResult(
            request=request,
            pipeline=pipeline,
            pipeline_name=pipeline.pipeline_name,
            product_type=request.product_type,
            raw_output={"markdown": text},
            started_at=started,
            completed_at=datetime.now(UTC),
            latency_in_ms=0,
        )

    def normalize(self, raw_result: RawInferenceResult) -> InferenceResult:
        """The page as ParseBench's one-page parse output."""
        text = str(raw_result.raw_output["markdown"])
        output = ParseOutput(
            task_type="parse",
            example_id=raw_result.request.example_id,
            pipeline_name=raw_result.pipeline_name,
            pages=[PageIR(page_index=0, markdown=text)],
            markdown=text,
        )
        return InferenceResult(
            request=raw_result.request,
            pipeline_name=raw_result.pipeline_name,
            product_type=raw_result.product_type,
            raw_output=raw_result.raw_output,
            output=output,
            started_at=raw_result.started_at,
            completed_at=raw_result.completed_at,
            latency_in_ms=raw_result.latency_in_ms,
        )


def main() -> int:
    """Score the saved Markdown in argv[2] on ParseBench's group argv[4]."""
    data, saved, out, group, pipeline = sys.argv[1:6]
    register_pipeline(
        PipelineSpec(
            pipeline_name=pipeline,
            provider_name="saved_markdown",
            product_type="parse",
            config={"folder": saved},
        )
    )
    return BenchCLI().run(
        pipeline=pipeline,
        input_dir=data,
        output_dir=out,
        group=group,
        open_report=False,
        max_concurrent=4,
    )


if __name__ == "__main__":
    raise SystemExit(main())
