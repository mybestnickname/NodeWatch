import asyncio
import logging
import random

from app.checks.base import Check as CheckService
from app.checks.models import CheckStatus, Request, Response
from app.config import Check

logger = logging.getLogger(__name__)


def _log_result(response: Response) -> None:
    result = response.result
    if result is None:
        logger.error("Check %s finished without a result. Details: %s", response.name, response.model_dump())
        return
    if result.status == CheckStatus.OK:
        logger.info("Check %s completed successfully. Result: %s", response.name, result.model_dump())
    else:
        logger.error("Check %s finished with errors. Result: %s", response.name, result.model_dump())


async def periodic_check_runner(check: Check, check_service: CheckService) -> None:
    """Run a single check forever on its configured interval (with jitter)."""
    await asyncio.sleep(random.uniform(0, check.jitter))
    loop = asyncio.get_running_loop()
    while True:
        logger.info("Running scheduled check: %s", check.name)
        start_time = loop.time()
        try:
            response = await check_service.run(Request(name=check.name))
            _log_result(response)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Error occurred while running scheduled check %s", check.name)

        elapsed = loop.time() - start_time
        delay = max(0.0, (check.interval + random.uniform(0, check.jitter)) - elapsed)
        logger.info("Check %s took %.2fs. Next run in %.2fs.", check.name, elapsed, delay)
        await asyncio.sleep(delay)


async def run_checks(checks: list[Check], check_services: dict[str, CheckService]) -> list[asyncio.Task]:
    """Start a background task for every check with a non-zero interval."""
    logger.info("Starting periodic checks.")
    tasks: list[asyncio.Task] = []
    for check in checks:
        if check.interval == 0:
            continue
        check_service = check_services.get(check.name)
        if check_service is None:
            logger.error("No service found for scheduled check %s.", check.name)
            continue
        tasks.append(asyncio.create_task(periodic_check_runner(check, check_service)))
    return tasks
