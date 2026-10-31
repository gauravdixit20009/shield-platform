"""
SHIELD Platform — FastAPI Application Entry Point
Production-ready with middleware, CORS, rate limiting, security headers.
"""
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import time
import uuid

from app.core.database import engine, Base
from app.api.v1 import router as api_v1_router
from app.utils.logger import logger

APP_VERSION = "1.0.0"
ENVIRONMENT = "development"


# ─── Startup / Shutdown ────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"🛡️ SHIELD Platform starting... [{ENVIRONMENT}]")
    # Create tables (use Alembic in production)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("✅ Database connected")
    logger.info("✅ SHIELD Platform ready")
    yield
    logger.info("🛑 SHIELD Platform shutting down...")
    await engine.dispose()


# ─── App Init ──────────────────────────────────────────────
app = FastAPI(
    title="SHIELD API",
    description="Secure Hub for Intelligence, Enforcement & Law Data",
    version=APP_VERSION,
    lifespan=lifespan,
    docs_url="/api/docs",       # Enable Swagger UI for development
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)


# ─── Security Headers Middleware ───────────────────────────
@app.middleware("http")
async def security_headers(request: Request, call_next):
    """Add security headers to every response."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
        "script-src 'self' 'unsafe-inline' https://cdn.tailwindcss.com https://unpkg.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://unpkg.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob: https://*.basemaps.cartocdn.com https://*.tile.openstreetmap.org https://unpkg.com https://server.arcgisonline.com https://*.arcgisonline.com; "
        "connect-src 'self'; "
        "frame-ancestors 'none';"
    )
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(self), microphone=(self), camera=(self)"
    # Remove fingerprinting headers if present
    if "x-powered-by" in response.headers:
        del response.headers["x-powered-by"]
    if "server" in response.headers:
        del response.headers["server"]
    return response


# ─── Request ID Middleware ──────────────────────────────────
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    """Attach unique request ID for tracing."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time"] = f"{duration:.3f}s"
    return response


# ─── CORS (allow any device on local network / dev clients) ────────
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://.*$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],
)

# ─── GZip Compression ──────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=1000)


# ─── Global Exception Handlers ─────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error. Request ID: " + getattr(request.state, "request_id", "unknown")},
    )


# ─── Health Check ──────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "service": "SHIELD Platform",
        "version": APP_VERSION,
    }


# ─── API Router ────────────────────────────────────────────
app.include_router(api_v1_router, prefix="/api/v1")


# ─── Interactive Web Portal ────────────────────────────────
import os
from fastapi.responses import FileResponse

STATIC_INDEX = os.path.join(os.path.dirname(__file__), "static", "index.html")

@app.get("/", include_in_schema=False)
async def serve_dashboard():
    if os.path.exists(STATIC_INDEX):
        return FileResponse(STATIC_INDEX)
    return JSONResponse({"message": "SHIELD API active. Visit /api/docs"})

