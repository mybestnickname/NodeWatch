import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Request

from app.api.errors.http_errors import InternalError, UnprocessableEntityError
from app.checks.models import Request as CheckRunRequest
from app.checks.models import Response as CheckResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.post(
    "/check/",
    tags=["postruncheck"],
    response_model=Optional[CheckResponse],
    responses={
        200: {"description": "Task has been started.", },
        500: {"description": "Internal error.", },
        422: {"description": "Unprocessable Entity.", },
    },
)
async def post_run_check(
    params: CheckRunRequest,
    request: Request,
    background_tasks: BackgroundTasks
) -> Optional[CheckResponse]:
    logger.info(f"Received request to run check: {params.name} with arguments: {params.dict()}")
    if not params.manual:
        logger.info("'manual' set to True as the check was triggered by an api request.")
        params.manual = True
    try:
        if params.nowait:
            logger.info(f"Check {params.name} will run asynchronously in the background.")
            background_tasks.add_task(run_check_in_background, params, request)
            return CheckResponse(
                name=params.name,
                arguments=params.arguments,
                result=None,
                manual=params.manual,
                nowait=params.nowait
            )

        logger.info(f"Check {params.name} will run synchronously.")
        check_result = await request.app.state.checks[params.name].run(params)
    except KeyError as e:
        logger.error(f"Check {params.name} not found in available checks: {str(e)}")
        raise UnprocessableEntityError
    except Exception:
        logger.exception(f"Internal server error while running check {params.name}.")
        raise InternalError
    else:
        logger.info(f"Check {params.name} completed successfully. Result: {check_result}")
        return check_result


async def run_check_in_background(params: CheckRunRequest, request: Request):
    logger.info(f"Background execution started for check: {params.name} with arguments: {params.model_dump()}")
    try:
        result = await request.app.state.checks[params.name].run(params)
        logger.info(f"Background execution of check {params.name} completed. Result: {result}")
    except Exception:
        logger.exception(f"Error occurred during background execution of check {params.name}.")
