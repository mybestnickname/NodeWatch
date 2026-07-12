
from pydantic import BaseModel, Field


class Config(BaseModel):
    """Options for the free-disk-space check."""

    path: str = Field("/", description="Mount point or path to inspect")
    min_free_percent: float = Field(
        10.0, ge=0, le=100, description="Minimum acceptable free space, percent of total"
    )
    min_free_bytes: int | None = Field(
        None, ge=0, description="Optional absolute minimum of free bytes"
    )
