import logging
from functools import lru_cache
from typing import Optional

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
    time: Optional[str] = None  # время сохранения кеша
    count: int  # количество изменений


class Afick:
    def __init__(self, throttler: Throttler, afick_wrapper: AfickWrapper):
        self.throttler = throttler
        self.afick_wrapper = afick_wrapper
        logger.debug("Afick service is running.")

    async def run(self, timeout: float) -> Optional[AfickResult]:
        logger.debug(f"running afick with timeout: {timeout}")
        try:
            afick_result = await self.throttler.run_task(self._call_afick_with_result, timeout)
        except QueueIsFullException:
            raise AfickInternalError("task queue is full, please wait")
        except Exception as e:
            raise AfickInternalError(f"task failed with error: {str(e)}")

        if afick_result is None:
            raise AfickInternalError(f"the task was not completed on time: {timeout}")

        return AfickResult(**afick_result)

    def _call_afick_with_result(self, timeout) -> dict:
        """
        Запрашиваем afick проверку и дожидаемся результата без кэширования.
        Метод вызывается через self.throttler
        """
        try:
            afick_task_run_result = self.afick_wrapper.compare()
        except (Exception, SystemExit):
            logger.exception("afick task call error")
            raise AfickInternalError
        return afick_task_run_result


afick_service_instance = Afick(
    throttler=Throttler(max_concurrent_tasks=MAX_CONCURRENT_RUNS),
    afick_wrapper=AfickWrapper(timeout=AFICK_TIMEOUT)
)


@lru_cache()
def get_afick_service() -> Afick:
    return afick_service_instance
