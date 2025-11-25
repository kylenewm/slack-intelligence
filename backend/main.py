"""
FastAPI application entry point.
Main server for Slack Intelligence API.
"""

import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from .config import settings
from .database import init_db
from .api.routes import router
from .api.slack_events import router as events_router
from .logging_config import setup_logging

# Configure structured logging
logger = setup_logging()

# Initialize scheduler
scheduler = AsyncIOScheduler()


@scheduler.scheduled_job('interval', minutes=settings.SYNC_INTERVAL_MINUTES, id='auto_sync')
async def auto_sync_job():
    """Background job to auto-sync Slack messages"""
    if not settings.AUTO_SYNC_ENABLED:
        return
    
    logger.info("🔄 Auto-sync running...")
    try:
        from .services.sync_service import SyncService
        sync_service = SyncService()
        result = await sync_service.sync(hours_ago=1)
        logger.info(f"✅ Auto-sync completed: {result.get('new_messages', 0)} new messages")
    except Exception as e:
        logger.error(f"❌ Auto-sync failed: {e}", exc_info=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("🚀 Starting Slack Intelligence API...")
    
    # Validate configuration
    if not settings.validate():
        logger.error("❌ Configuration validation failed")
        logger.error("   Please check your .env file")
    
    # Initialize database
    init_db()
    
    # Start scheduler if enabled
    if settings.AUTO_SYNC_ENABLED:
        scheduler.start()
        logger.info(f"✅ Auto-sync enabled (every {settings.SYNC_INTERVAL_MINUTES} min)")
    else:
        logger.info("⏸️  Auto-sync disabled (set AUTO_SYNC_ENABLED=true to enable)")
    
    logger.info("✅ Application started successfully")
    logger.info(f"   Debug mode: {settings.DEBUG}")
    logger.info(f"   Database: {settings.DATABASE_URL}")
    
    yield
    
    # Shutdown
    if scheduler.running:
        scheduler.shutdown()
    logger.info("👋 Shutting down Slack Intelligence API...")


# Create FastAPI app
app = FastAPI(
    title="Slack Intelligence API",
    description="AI-powered Slack inbox prioritization and search",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)
app.include_router(events_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Slack Intelligence",
        "version": "1.0.0",
        "status": "running",
        "api_docs": "/docs",
        "api_base": "/api/slack"
    }


@app.get("/health")
async def health():
    """Health check"""
    return {
        "status": "healthy",
        "service": "slack-intelligence"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )

