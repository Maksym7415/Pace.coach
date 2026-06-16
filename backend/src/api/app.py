"""FastAPI application factory."""
import logging
import os

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from src.core.config import APP_ENV
from src.core.responses import legacy_error_response, success_json
from src.modules.coaching.router import router as coaching_router
from src.modules.gear_track.router import router as gear_track_router
from src.modules.identity.router import router as identity_router
from src.modules.recovery.router import router as recovery_router
from src.modules.training.router import router as training_router
from src.modules.third_party.strava.router import router as strava_router

LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("coach_app.api")


def create_app() -> FastAPI:
    app = FastAPI(title="Coach App API", version="0.1.0")

    _frontend_origin = os.environ.get("FRONTEND_WEB_ORIGIN")
    if APP_ENV.lower() == "development":
        dev_origins = [
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ]
        if _frontend_origin:
            dev_origins.append(_frontend_origin)
        allow_origins = dev_origins
    elif _frontend_origin:
        allow_origins = [_frontend_origin]
    else:
        allow_origins = []

    if allow_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=allow_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            allow_headers=["Authorization", "Content-Type"],
        )

    @app.get("/api/health")
    def health():
        return success_json({"status": "ok"})

    app.include_router(identity_router)
    app.include_router(gear_track_router)
    app.include_router(strava_router)
    app.include_router(coaching_router)
    app.include_router(recovery_router)
    app.include_router(training_router)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return legacy_error_response(request, exc)

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 404:
            return JSONResponse(
                status_code=404,
                content={"success": False, "error": "Endpoint not found"},
            )
        return JSONResponse(status_code=exc.status_code, content={"success": False, "error": exc.detail})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception("Internal server error")
        return JSONResponse(
            status_code=500,
            content={"success": False, "error": "Internal server error"},
        )

    return app


app = create_app()
