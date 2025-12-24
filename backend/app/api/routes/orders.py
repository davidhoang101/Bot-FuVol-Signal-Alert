"""Orders endpoints."""
from fastapi import APIRouter, Query
from typing import Optional
from app.services.monitoring import MonitoringService

router = APIRouter()


@router.get("")
async def get_orders(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    market_type: Optional[str] = Query(None, description="Filter by market type (spot/futures)")
):
    """Get orders."""
    monitoring = MonitoringService()
    orders = await monitoring.get_orders(symbol=symbol, market_type=market_type)
    return {"orders": orders, "count": len(orders)}
