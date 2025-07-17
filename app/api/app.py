from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.openapi.utils import get_openapi
from fastapi.responses import ORJSONResponse

from app.api import router
from app.api.utils import find_check_subclasses, resolve_path
from app.checks.base import Check
from app.checks.periodic import run_checks
from app.config import Config

CHECKS_DIR = "app/checks"


def custom_openapi(app: FastAPI):
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="NodeWatch Handlers",
        version="1.0.0",
        description="This is the first version of the nodewatch service",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    app = FastAPI(
        docs_url='/nodewatch/openapi',
        openapi_url='/nodewatch/openapi.json',
        default_response_class=ORJSONResponse,
    )

    # Сохраняем настройки в app.state
    app.state.config = Config()

    # доступные проверки храним в app.state.checks
    if getattr(app.state.config, 'checks', None) is None:
        app.state.checks = {}
    checks_in_config = {check.name: check for check in app.state.config.checks}

    check_services_with_cfg = {}
    for check_class in find_check_subclasses(resolve_path(CHECKS_DIR), Check):
        try:
            check_services_with_cfg[check_class.name] = check_class(
                app.state.config.collector,
                checks_in_config[check_class.name].config,
                checks_in_config[check_class.name].metadata,
                checks_in_config[check_class.name].timeout
            )
        except KeyError:
            continue

    app.state.checks = check_services_with_cfg

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # STARTUP
        fi_service = app.state.checks.get('file_integrity')
        if fi_service:
            fi_service_afick_throttler = fi_service.afick_service.throttler
            await fi_service_afick_throttler.start_workers()

        await run_checks(app.state.config.checks, app.state.checks)

        yield

        # SHUTDOWN
        fi_service = app.state.checks.get('file_integrity')
        if fi_service:
            fi_service_afick_throttler = fi_service.afick_service.throttler
            fi_service_afick_throttler.shutdown()

    app.openapi = lambda: custom_openapi(app)

    app.include_router(router.router, prefix='/nodewatch/v1alpha1')
    return app
