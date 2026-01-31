"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.config import settings, get_cors_origins_list
from api.tickets import router as tickets_router

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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

# CORS Middleware (for Next.js frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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
