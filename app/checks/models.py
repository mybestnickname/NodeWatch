from pydantic import BaseModel, Enum, Field
from typing import Dict, Any, Optional


class Request(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]] = None
    manual: bool
    nowait: bool


class Config(BaseModel):  # must be subclassed
    pass


class CheckStatus(str, Enum):
    OK = "OK"
    FAIL = "FAIL"


class Result(BaseModel):
    timestamp: str = Field(..., description="Check completion time")
    duration: int = Field(..., description="Check duration in seconds")
    status: CheckStatus = Field(..., description="Check result")
    description: str = Field(..., description="Comment for the user")


class Response(BaseModel):
    name: str
    arguments: Optional[Dict[str, Any]]
    result: Optional[Result]
    manual: bool
    nowait: bool
