from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Request(BaseModel):
    name: str
    arguments: dict[str, Any] | None = None
    # Whether the run was triggered manually (via the API) or by the scheduler.
    manual: bool = False
    # When True the API returns immediately and the check runs in the background.
    nowait: bool = False


class Config(BaseModel):  # must be subclassed by each check
    pass


class CheckStatus(str, Enum):
    OK = "OK"
    FAIL = "FAIL"


class Result(BaseModel):
    timestamp: str = Field(..., description="Check completion time (ISO-8601, UTC)")
    duration: float = Field(..., description="Check duration in seconds")
    status: CheckStatus = Field(..., description="Check result")
    description: str = Field(..., description="Human-readable comment")


class Response(BaseModel):
    name: str
    arguments: dict[str, Any] | None = None
    result: Result | None = None
    manual: bool = False
    nowait: bool = False
