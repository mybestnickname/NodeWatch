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

    app.openapi = lambda: custom_openapi(app)

    app.include_router(router.router, prefix='/nodewatch/v1alpha1')
    return app
