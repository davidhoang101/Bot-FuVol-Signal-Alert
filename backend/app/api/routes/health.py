"""Health check endpoint."""
from fastapi import APIRouter, Request
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health_check(request: Request):
    """Health check endpoint."""
    try:
        client_host = request.client.host if request.client and hasattr(request.client, 'host') else 'unknown'
        logger.info(f"Health check called from {client_host}")
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "API is working"
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e),
            "type": type(e).__name__,
            "timestamp": datetime.utcnow().isoformat()
        }
