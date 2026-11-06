from typing import Literal

from pydantic import BaseModel, Field


class Finding(BaseModel):
    code: Literal[
        "missing_values",
        "blank_values",
        "placeholder_values",
        "duplicate_rows",
        "potential_outliers",
    ]
    column: str | None
    count: int = Field(ge=0)
    message: str