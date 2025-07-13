import datetime as dt
import logging

from pydantic import ValidationError

from app.checks.base import Check
from app.checks.models import CheckStatus, Request, Response, Result
from app.cli_wrappers.afick.afick_wrapper import Result as AfickUtilityCallResult
from app.cli_wrappers.afick.runner import get_afick_service
from app.config import CheckConfig

logger = logging.getLogger(__name__)
TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%fZ"


class FileIntegrityInternalError(Exception):
    pass


class FileIntegrityComponentInternalError(Exception):
    pass


class FileIntegrityCheck(Check):
    name = "file_integrity"

    def __init__(
        self,
        config: CheckConfig,
        check_timeout: float,
    ):
        super().__init__(None)  # config = None
        logger.debug("FileIntegrityService is running.")
        self.config = config
        self.check_timeout = check_timeout
        self.afick_service = get_afick_service()

    async def run(self, check_req: Request) -> Response:
        if not self.config:
            comment = "FileIntegrityCheck config is empty"
            logger.error(comment)
            raise FileIntegrityInternalError(comment)

        # дополняем конфиг переданными аргументами
        try:
            updated_config = self.config.model_copy(update=check_req.arguments)
        except (ValueError, ValidationError) as e:
            logger.exception("wrong param in fi_check_args")
            raise FileIntegrityInternalError(str(e))

        fi_check_result = Result(
            timestamp=dt.datetime.now(tz=dt.timezone.utc).strftime(TIMESTAMP_FORMAT),
            duration=0,
            status=CheckStatus.FAIL,
            description="",
        )

        # AFICK
        afick_start_time_call = dt.datetime.now(tz=dt.timezone.utc)
        try:
            afick_result = await self.afick_service.run(self.check_timeout)
            afick_end_time_call = dt.datetime.now(tz=dt.timezone.utc)
            afick_duration_call = (afick_end_time_call - afick_start_time_call).total_seconds()
        except Exception:
            comment = "Failed to run afick task."
            logger.exception(comment)
            raise FileIntegrityComponentInternalError(comment)

        # timestamp = время окончания работы последнего компонента проверки
        fi_check_result.timestamp = afick_end_time_call.strftime(TIMESTAMP_FORMAT)
        # суммируем время в сек для каждой проверки
        fi_check_result.duration += afick_duration_call
        fi_check_result.status = CheckStatus.OK if (
            afick_result.status == AfickUtilityCallResult.afick_success
        ) else CheckStatus.FAIL
        fi_check_result.description += f"Количество изменений по afick: {afick_result.count}."

        if check_req.manual:
            logger_comment = (
                f"Проверка целостности файлов была выполнена по запросу пользователя. {fi_check_result.description}"
            )
        else:
            logger_comment = f"Проверка целостности файлов была выполнена. {fi_check_result.description}"

        if afick_result.count:
            logger.error(logger_comment)
        else:
            logger.info(logger_comment)

        return Response(
            name=check_req.name,
            arguments=updated_config.model_dump(),
            result=fi_check_result,
            manual=check_req.manual,
            nowait=check_req.nowait
        )
