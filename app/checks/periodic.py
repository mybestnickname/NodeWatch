import asyncio
import logging
import random
from typing import List

from app.checks.models import CheckStatus, Request
from app.config import Check

logger = logging.getLogger(__name__)


async def periodic_check_runner(check: Check, check_service):
    start_delay = random.uniform(0, check.jitter)
    logger.info(f"{check.name} check will be runned in {start_delay} sec")
    await asyncio.sleep(start_delay)
    while True:
        logger.info(f"Running check: {check.name}.")
        start_time = asyncio.get_running_loop().time()
        try:
            check_resp = await check_service.run(Request(name=check.name, nowait=False, manual=False,))
        except Exception:
            logger.error(f"Error occurred for {check.name} check.", exc_info=1)
            continue

        check_result = getattr(check_resp, "result", None)
        if check_result:
            if check_result.status == CheckStatus.OK:
                logger.info(f"Check {check_resp.name} has been successfully completed. Result: {check_result.dict()}")
            else:
                logger.error(f"Check {check_resp.name} finished with errors. Result: {check_result.dict()}")
        else:
            logger.error(f"Check {check_resp.name} finished with errors without result. Details: {check_resp.dict()}")

        elapsed_time = asyncio.get_running_loop().time() - start_time
        delay = max(0, (check.interval + random.uniform(0, check.jitter)) - elapsed_time)
        logger.info(
            f"Elapsed time for {check.name}: {elapsed_time:.2f} seconds. Sleeping for {delay:.2f} seconds."
        )
        await asyncio.sleep(delay)


async def run_checks(checks: List[Check], check_services: dict):
    logger.info("Starting periodic checks.")
    runned_tasks = []
    for check in checks:
        if check.interval != 0:
            try:
                check_service = check_services[check.name]
            except KeyError:
                logger.error(f"Failed to found service for {check.name} check.")
                continue
            runned_tasks.append(asyncio.create_task(periodic_check_runner(check, check_service)))
    return runned_tasks
