# app/schemas/sentence_import.py
from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.config import settings
from app.schemas.tagging import Topic


class PreviewRow(BaseModel):
    """One parsed spreadsheet row, as shown in the review modal. Nothing is saved."""

    row_number: int  # the real spreadsheet row (header is row 1)
    de: str
    en: str
    topics: list[str]
    grammar_tag: str | None
    tagged: bool  # False: tagging failed or was skipped (not "tagged with nothing")
    issues: list[str]
    has_blocking_issue: bool


class ImportPreviewOut(BaseModel):
    rows: list[PreviewRow]


class ImportConfirmRow(BaseModel):
    """One row the client asks us to save. Never trusted: validated again here."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Same caps as SentenceCreate / SentenceUpdate (tests guard against drift).
    de: str = Field(..., min_length=1, max_length=2000)
    en: str = Field(..., min_length=1, max_length=2000)
    topics: list[Topic] = Field(default_factory=list)
    grammar_tag: str | None = Field(None, max_length=100)

    @field_validator("grammar_tag")
    @classmethod
    def blank_grammar_tag_is_none(cls, value: str | None) -> str | None:
        return value or None


class ImportConfirmIn(BaseModel):
    sentences: list[ImportConfirmRow] = Field(
        ..., min_length=1, max_length=settings.bulk_import_max_rows
    )
