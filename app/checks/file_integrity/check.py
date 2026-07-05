import datetime as dt
import logging

from pydantic import ValidationError

from app.checks.base import Check
from app.checks.file_integrity.config import Config as FileIntegrityConfig
from app.checks.models import CheckStatus, Request, Response, Result
from app.cli_wrappers.afick.afick_wrapper import Result as AfickUtilityCallResult
from app.cli_wrappers.afick.runner import get_afick_service

logger = logging.getLogger(__name__)
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class FileIntegrityInternalError(Exception):
    pass


class FileIntegrityComponentInternalError(Exception):
    pass


class FileIntegrityCheck(Check[FileIntegrityConfig]):
    """Verify file-system integrity using the ``afick`` utility.

    A non-zero number of detected changes is reported as ``FAIL`` — for an
    integrity monitor any unexpected change is a finding, not a success.
    """

    name = "file_integrity"

    def __init__(self, config: FileIntegrityConfig | None, timeout: int) -> None:
        super().__init__(config, timeout)
        self.afick_service = get_afick_service()
        logger.debug("FileIntegrityCheck initialised (timeout=%ss).", timeout)

    async def startup(self) -> None:
        await self.afick_service.throttler.start_workers()

    async def shutdown(self) -> None:
        self.afick_service.throttler.shutdown()

    async def run(self, request: Request) -> Response:
        if self.config is None:
            comment = "FileIntegrityCheck config is empty"
            logger.error(comment)
            raise FileIntegrityInternalError(comment)

        # Overlay per-request arguments on top of the static config.
        try:
            effective_config = self.config.model_copy(update=request.arguments or {})
        except (ValueError, ValidationError) as exc:
            logger.exception("Invalid argument passed to file_integrity check")
            raise FileIntegrityInternalError(str(exc)) from exc

        start_time = dt.datetime.now(tz=dt.timezone.utc)
        try:
            afick_result = await self.afick_service.run(self.timeout)
        except Exception as exc:
            logger.exception("Failed to run afick task.")
            raise FileIntegrityComponentInternalError("Failed to run afick task.") from exc
        end_time = dt.datetime.now(tz=dt.timezone.utc)

        tool_ok = afick_result.status == AfickUtilityCallResult.afick_success
        if not tool_ok:
            status = CheckStatus.FAIL
            description = f"afick failed to run (status={afick_result.status})."
        elif afick_result.count > 0:
            status = CheckStatus.FAIL
            description = f"File integrity violated: {afick_result.count} change(s) detected by afick."
        else:
            status = CheckStatus.OK
            description = "File integrity verified: no changes detected by afick."

        result = Result(
            timestamp=end_time.strftime(TIMESTAMP_FORMAT),
            duration=(end_time - start_time).total_seconds(),
            status=status,
            description=description,
        )

        trigger = "on user request" if request.manual else "on schedule"
        log = logger.error if status == CheckStatus.FAIL else logger.info
        log("File integrity check executed %s. %s", trigger, description)

        return Response(
            name=request.name,
            arguments=effective_config.model_dump(),
            result=result,
            manual=request.manual,
            nowait=request.nowait,
        )
