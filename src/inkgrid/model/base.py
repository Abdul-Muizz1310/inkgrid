"""The shared base model and the quantized coordinate type."""

from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict

from inkgrid.model.geometry import quantize

Coord = Annotated[float, AfterValidator(quantize)]
"""A coordinate or length in PDF points, rounded to 0.01 at validation."""


class Frozen(BaseModel):
    """Base of every inkgrid model: immutable, strict, closed to unknown fields."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        serialize_by_alias=True,
        validate_by_alias=True,
        validate_by_name=True,
    )
