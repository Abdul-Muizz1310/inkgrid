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
        json_schema_serialization_defaults_required=True,
        # Nested instances are validated again: a value altered with model_copy(update=...) cannot
        # slip into another model, and a subclass instance cannot pose as its parent type.
        revalidate_instances="always",
    )
