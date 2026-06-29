import logging
from functools import lru_cache

from pydantic import BaseModel

from app.cli_wrappers.afick.afick_wrapper import AfickWrapper
from app.cli_wrappers.throttler import QueueIsFullException, Throttler

logger = logging.getLogger(__name__)
MAX_CONCURRENT_RUNS = 2
AFICK_TIMEOUT = 30


class AfickInternalError(Exception):
    pass


class AfickResult(BaseModel):
    status: int
    time: str | None = None  # cache save time
    count: int  # number of detected changes


class Afick:
    def __init__(self, throttler: Throttler, afick_wrapper: AfickWrapper) -> None:
        self.throttler = throttler
        self.afick_wrapper = afick_wrapper
        logger.debug("Afick service initialised.")

    async def run(self, timeout: float) -> AfickResult:
        logger.debug("Running afick with timeout: %s", timeout)
        try:
            afick_result = await self.throttler.run_task(self._call_afick_with_result, timeout=timeout)
        except QueueIsFullException as exc:
            raise AfickInternalError("task queue is full, please wait") from exc
        except Exception as exc:
            raise AfickInternalError(f"task failed with error: {exc}") from exc

        if afick_result is None:
            raise AfickInternalError(f"the task was not completed within {timeout}s")

        return AfickResult(**afick_result)

    def _call_afick_with_result(self) -> dict:
        """Run an afick comparison and return the parsed result (no caching).

        Invoked through :class:`Throttler` so it runs in the thread pool.
        """
        try:
            return self.afick_wrapper.compare()
        except (Exception, SystemExit) as exc:
            logger.exception("afick task call error")
            raise AfickInternalError(str(exc)) from exc


afick_service_instance = Afick(
    throttler=Throttler(max_concurrent_tasks=MAX_CONCURRENT_RUNS),
    afick_wrapper=AfickWrapper(timeout=AFICK_TIMEOUT),
)


@lru_cache
def get_afick_service() -> Afick:
    return afick_service_instance
