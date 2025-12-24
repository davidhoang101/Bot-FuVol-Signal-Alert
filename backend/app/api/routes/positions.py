"""Positions endpoints."""
from fastapi import APIRouter, Query
from typing import Optional
from app.services.monitoring import MonitoringService

router = APIRouter()


@router.get("")
async def get_positions(
    symbol: Optional[str] = Query(None, description="Filter by symbol")
):
    """Get positions."""
    monitoring = MonitoringService()
    positions = await monitoring.get_positions(symbol=symbol)
    return {"positions": positions, "count": len(positions)}
