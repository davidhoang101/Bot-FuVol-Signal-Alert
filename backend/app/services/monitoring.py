"""Monitoring service."""
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta

from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.exchange.binance_ccxt import BinanceExchangeAdapter
from app.db.models import Order, Trade, EventLog
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class MonitoringService:
    """Service for monitoring orders, positions, and balances."""
    
    def __init__(self):
        """Initialize monitoring service."""
        self.exchange = BinanceExchangeAdapter()
        self._initialized = False
    
    async def initialize(self):
        """Initialize exchange adapter."""
        if not self._initialized:
            await self.exchange.initialize()
            self._initialized = True
    
    async def get_orders(
        self,
        symbol: Optional[str] = None,
        market_type: Optional[str] = None
    ) -> List[Dict]:
        """Get orders from database and exchange."""
        await self.initialize()
        
        db = SessionLocal()
        try:
            query = db.query(Order)
            if symbol:
                query = query.filter(Order.symbol == symbol)
            if market_type:
                query = query.filter(Order.market_type == market_type)
            
            orders = query.order_by(desc(Order.created_at)).limit(100).all()
            
            result = []
            for order in orders:
                result.append({
                    'id': order.id,
                    'symbol': order.symbol,
                    'market_type': order.market_type,
                    'side': order.side,
                    'order_type': order.order_type,
                    'qty': order.qty,
                    'price': order.price,
                    'status': order.status,
                    'exchange_order_id': order.exchange_order_id,
                    'fill_price': order.fill_price,
                    'fill_qty': order.fill_qty,
                    'created_at': order.created_at.isoformat() if order.created_at else None,
                    'metadata': order.meta_data  # Note: column is meta_data, but we expose as metadata in API
                })
            
            return result
        finally:
            db.close()
    
    async def get_positions(self, symbol: Optional[str] = None) -> List[Dict]:
        """Get current positions from exchange."""
        await self.initialize()
        
        try:
            if symbol:
                position = await self.exchange.fetch_position(symbol)
                if position and position['size'] != 0:
                    return [position]
                return []
            else:
                # Get all positions (would need to fetch all symbols)
                # For now, return empty - can be enhanced
                return []
        except Exception as e:
            logger.error(f"Error fetching positions: {e}")
            return []
    
    async def get_balances(self) -> Dict:
        """Get account balances."""
        await self.initialize()
        
        try:
            spot_balance = await self.exchange.fetch_balance('spot')
            futures_balance = await self.exchange.fetch_balance('futures')
            
            return {
                'spot': spot_balance,
                'futures': futures_balance
            }
        except Exception as e:
            logger.error(f"Error fetching balances: {e}")
            return {'spot': {}, 'futures': {}}
    
    async def get_margin_info(self) -> Dict:
        """Get margin information."""
        await self.initialize()
        
        try:
            return await self.exchange.fetch_margin_info()
        except Exception as e:
            logger.error(f"Error fetching margin info: {e}")
            return {
                'total_margin': 0,
                'free_margin': 0,
                'used_margin': 0,
                'margin_ratio': 0,
                'free_margin_pct': 100,
                'total_balance': 0
            }
    
    async def check_delta_drift(self, symbol: str, tolerance: float = 0.01) -> Dict:
        """
        Check delta drift for a symbol.
        
        Returns:
            Dict with delta info and drift status
        """
        await self.initialize()
        
        try:
            # Get position
            position = await self.exchange.fetch_position(symbol)
            
            # Get spot balance
            balance = await self.exchange.fetch_balance('spot')
            base_asset = symbol.replace('USDT', '')
            spot_qty = balance['free'].get(base_asset, 0) + balance['used'].get(base_asset, 0)
            
            # Calculate delta
            perp_qty = position['size'] if position else 0
            delta = spot_qty + perp_qty  # Should be ~0 for delta-neutral
            
            drift_exceeded = abs(delta) > tolerance
            
            return {
                'symbol': symbol,
                'spot_qty': spot_qty,
                'perp_qty': perp_qty,
                'delta': delta,
                'tolerance': tolerance,
                'drift_exceeded': drift_exceeded,
                'warning': drift_exceeded
            }
        except Exception as e:
            logger.error(f"Error checking delta drift for {symbol}: {e}")
            return {
                'symbol': symbol,
                'error': str(e)
            }
    
    def log_event(self, level: str, message: str, context: Optional[Dict] = None):
        """Log an event to the database."""
        db = SessionLocal()
        try:
            event = EventLog(
                level=level,
                message=message,
                context_json=context
            )
            db.add(event)
            db.commit()
        except Exception as e:
            logger.error(f"Error logging event: {e}")
        finally:
            db.close()
    
    def get_event_logs(self, limit: int = 100, level: Optional[str] = None) -> List[Dict]:
        """Get recent event logs."""
        db = SessionLocal()
        try:
            query = db.query(EventLog)
            if level:
                query = query.filter(EventLog.level == level)
            
            logs = query.order_by(desc(EventLog.timestamp)).limit(limit).all()
            return [log.to_dict() for log in logs]
        finally:
            db.close()
