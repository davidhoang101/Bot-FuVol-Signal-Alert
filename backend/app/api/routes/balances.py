"""Balances endpoints."""
from fastapi import APIRouter
from app.services.monitoring import MonitoringService

router = APIRouter()


@router.get("")
async def get_balances():
    """Get account balances."""
    monitoring = MonitoringService()
    balances = await monitoring.get_balances()
    return balances
