"""Logs endpoints."""
from fastapi import APIRouter, Query
from typing import Optional
from app.services.monitoring import MonitoringService

router = APIRouter()


@router.get("/tail")
async def get_logs_tail(
    limit: int = Query(100, description="Number of log lines to return"),
    level: Optional[str] = Query(None, description="Filter by log level")
):
    """Get recent event logs."""
    monitoring = MonitoringService()
    logs = monitoring.get_event_logs(limit=limit, level=level)
    return {"logs": logs, "count": len(logs)}
