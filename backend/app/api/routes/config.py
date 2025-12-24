"""Configuration endpoints."""
from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("")
async def get_config():
    """Get non-secret configuration."""
    return {
        "funding_scanner": {
            "min_rate": settings.FUNDING_SCANNER_MIN_RATE,
            "max_spread_bps": settings.FUNDING_SCANNER_MAX_SPREAD_BPS,
            "refresh_sec": settings.FUNDING_SCANNER_REFRESH_SEC,
        },
        "trading": {
            "max_notional_per_symbol": settings.TRADING_MAX_NOTIONAL_PER_SYMBOL,
            "max_total_notional": settings.TRADING_MAX_TOTAL_NOTIONAL,
            "min_free_margin_pct": settings.TRADING_MIN_FREE_MARGIN_PCT,
            "default_leverage": settings.TRADING_DEFAULT_LEVERAGE,
            "taker_fee_bps_spot": settings.TRADING_TAKER_FEE_BPS_SPOT,
            "taker_fee_bps_perp": settings.TRADING_TAKER_FEE_BPS_PERP,
            "paper_mode": settings.TRADING_PAPER_MODE,
        },
        "binance": {
            "testnet": settings.BINANCE_ENABLE_TESTNET,
        }
    }


@router.post("/reload")
async def reload_config():
    """Reload configuration (placeholder - would reload from file)."""
    return {"status": "ok", "message": "Config reloaded"}
