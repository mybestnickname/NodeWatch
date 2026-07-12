import datetime as dt
import logging
import shutil

from pydantic import ValidationError

from app.checks.base import Check
from app.checks.fs_free_space.config import Config as FsFreeSpaceConfig
from app.checks.models import CheckStatus, Request, Response, Result

logger = logging.getLogger(__name__)
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class FsFreeSpaceInternalError(Exception):
    pass


class FsFreeSpaceCheck(Check[FsFreeSpaceConfig]):
    """Check that a mount point has enough free disk space.

    Fails when the free space drops below ``min_free_percent`` (and, if set,
    below ``min_free_bytes``).
    """

    name = "fs_free_space"

    def __init__(self, config: FsFreeSpaceConfig | None, timeout: int) -> None:
        super().__init__(config, timeout)
        logger.debug("FsFreeSpaceCheck initialised (timeout=%ss).", timeout)

    async def run(self, request: Request) -> Response:
        if self.config is None:
            comment = "FsFreeSpaceCheck config is empty"
            logger.error(comment)
            raise FsFreeSpaceInternalError(comment)

        try:
            cfg = self.config.model_copy(update=request.arguments or {})
        except (ValueError, ValidationError) as exc:
            logger.exception("Invalid argument passed to fs_free_space check")
            raise FsFreeSpaceInternalError(str(exc)) from exc

        start_time = dt.datetime.now(tz=dt.timezone.utc)
        try:
            usage = shutil.disk_usage(cfg.path)
        except OSError as exc:
            logger.exception("Failed to read disk usage for %s", cfg.path)
            raise FsFreeSpaceInternalError(str(exc)) from exc
        end_time = dt.datetime.now(tz=dt.timezone.utc)

        free_percent = (usage.free / usage.total * 100) if usage.total else 0.0
        enough_percent = free_percent >= cfg.min_free_percent
        enough_bytes = cfg.min_free_bytes is None or usage.free >= cfg.min_free_bytes

        if enough_percent and enough_bytes:
            status = CheckStatus.OK
            description = f"{cfg.path}: {free_percent:.1f}% free ({usage.free} bytes)."
        else:
            status = CheckStatus.FAIL
            description = (
                f"{cfg.path}: low disk space — {free_percent:.1f}% free "
                f"({usage.free} bytes), threshold {cfg.min_free_percent}%."
            )

        result = Result(
            timestamp=end_time.strftime(TIMESTAMP_FORMAT),
            duration=(end_time - start_time).total_seconds(),
            status=status,
            description=description,
        )

        log = logger.error if status == CheckStatus.FAIL else logger.info
        log("Free space check executed for %s. %s", cfg.path, description)

        return Response(
            name=request.name,
            arguments=cfg.model_dump(),
            result=result,
            manual=request.manual,
            nowait=request.nowait,
        )
