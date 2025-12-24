"""Trading endpoints."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.trade_executor import TradeExecutorService

router = APIRouter()


class OpenDeltaNeutralRequest(BaseModel):
    symbol: str
    notional: float
    leverage: int = 1
    client_request_id: Optional[str] = None


class CloseDeltaNeutralRequest(BaseModel):
    symbol: str
    client_request_id: Optional[str] = None


class PlaceOrderRequest(BaseModel):
    symbol: str
    side: str
    amount: float
    market_type: str
    order_type: str = "market"
    price: Optional[float] = None
    leverage: Optional[int] = None


@router.post("/open_delta_neutral")
async def open_delta_neutral(request: OpenDeltaNeutralRequest):
    """Open delta-neutral position."""
    executor = TradeExecutorService()
    result = await executor.open_delta_neutral(
        symbol=request.symbol,
        notional=request.notional,
        leverage=request.leverage,
        client_request_id=request.client_request_id
    )
    
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('error', 'Unknown error'))
    
    return result


@router.post("/close_delta_neutral")
async def close_delta_neutral(request: CloseDeltaNeutralRequest):
    """Close delta-neutral position."""
    executor = TradeExecutorService()
    result = await executor.close_delta_neutral(
        symbol=request.symbol,
        client_request_id=request.client_request_id
    )
    
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('error', 'Unknown error'))
    
    return result


@router.post("/place_order")
async def place_order(request: PlaceOrderRequest):
    """Place a manual order."""
    executor = TradeExecutorService()
    result = await executor.place_manual_order(
        symbol=request.symbol,
        side=request.side,
        amount=request.amount,
        market_type=request.market_type,
        order_type=request.order_type,
        price=request.price,
        leverage=request.leverage
    )
    
    if result.get('status') == 'error':
        raise HTTPException(status_code=400, detail=result.get('error', 'Unknown error'))
    
    return result
