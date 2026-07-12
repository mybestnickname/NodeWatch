import logging

from fastapi import FastAPI
from fastapi.concurrency import asynccontextmanager
from fastapi.openapi.utils import get_openapi
from fastapi.responses import ORJSONResponse

from app.api import router
from app.api.utils import discover_checks
from app.checks.base import Check
from app.checks.periodic import run_checks
from app.config import Config, load_config

logger = logging.getLogger(__name__)


def _setup_logging() -> None:
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        )


def custom_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema
    app.openapi_schema = get_openapi(
        title="NodeWatch Handlers",
        version="1.0.0",
        description="Lightweight host-integrity monitoring agent.",
        routes=app.routes,
    )
    return app.openapi_schema


def _build_check_services(config: Config) -> dict[str, Check]:
    """Instantiate every discovered check that has a matching config entry.

    The config entry is resolved by convention: ``CheckConfig.<name>`` holds the
    typed config for the check whose ``name`` equals that field.
    """
    registry = discover_checks()
    checks_in_config = {check.name: check for check in config.checks}

    services: dict[str, Check] = {}
    for name, check_class in registry.items():
        check_cfg = checks_in_config.get(name)
        if check_cfg is None:
            logger.info("Check %s is available but not configured; skipping.", name)
            continue
        sub_config = getattr(check_cfg.config, name, None)
        services[name] = check_class(sub_config, check_cfg.timeout)
        logger.info("Registered check service: %s", name)
    return services


def create_app() -> FastAPI:
    _setup_logging()

    config = load_config()
    check_services = _build_check_services(config)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # STARTUP
        for service in app.state.checks.values():
            await service.startup()
        scheduled_tasks = await run_checks(app.state.config.checks, app.state.checks)

        yield

        # SHUTDOWN
        for task in scheduled_tasks:
            task.cancel()
        for service in app.state.checks.values():
            await service.shutdown()

    app = FastAPI(
        docs_url="/nodewatch/openapi",
        openapi_url="/nodewatch/openapi.json",
        default_response_class=ORJSONResponse,
        lifespan=lifespan,
    )

    app.state.config = config
    app.state.checks = check_services

    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]
    app.include_router(router.router, prefix="/nodewatch/v1alpha1")
    return app
