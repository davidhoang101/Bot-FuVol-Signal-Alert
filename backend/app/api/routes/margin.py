"""Margin endpoints."""
from fastapi import APIRouter
from app.services.monitoring import MonitoringService

router = APIRouter()


@router.get("")
async def get_margin():
    """Get margin information."""
    monitoring = MonitoringService()
    margin_info = await monitoring.get_margin_info()
    return margin_info
