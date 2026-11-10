from fastapi import FastAPI

from food_allergy_tracker.config import get_settings
from food_allergy_tracker.routers import health, items


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, debug=settings.debug)
    app.include_router(health.router)
    app.include_router(items.router)
    return app


app = create_app()