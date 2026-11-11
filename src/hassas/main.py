from fastapi import FastAPI

from hassas import health
from hassas.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.include_router(health.router)
    return app


app = create_app()
