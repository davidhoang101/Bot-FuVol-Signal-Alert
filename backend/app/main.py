"""FastAPI main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.routes import health, config, markets, trade, orders, positions, balances, margin, emergency, logs
from app.db.session import init_db

# Setup logging
setup_logging()

# Create FastAPI app
app = FastAPI(
    title="Binance Trading Console API",
    description="Funding Rate Scanner + Manual/Assisted Trading Console",
    version="1.0.0",
    debug=settings.DEBUG
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(config.router, prefix="/api/config", tags=["config"])
app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
app.include_router(trade.router, prefix="/api/trade", tags=["trade"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(positions.router, prefix="/api/positions", tags=["positions"])
app.include_router(balances.router, prefix="/api/balances", tags=["balances"])
app.include_router(margin.router, prefix="/api/margin", tags=["margin"])
app.include_router(emergency.router, prefix="/api/emergency", tags=["emergency"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger = logging.getLogger(__name__)
    logger.info("Starting up application...")
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        # Don't raise - allow app to start even if DB init fails
        logger.warning("Continuing without database initialization")


@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    import traceback
    
    logger = logging.getLogger(__name__)
    error_trace = traceback.format_exc()
    
    # Log full error for debugging
    logger.error(f"Unhandled exception at {request.url}: {exc}", exc_info=True)
    logger.error(f"Full traceback:\n{error_trace}")
    
    # Always return detailed error for now (easier debugging)
    try:
        return JSONResponse(
            status_code=500,
            content={
                "error": str(exc),
                "type": type(exc).__name__,
                "path": str(request.url.path) if hasattr(request, 'url') else "unknown",
                "traceback": error_trace.split('\n')[-15:]  # Last 15 lines of traceback
            }
        )
    except Exception as e2:
        # If even error handler fails, return minimal response
        logger.error(f"Error handler itself failed: {e2}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "detail": str(exc)}
        )


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower()
    )
