"""Market data endpoints."""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
import logging
from app.services.funding_scanner import FundingScannerService

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/funding")
async def get_funding_opportunities(
    min_rate: Optional[float] = Query(None, description="Minimum funding rate"),
    max_spread_bps: Optional[float] = Query(None, description="Maximum spread in basis points"),
    quote: str = Query("USDT", description="Quote asset"),
    exclude_low_volume: bool = Query(True, description="Exclude low volume symbols")
):
    """Get funding opportunities."""
    try:
        scanner = FundingScannerService()
        results = await scanner.scan_funding_opportunities(
            min_rate=min_rate,
            max_spread_bps=max_spread_bps,
            quote=quote,
            exclude_low_volume=exclude_low_volume
        )
        return {"results": results, "count": len(results)}
    except Exception as e:
        logger.error(f"Error in get_funding_opportunities: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch funding opportunities: {str(e)}")


@router.get("/symbol/{symbol}/snapshot")
async def get_symbol_snapshot(symbol: str):
    """Get detailed snapshot for a symbol."""
    scanner = FundingScannerService()
    snapshot = await scanner.get_symbol_snapshot(symbol)
    return snapshot
