"""Error and validation models."""

from typing import Literal
from pydantic import BaseModel, Field


class ErrorLog(BaseModel):
    """Error information with self-healing support."""

    file_path: str
    line_number: int | None = None
    column: int | None = None
    error_type: str
    message: str
    traceback_snippet: str
    suggested_fix: str | None = Field(
        default=None,
        description="LLM-generated fix suggestion"
    )


ErrorType = Literal["syntax", "import", "runtime", "test", "lint"]
