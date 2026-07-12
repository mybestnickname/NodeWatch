import logging

from fastapi import APIRouter, BackgroundTasks, Request

from app.api.errors.http_errors import InternalError, UnprocessableEntityError
from app.checks.models import Request as CheckRunRequest
from app.checks.models import Response as CheckResponse

router = APIRouter()

logger = logging.getLogger(__name__)


@router.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/checks", tags=["meta"])
async def list_checks(request: Request) -> list[dict[str, object]]:
    """List the checks configured on this node."""
    configured = {check.name: check for check in request.app.state.config.checks}
    return [
        {
            "name": name,
            "available": name in request.app.state.checks,
            "interval": configured[name].interval,
            "timeout": configured[name].timeout,
        }
        for name in configured
    ]


@router.post(
    "/check/",
    tags=["postruncheck"],
    response_model=CheckResponse | None,
    responses={
        200: {"description": "Task has been started."},
        500: {"description": "Internal error."},
        422: {"description": "Unprocessable Entity."},
    },
)
async def post_run_check(
    params: CheckRunRequest,
    request: Request,
    background_tasks: BackgroundTasks,
) -> CheckResponse | None:
    logger.info("Received request to run check: %s with arguments: %s", params.name, params.model_dump())

    if params.name not in request.app.state.checks:
        logger.error("Check %s not found in available checks.", params.name)
        raise UnprocessableEntityError

    # A check triggered through the API is, by definition, manual.
    params.manual = True

    try:
        if params.nowait:
            logger.info("Check %s will run asynchronously in the background.", params.name)
            background_tasks.add_task(run_check_in_background, params, request)
            return CheckResponse(
                name=params.name,
                arguments=params.arguments,
                result=None,
                manual=params.manual,
                nowait=params.nowait,
            )

        logger.info("Check %s will run synchronously.", params.name)
        check_result = await request.app.state.checks[params.name].run(params)
    except Exception as exc:
        logger.exception("Internal server error while running check %s.", params.name)
        raise InternalError from exc
    else:
        logger.info("Check %s completed. Result: %s", params.name, check_result)
        return check_result


async def run_check_in_background(params: CheckRunRequest, request: Request) -> None:
    logger.info("Background execution started for check: %s", params.name)
    try:
        result = await request.app.state.checks[params.name].run(params)
        logger.info("Background execution of check %s completed. Result: %s", params.name, result)
    except Exception:
        logger.exception("Error occurred during background execution of check %s.", params.name)
