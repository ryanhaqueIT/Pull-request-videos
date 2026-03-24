"""FastAPI application entry point."""

import logging
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from config.settings import load_settings
from routers import agent, control, health, video
from services.control_plane import ControlPlaneService

settings = load_settings()


def setup_logging() -> None:
    """Configure structured JSON logging."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )
    logging.basicConfig(level=settings.log_level, format="%(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application startup and shutdown."""
    setup_logging()
    app.state.control_plane = ControlPlaneService(settings)
    logger = structlog.get_logger()
    logger.info("application_started", host=settings.host, port=settings.port)
    yield
    logger.info("application_stopped")


app = FastAPI(
    title="PR Video Generator",
    description="Automated PR demo video generation pipeline",
    version="0.1.0",
    lifespan=lifespan,
)

# Initialize control plane eagerly so it's available in tests (lifespan may not run)
app.state.control_plane = ControlPlaneService(settings)

app.include_router(health.router)
app.include_router(video.router)
app.include_router(agent.router)
app.include_router(control.router)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint — redirect to docs."""
    return {
        "service": "PR Video Agent",
        "version": "0.2.0",
        "docs": "/docs",
        "health": "/health",
    }


@app.middleware("http")
async def add_correlation_id(request: Request, call_next: Any) -> Any:
    """Add correlation_id to every request for tracing."""
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.exception_handler(404)
async def not_found_handler(request: Request, exc: Any) -> JSONResponse:
    """Return structured 404 with correlation_id."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    return JSONResponse(
        status_code=404,
        content={
            "error": "Not Found",
            "detail": f"Path {request.url.path} not found",
            "correlation_id": correlation_id,
        },
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Any) -> JSONResponse:
    """Return structured 500 with correlation_id."""
    correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))
    logger = logging.getLogger(__name__)
    logger.error(
        "Internal server error",
        extra={"correlation_id": correlation_id, "error": str(exc)},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "correlation_id": correlation_id,
        },
    )
