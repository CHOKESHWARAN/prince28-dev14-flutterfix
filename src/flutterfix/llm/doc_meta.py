"""The record we want for every document of FlutterFix.

This class is a contract. The extraction prompt, the database and (from Week 3)
the search filters all rely on it: add a field freely, but rename or remove one
only on purpose.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

Short = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]
Values = Annotated[list[Short], Field(default_factory=list, max_length=8)]
Kind = Literal[
    "guideline", "rule", "notice", "list", "report", "faq", "form", "tutorial", "reference", "other"
]
ChangeType = Literal["breaking", "deprecation", "migration", "feature", "other"]


class DocMeta(BaseModel):
    model_config = ConfigDict(extra="forbid")  # an unknown key is an error, not a surprise

    doc_kind: Kind
    year: int | None = Field(default=None, ge=1950, le=2027)  # null when the document has none
    language: Literal["en", "ta", "hi", "other"]
    summary: str = Field(min_length=20, max_length=300)
    topics: Annotated[list[Short], Field(min_length=1, max_length=6)]

    # Product fields from project card
    page: Values
    widget_or_api: Values
    flutter_version: Values
    dart_version: Values
    change_type: Annotated[list[ChangeType], Field(default_factory=list, max_length=8)]

    @field_validator("topics")
    @classmethod
    def _tidy(cls, value: list[str]) -> list[str]:
        """Lowercase and without repeats, so 'Dengue' and 'dengue' are one topic."""
        return list(dict.fromkeys(topic.lower() for topic in value))
