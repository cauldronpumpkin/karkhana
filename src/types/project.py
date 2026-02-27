"""Project structure models."""

from typing import Any, Literal
from pydantic import BaseModel, Field


class ComponentSpec(BaseModel):
    """Specification for a single component/file."""

    name: str
    path: str
    language: Literal["python", "javascript", "typescript", "json", "markdown"]
    purpose: str
    dependencies: list[str] = Field(default_factory=list)


class FileTree(BaseModel):
    """Complete project file tree structure."""

    root_dir: str = Field(default="project")
    files: dict[str, list[ComponentSpec]] = Field(
        default_factory=dict,
        description="Directory -> list of files"
    )
    backend: dict[str, Any] | None = None
    frontend: dict[str, Any] | None = None


class TechStack(BaseModel):
    """Technology stack specification."""

    frontend: dict[str, Any]
    backend: dict[str, Any]
    database: str
    testing: list[str]
