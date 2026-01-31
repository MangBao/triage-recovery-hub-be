"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.database import engine, Base
from app.config import settings, get_cors_origins_list
from app.logging_config import setup_logging
from api.tickets import router as tickets_router

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
