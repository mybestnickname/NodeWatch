from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.responses import ORJSONResponse


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


def create_app() -> FastAPI:  # TODO: start config
    app = FastAPI(
        docs_url='/nodewatch/openapi',
        openapi_url='/nodewatch/openapi.json',
        default_response_class=ORJSONResponse,
    )

    # Сохраняем настройки в app.state
    # TODO Config
    # config=None
    # app.state.config = config

    # @app.on_event("startup") # TODO: lifespan event handlers
    # async def startup_event():
    #     # Запуск воркеров Throttler-а внутри сервисов или другие необходимые процессы
    #     pass

    # @app.on_event("shutdown") # TODO: lifespan event handlers
    # async def shutdown_event():
    #     # Освобождение ресурсов
    #     pass

    app.openapi = lambda: custom_openapi(app)

    # app.include_router(router.router, prefix='/nodewatch/v1alpha1')
    return app
