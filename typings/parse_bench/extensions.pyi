from collections.abc import Callable

from parse_bench.inference.providers.base import Provider
from parse_bench.schemas.pipeline import PipelineSpec

def register_provider(name: str) -> Callable[[type[Provider]], type[Provider]]: ...
def register_pipeline(spec: PipelineSpec) -> None: ...
