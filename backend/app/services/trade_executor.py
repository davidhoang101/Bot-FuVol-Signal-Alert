"""Trade execution service."""
import asyncio
import logging
from typing import Dict, Optional
from datetime import datetime
import uuid

from sqlalchemy.orm import Session

from app.exchange.binance_ccxt import BinanceExchangeAdapter
from app.core.config import settings
from app.db.models import Trade, Order
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


class TradeExecutorService:
    """Service for executing trades."""
    
    def __init__(self):
        """Initialize trade executor."""
        self.exchange = BinanceExchangeAdapter()
        self._initialized = False
    
    async def initialize(self):
        """Initialize exchange adapter."""
        if not self._initialized:
            await self.exchange.initialize()
            self._initialized = True
    
    def _check_idempotency(self, client_request_id: str) -> Optional[Trade]:
        """Check if request ID already exists."""
        db = SessionLocal()
        try:
            return db.query(Trade).filter(Trade.client_request_id == client_request_id).first()
        finally:
            db.close()
    
    def _validate_trade(self, symbol: str, notional: float) -> Dict:
        """Validate trade parameters."""
        errors = []
        
        # Check notional limits
        if notional > settings.TRADING_MAX_NOTIONAL_PER_SYMBOL:
            errors.append(f"Notional {notional} exceeds max per symbol {settings.TRADING_MAX_NOTIONAL_PER_SYMBOL}")
        
        # Check margin (will be checked before execution)
        
        return {'valid': len(errors) == 0, 'errors': errors}
    
    async def _check_preconditions(self, symbol: str) -> Dict:
        """Check preconditions before trading."""
        await self.initialize()
        
        try:
            # Get current prices
            spot_price = await self.exchange.get_spot_price(symbol)
            perp_price = await self.exchange.get_perp_price(symbol)
            
            # Calculate spread
            basis_pct = ((perp_price - spot_price) / spot_price * 100) if spot_price > 0 else 0
            spread_bps = abs(basis_pct * 100)
            
            # Check spread
            if spread_bps > settings.FUNDING_SCANNER_MAX_SPREAD_BPS:
                return {
                    'valid': False,
                    'error': f'Spread {spread_bps:.2f} bps exceeds max {settings.FUNDING_SCANNER_MAX_SPREAD_BPS} bps'
                }
            
            # Check margin
            margin_info = await self.exchange.fetch_margin_info()
            if margin_info['free_margin_pct'] < settings.TRADING_MIN_FREE_MARGIN_PCT:
                return {
                    'valid': False,
                    'error': f'Free margin {margin_info["free_margin_pct"]:.1f}% below minimum {settings.TRADING_MIN_FREE_MARGIN_PCT}%'
                }
            
            return {
                'valid': True,
                'spot_price': spot_price,
                'perp_price': perp_price,
                'spread_bps': spread_bps,
                'margin_info': margin_info
            }
        except Exception as e:
            logger.error(f"Error checking preconditions: {e}")
            return {'valid': False, 'error': str(e)}
    
    def _create_order_record(
        self,
        symbol: str,
        market_type: str,
        side: str,
        order_type: str,
        qty: float,
        price: Optional[float],
        status: str,
        exchange_order_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Order:
        """Create order record in database."""
        db = SessionLocal()
        try:
            order = Order(
                symbol=symbol,
                market_type=market_type,
                side=side,
                order_type=order_type,
                qty=qty,
                price=price,
                status=status,
                exchange_order_id=exchange_order_id,
                meta_data=metadata  # Column name is meta_data to avoid SQLAlchemy reserved word
            )
            db.add(order)
            db.commit()
            db.refresh(order)
            return order
        finally:
            db.close()
    
    def _create_trade_record(
        self,
        symbol: str,
        strategy_type: str,
        status: str,
        notional: float,
        client_request_id: Optional[str] = None,
        spot_order_id: Optional[str] = None,
        perp_order_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Trade:
        """Create trade record in database."""
        db = SessionLocal()
        try:
            trade = Trade(
                client_request_id=client_request_id,
                symbol=symbol,
                strategy_type=strategy_type,
                status=status,
                notional=notional,
                spot_order_id=spot_order_id,
                perp_order_id=perp_order_id,
                meta_data=metadata  # Column name is meta_data to avoid SQLAlchemy reserved word
            )
            db.add(trade)
            db.commit()
            db.refresh(trade)
            return trade
        finally:
            db.close()
    
    async def open_delta_neutral(
        self,
        symbol: str,
        notional: float,
        leverage: int = 1,
        client_request_id: Optional[str] = None
    ) -> Dict:
        """
        Open delta-neutral position: BUY spot + SHORT perp.
        
        Returns:
            Dict with trade info and order details
        """
        await self.initialize()
        
        # Generate request ID if not provided
        if not client_request_id:
            client_request_id = str(uuid.uuid4())
        
        # Check idempotency
        existing = self._check_idempotency(client_request_id)
        if existing:
            return {
                'status': 'duplicate',
                'message': 'Request ID already processed',
                'trade_id': existing.id
            }
        
        # Validate
        validation = self._validate_trade(symbol, notional)
        if not validation['valid']:
            return {'status': 'error', 'errors': validation['errors']}
        
        # Check preconditions
        preconditions = await self._check_preconditions(symbol)
        if not preconditions['valid']:
            return {'status': 'error', 'error': preconditions.get('error')}
        
        spot_price = preconditions['spot_price']
        qty = notional / spot_price
        
        # Create trade record
        trade = self._create_trade_record(
            symbol=symbol,
            strategy_type='delta_neutral',
            status='pending',
            notional=notional,
            client_request_id=client_request_id
        )
        
        try:
            # Phase 1: BUY spot
            if settings.TRADING_PAPER_MODE:
                spot_order = {
                    'id': f'sim_{uuid.uuid4()}',
                    'status': 'simulated',
                    'filled': qty,
                    'price': spot_price
                }
                spot_order_record = self._create_order_record(
                    symbol=symbol,
                    market_type='spot',
                    side='buy',
                    order_type='market',
                    qty=qty,
                    price=None,
                    status='simulated',
                    exchange_order_id=spot_order['id'],
                    metadata={'paper_mode': True}
                )
            else:
                spot_order = await self.exchange.place_order(
                    symbol=symbol,
                    side='buy',
                    amount=qty,
                    market_type='spot',
                    order_type='market'
                )
                spot_order_record = self._create_order_record(
                    symbol=symbol,
                    market_type='spot',
                    side='buy',
                    order_type='market',
                    qty=qty,
                    price=spot_order.get('price'),
                    status=spot_order.get('status', 'pending'),
                    exchange_order_id=str(spot_order.get('id')),
                )
            
            # Update trade with spot order
            db = SessionLocal()
            try:
                trade.spot_order_id = str(spot_order_record.id)
                db.commit()
            finally:
                db.close()
            
            # Phase 2: SHORT perp
            try:
                if settings.TRADING_PAPER_MODE:
                    perp_order = {
                        'id': f'sim_{uuid.uuid4()}',
                        'status': 'simulated',
                        'filled': qty,
                        'price': preconditions['perp_price']
                    }
                    perp_order_record = self._create_order_record(
                        symbol=symbol,
                        market_type='futures',
                        side='short',
                        order_type='market',
                        qty=qty,
                        price=None,
                        status='simulated',
                        exchange_order_id=perp_order['id'],
                        metadata={'paper_mode': True, 'leverage': leverage}
                    )
                else:
                    perp_order = await self.exchange.place_order(
                        symbol=symbol,
                        side='short',
                        amount=qty,
                        market_type='futures',
                        order_type='market',
                        leverage=leverage
                    )
                    perp_order_record = self._create_order_record(
                        symbol=symbol,
                        market_type='futures',
                        side='short',
                        order_type='market',
                        qty=qty,
                        price=perp_order.get('price'),
                        status=perp_order.get('status', 'pending'),
                        exchange_order_id=str(perp_order.get('id')),
                        metadata={'leverage': leverage}
                    )
                
                # Update trade with perp order
                db = SessionLocal()
                try:
                    trade.perp_order_id = str(perp_order_record.id)
                    trade.status = 'open'
                    db.commit()
                finally:
                    db.close()
                
                return {
                    'status': 'success',
                    'trade_id': trade.id,
                    'spot_order': {
                        'id': spot_order_record.id,
                        'exchange_id': spot_order.get('id'),
                        'status': spot_order.get('status')
                    },
                    'perp_order': {
                        'id': perp_order_record.id,
                        'exchange_id': perp_order.get('id'),
                        'status': perp_order.get('status')
                    },
                    'paper_mode': settings.TRADING_PAPER_MODE
                }
            
            except Exception as e:
                # Phase 2 failed - revert spot position
                logger.error(f"Perp order failed, reverting spot: {e}")
                try:
                    if not settings.TRADING_PAPER_MODE:
                        await self.exchange.place_order(
                            symbol=symbol,
                            side='sell',
                            amount=qty,
                            market_type='spot',
                            order_type='market'
                        )
                except Exception as revert_error:
                    logger.error(f"Failed to revert spot position: {revert_error}")
                
                # Update trade status
                db = SessionLocal()
                try:
                    trade.status = 'failed'
                    db.commit()
                finally:
                    db.close()
                
                return {
                    'status': 'error',
                    'error': f'Perp order failed: {e}. Spot position reverted.',
                    'trade_id': trade.id
                }
        
        except Exception as e:
            logger.error(f"Error opening delta-neutral position: {e}")
            db = SessionLocal()
            try:
                trade.status = 'failed'
                db.commit()
            finally:
                db.close()
            return {'status': 'error', 'error': str(e), 'trade_id': trade.id}
    
    async def close_delta_neutral(
        self,
        symbol: str,
        client_request_id: Optional[str] = None
    ) -> Dict:
        """
        Close delta-neutral position: close perp + SELL spot.
        
        Returns:
            Dict with close info
        """
        await self.initialize()
        
        if not client_request_id:
            client_request_id = str(uuid.uuid4())
        
        # Check idempotency
        existing = self._check_idempotency(client_request_id)
        if existing:
            return {
                'status': 'duplicate',
                'message': 'Request ID already processed',
                'trade_id': existing.id
            }
        
        try:
            # Get current position
            position = await self.exchange.fetch_position(symbol)
            if not position or position['size'] == 0:
                return {'status': 'error', 'error': 'No open position'}
            
            # Get spot balance
            balance = await self.exchange.fetch_balance('spot')
            base_asset = symbol.replace('USDT', '')
            spot_qty = balance['free'].get(base_asset, 0)
            
            if spot_qty == 0:
                return {'status': 'error', 'error': 'No spot balance to close'}
            
            # Phase 1: Close perp position
            if settings.TRADING_PAPER_MODE:
                close_result = {'status': 'simulated', 'order': {'id': f'sim_{uuid.uuid4()}'}}
            else:
                close_result = await self.exchange.close_position(symbol)
            
            # Phase 2: SELL spot
            if settings.TRADING_PAPER_MODE:
                spot_order = {
                    'id': f'sim_{uuid.uuid4()}',
                    'status': 'simulated',
                    'filled': spot_qty
                }
            else:
                spot_order = await self.exchange.place_order(
                    symbol=symbol,
                    side='sell',
                    amount=spot_qty,
                    market_type='spot',
                    order_type='market'
                )
            
            # Create trade record
            trade = self._create_trade_record(
                symbol=symbol,
                strategy_type='delta_neutral_close',
                status='closed',
                notional=0,  # Will be calculated
                client_request_id=client_request_id
            )
            
            return {
                'status': 'success',
                'trade_id': trade.id,
                'perp_close': close_result,
                'spot_sell': spot_order,
                'paper_mode': settings.TRADING_PAPER_MODE
            }
        
        except Exception as e:
            logger.error(f"Error closing delta-neutral position: {e}")
            return {'status': 'error', 'error': str(e)}
    
    async def place_manual_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        market_type: str,
        order_type: str = 'market',
        price: Optional[float] = None,
        leverage: Optional[int] = None
    ) -> Dict:
        """Place a manual single order."""
        await self.initialize()
        
        try:
            if settings.TRADING_PAPER_MODE:
                # Simulate order
                current_price = await self.exchange.get_spot_price(symbol) if market_type == 'spot' else await self.exchange.get_perp_price(symbol)
                order = {
                    'id': f'sim_{uuid.uuid4()}',
                    'status': 'simulated',
                    'filled': amount,
                    'price': price or current_price
                }
                order_record = self._create_order_record(
                    symbol=symbol,
                    market_type=market_type,
                    side=side,
                    order_type=order_type,
                    qty=amount,
                    price=price,
                    status='simulated',
                    exchange_order_id=order['id'],
                    metadata={'paper_mode': True}
                )
            else:
                order = await self.exchange.place_order(
                    symbol=symbol,
                    side=side,
                    amount=amount,
                    market_type=market_type,
                    order_type=order_type,
                    price=price,
                    leverage=leverage
                )
                order_record = self._create_order_record(
                    symbol=symbol,
                    market_type=market_type,
                    side=side,
                    order_type=order_type,
                    qty=amount,
                    price=price,
                    status=order.get('status', 'pending'),
                    exchange_order_id=str(order.get('id')),
                    metadata={'leverage': leverage} if leverage else None
                )
            
            return {
                'status': 'success',
                'order_id': order_record.id,
                'exchange_order_id': order.get('id'),
                'status': order.get('status'),
                'paper_mode': settings.TRADING_PAPER_MODE
            }
        
        except Exception as e:
            logger.error(f"Error placing manual order: {e}")
            return {'status': 'error', 'error': str(e)}
