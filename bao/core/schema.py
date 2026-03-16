"""Output schema (Pydantic)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Table(BaseModel):
    model_config = ConfigDict(extra="forbid")
    content: str
    caption: str | None = None


class Figure(BaseModel):
    model_config = ConfigDict(extra="forbid")
    caption: str | None = None
    path: str | None = None
    description: str | None = None


class Lesson(BaseModel):
    model_config = ConfigDict(extra="forbid")
    lessonTitle: str
    type: str
    summary: str
    file: str
    equations: list[str] | None = None
    tables: list[Table] | None = None
    figures: list[Figure] | None = None


class Chapter(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    description: str
    lessons: list[Lesson] = Field(default_factory=list)


class PdfToJsonRoot(BaseModel):
    model_config = ConfigDict(extra="forbid")
    chapter: Chapter


def validate_pdf_to_json(data: dict[str, Any]) -> PdfToJsonRoot:
    return PdfToJsonRoot.model_validate(data)


def export_json_schema() -> dict[str, Any]:
    return PdfToJsonRoot.model_json_schema()
