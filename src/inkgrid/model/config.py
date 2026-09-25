"""Configuration values: `Profile` (geometry tolerances) and `Lexicon` (what a token is).

Both carry an `id` that the output's `Producer` records. A changed configuration must carry a new
id, so a document never claims a configuration that did not run.
"""

from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from inkgrid.model.base import Frozen

DEFAULT_PROFILE_ID = "default/1"
DEFAULT_LEXICON_ID = "generic/1"
DEFAULT_BULLETS = (
    "\u2022",
    "\u25aa",
    "\u25e6",
    "\u25a0",
    "\u25a1",
    "\u25cf",
    "\u25cb",
    "\u2023",
    "\u2043",
    "\u2219",
    "\u00b7",
    "\u2013",
    "\u2014",
    "-",
    "*",
)

Id = Annotated[str, Field(min_length=1)]
Ratio = Annotated[float, Field(gt=0)]
Share = Annotated[float, Field(gt=0, lt=1)]
Count = Annotated[int, Field(ge=1)]


def _changed_fields(model: Frozen) -> list[str]:
    fields = type(model).model_fields
    return [
        name for name, f in fields.items() if name != "id" and getattr(model, name) != f.default
    ]


class _Configuration(Frozen):
    id: Id

    @model_validator(mode="after")
    def _new_values_need_a_new_id(self) -> Self:
        default_id = type(self).model_fields["id"].default
        changed = _changed_fields(self)
        if self.id == default_id and changed:
            msg = (
                f"{', '.join(changed)} differ from the defaults, so the id must differ from "
                f"{default_id!r}"
            )
            raise ValueError(msg)
        return self


class Profile(_Configuration):
    """Geometry tolerances, as ratios of each document's own measurements (spec 04, section 1)."""

    id: Id = DEFAULT_PROFILE_ID
    line_overlap: Share = 0.5
    fragment_gap_em: Ratio = 1.0
    gutter_min_em: Ratio = 1.0
    column_min_lines: Count = 3
    prose_min_words: Ratio = 4.0
    paragraph_gap_ratio: Ratio = 1.75
    paragraph_gap_floor: Ratio = 2.0
    size_change_ratio: Ratio = 0.1
    heading_size_ratio: Ratio = 1.1
    heading_max_words: Count = 15
    heading_max_lines: Count = 2
    footnote_size_ratio: Ratio = 0.9
    furniture_share: Share = 0.4
    furniture_band: Share = 0.1
    furniture_x_tol: Ratio = 3.0
    long_document_pages: Count = 8

    @classmethod
    def default(cls) -> Self:
        """The default profile, `default/1`."""
        return cls()


class Lexicon(_Configuration):
    """Token classes. It never decides structure (spec 04, section 1)."""

    id: Id = DEFAULT_LEXICON_ID
    bullets: tuple[str, ...] = DEFAULT_BULLETS

    @classmethod
    def default(cls) -> Self:
        """The default lexicon, `generic/1`."""
        return cls()

    @field_validator("bullets")
    @classmethod
    def _bullets_are_single_characters(cls, bullets: tuple[str, ...]) -> tuple[str, ...]:
        if not bullets:
            msg = "bullets must not be empty"
            raise ValueError(msg)
        if any(len(b) != 1 for b in bullets):
            msg = "every bullet must be exactly one character"
            raise ValueError(msg)
        if len(set(bullets)) != len(bullets):
            msg = "bullets must not repeat"
            raise ValueError(msg)
        return bullets
