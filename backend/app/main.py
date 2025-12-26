"""FastAPI main application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import logging
import os
from pathlib import Path

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

# Include routers (must be before catch-all route)
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

# Serve static files from frontend build (for production)
# Try multiple paths to support both local dev and Docker deployment
# Local: backend/app/main.py -> backend -> root -> frontend/dist
# Docker: /app/backend/app/main.py -> /app/backend -> /app -> frontend/dist
# Or: /app/frontend/dist (absolute path in Docker)
logger_main = logging.getLogger(__name__)
possible_paths = [
    Path("/app/frontend/dist"),  # Docker absolute path (Railway/Docker)
    Path(__file__).parent.parent.parent / "frontend" / "dist",  # Docker: /app/backend -> /app -> frontend/dist
    Path(__file__).parent.parent.parent.parent / "frontend" / "dist",  # Local dev: backend -> root -> frontend/dist
    Path.cwd().parent / "frontend" / "dist",  # Alternative: from working dir
    Path.cwd() / "frontend" / "dist",  # If running from root
]

frontend_dist = None
logger_main.info(f"Searching for frontend dist. Current dir: {Path.cwd()}, __file__: {__file__}")
for path in possible_paths:
    logger_main.info(f"Checking path: {path} (exists: {path.exists()})")
    if path.exists() and (path / "index.html").exists():
        frontend_dist = path
        logger_main.info(f"✅ Found frontend dist at: {frontend_dist}")
        break

if frontend_dist is None:
    # Fallback to first path if none found (will show error in startup)
    frontend_dist = possible_paths[0]
    logger_main.warning(f"⚠️ Frontend dist not found, using fallback: {frontend_dist}")

# Mount static assets if they exist (must be before catch-all route)
static_dir = frontend_dist / "assets"
if static_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(static_dir)), name="assets")

# Debug endpoint to check frontend status
@app.get("/api/debug/frontend")
async def debug_frontend():
    """Debug endpoint to check frontend build status."""
    return {
        "frontend_dist_path": str(frontend_dist),
        "frontend_dist_exists": frontend_dist.exists(),
        "index_html_exists": (frontend_dist / "index.html").exists() if frontend_dist.exists() else False,
        "current_dir": str(Path.cwd()),
        "file_location": __file__,
        "possible_paths": [str(p) for p in possible_paths],
        "static_dir_exists": static_dir.exists() if frontend_dist.exists() else False,
    }

# Root path - serve index.html
@app.get("/")
async def serve_root():
    """Serve frontend index.html for root path."""
    index_path = frontend_dist / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    
    return JSONResponse(
        status_code=503,
        content={
            "error": "Frontend not built",
            "message": "Please build frontend first: cd frontend && npm run build",
            "path": str(frontend_dist),
            "current_dir": str(Path.cwd()),
            "debug": {
                "frontend_dist_exists": frontend_dist.exists(),
                "index_path": str(index_path),
            }
        }
    )

# Serve frontend static files (catch-all route - must be LAST)
@app.get("/{full_path:path}")
async def serve_frontend(full_path: str):
    """Serve frontend app for all non-API routes."""
    # Don't interfere with API routes
    if full_path.startswith("api/"):
        return JSONResponse(status_code=404, content={"error": "Not found"})
    
    # Check if frontend is built
    if not frontend_dist.exists() or not (frontend_dist / "index.html").exists():
        return JSONResponse(
            status_code=503,
            content={
                "error": "Frontend not built",
                "message": "Please build frontend first: cd frontend && npm run build",
                "path": str(frontend_dist),
                "current_dir": str(Path.cwd()),
                "requested": full_path
            }
        )
    
    # Serve static files if they exist (CSS, JS, images, etc.)
    if full_path and full_path != "":
        requested_file = frontend_dist / full_path
        if requested_file.exists() and requested_file.is_file():
            return FileResponse(str(requested_file))
    
    # For SPA routing, serve index.html for all other routes
    index_path = frontend_dist / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    
    return JSONResponse(
        status_code=404,
        content={
            "error": "Frontend file not found",
            "requested": full_path,
            "dist_path": str(frontend_dist)
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize database on startup."""
    logger = logging.getLogger(__name__)
    logger.info("Starting up application...")
    
    # Log frontend status
    logger.info(f"Checking for frontend at: {frontend_dist}")
    logger.info(f"Frontend dist exists: {frontend_dist.exists()}")
    logger.info(f"Current working directory: {os.getcwd()}")
    
    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        logger.info(f"✅ Frontend found at {frontend_dist}")
        static_dir = frontend_dist / "assets"
        if static_dir.exists():
            logger.info(f"✅ Static assets directory found: {static_dir}")
        else:
            logger.warning(f"⚠️ Static assets directory not found: {static_dir}")
    else:
        logger.warning(f"⚠️ Frontend dist not found at {frontend_dist}")
        if frontend_dist.parent.exists():
            logger.info(f"Files in frontend directory: {[f.name for f in frontend_dist.parent.iterdir()]}")
    
    # Initialize database
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
