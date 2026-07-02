from abc import ABC, abstractmethod
from typing import ClassVar, Generic, TypeVar

from pydantic import BaseModel

from app.checks.models import Request, Response

ConfigT = TypeVar("ConfigT", bound=BaseModel)


class Check(ABC, Generic[ConfigT]):
    """Base class for all checks.

    A concrete check declares a unique ``name`` (matching a field on
    ``CheckConfig``), is parameterised by its typed config model, receives that
    config plus a per-run ``timeout`` and implements :meth:`run`. Optional
    :meth:`startup`/:meth:`shutdown` hooks let a check manage background
    resources tied to the application lifespan.
    """

    name: ClassVar[str]

    def __init__(self, config: ConfigT | None, timeout: int) -> None:
        self.config = config
        self.timeout = timeout

    async def startup(self) -> None:
        """Initialise background resources. Called once on application startup."""

    async def shutdown(self) -> None:
        """Release background resources. Called once on application shutdown."""

    @abstractmethod
    async def run(self, request: Request) -> Response:
        """Execute the check and return its result."""
