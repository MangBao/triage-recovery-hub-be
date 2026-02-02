"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.database import engine, Base
from app.config import settings, get_cors_origins_list
from app.logging_config import setup_logging
from api.tickets import router as tickets_router
from api.websocket import router as websocket_router

# Setup centralized logging with file rotation
setup_logging()
logger = logging.getLogger(__name__)

# Rate Limiter (per IP address) with default limits for all routes
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan events.
    
    Startup:
    - Create database tables if they don't exist
    
    Shutdown:
    - Cleanup (if needed)
    """
    # Startup
    logger.info("🚀 Starting Triage & Recovery Hub API...")
    logger.info("Creating database tables if not exist...")
    # Using SQLAlchemy create_all for table creation
    # Alembic migrations available for schema versioning: `alembic upgrade head`
    Base.metadata.create_all(bind=engine)
    logger.info("✅ Database ready")
    logger.info(f"🛡️ Rate Limit: {settings.RATE_LIMIT_PER_MINUTE} req/min per IP (default for all routes)")
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    from api.websocket import manager
    if hasattr(manager, "shutdown"):
        await manager.shutdown()


# Create FastAPI application
app = FastAPI(
    title="Triage & Recovery Hub API",
    description="AI-powered customer support ticket triage system using Google Gemini",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Attach shared rate limiter to app state (used by api/tickets.py via request.app.state.limiter)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS Middleware (for Next.js frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate Limiting Middleware (global - applies to all routes)
app.add_middleware(SlowAPIMiddleware)

# Include routers
app.include_router(tickets_router, prefix="/api/tickets", tags=["tickets"])
app.include_router(websocket_router)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Used by:
    - Docker health checks
    - Load balancers
    - Monitoring systems
    """
    return {"status": "ok", "service": "triage-recovery-hub"}


@app.get("/health/deep")
async def deep_health_check():
    """
    Deep health check - verifies all backend dependencies.
    
    Checks:
    - PostgreSQL connectivity (SELECT 1)
    - Redis connectivity (PING)
    
    Returns:
        200 OK with component status if all healthy
        503 Service Unavailable if any dependency fails
    """
    from sqlalchemy import text
    from sqlalchemy.exc import SQLAlchemyError
    from app.database import SessionLocal
    import redis
    from redis.exceptions import RedisError
    
    status = {"db": "unknown", "redis": "unknown"}
    all_healthy = True
    
    # Check PostgreSQL with context manager
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        status["db"] = "ok"
    except SQLAlchemyError as e:
        status["db"] = f"error: {str(e)[:100]}"
        all_healthy = False
    
    # Check Redis with try/finally
    r = None
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        status["redis"] = "ok"
    except RedisError as e:
        status["redis"] = f"error: {str(e)[:100]}"
        all_healthy = False
    finally:
        if r is not None:
            try:
                r.close()
            except RedisError:
                pass  # Ignore close errors
    
    if all_healthy:
        return {"status": "ok", "components": status}
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "components": status}
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
