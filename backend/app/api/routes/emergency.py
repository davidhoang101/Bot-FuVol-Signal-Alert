"""Emergency endpoints."""
from fastapi import APIRouter, Query, HTTPException
from typing import Optional
from app.exchange.binance_ccxt import BinanceExchangeAdapter
from app.core.config import settings

router = APIRouter()


@router.post("/close_all")
async def emergency_close_all(
    symbol: Optional[str] = Query(None, description="Symbol to close (if None, closes all)")
):
    """Emergency close all positions for a symbol."""
    if settings.TRADING_PAPER_MODE:
        return {
            "status": "simulated",
            "message": "Paper mode enabled - no actual orders placed"
        }
    
    exchange = BinanceExchangeAdapter()
    await exchange.initialize()
    
    try:
        if symbol:
            # Close specific symbol
            result = await exchange.close_position(symbol)
            return {
                "status": "success",
                "symbol": symbol,
                "result": result
            }
        else:
            # Close all positions (would need to fetch all positions first)
            # For now, return error
            raise HTTPException(
                status_code=400,
                detail="Closing all positions requires specifying a symbol"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
