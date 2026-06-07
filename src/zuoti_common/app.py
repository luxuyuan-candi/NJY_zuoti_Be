from collections.abc import Iterable
from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings


def create_app(service_name: str, routers: Iterable[APIRouter]) -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=f"zuoti {service_name}",
        version="0.1.0",
        description="NJY zuoti FastAPI microservice",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz():
        return {"status": "ok", "service": service_name}

    @app.get("/readyz")
    def readyz():
        return {
            "status": "ready",
            "service": service_name,
            "env": settings.app_env,
        }

    for router in routers:
        app.include_router(router)

    return app
