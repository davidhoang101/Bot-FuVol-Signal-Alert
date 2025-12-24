"""Binance exchange adapter using ccxt."""
import asyncio
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

import ccxt.async_support as ccxt
from ccxt import NetworkError, ExchangeError
import aiohttp

from app.core.config import settings

logger = logging.getLogger(__name__)


class BinanceExchangeAdapter:
    """Binance exchange adapter built on ccxt."""
    
    def __init__(self):
        """Initialize Binance clients."""
        self.spot_client: Optional[ccxt.binance] = None
        self.futures_client: Optional[ccxt.binance] = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize spot and futures clients."""
        if self._initialized:
            return
        
        try:
            # Check if API keys are set (optional for public data)
            api_key = settings.BINANCE_API_KEY or ''
            api_secret = settings.BINANCE_API_SECRET or ''
            
            # Spot client
            self.spot_client = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                    'adjustForTimeDifference': True,
                },
                'sandbox': settings.BINANCE_ENABLE_TESTNET,
            })
            
            # Futures client
            self.futures_client = ccxt.binance({
                'apiKey': api_key,
                'secret': api_secret,
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future',  # Important: set to 'future' for futures
                    'adjustForTimeDifference': True,
                },
                'sandbox': settings.BINANCE_ENABLE_TESTNET,
            })
            
            # Test connections
            logger.info("Loading spot markets...")
            await self.spot_client.load_markets()
            logger.info("Loading futures markets...")
            await self.futures_client.load_markets()
            
            self._initialized = True
            logger.info("✅ Binance exchange adapter initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize Binance adapter: {e}", exc_info=True)
            raise
    
    async def close(self):
        """Close connections."""
        if self.spot_client:
            await self.spot_client.close()
        if self.futures_client:
            await self.futures_client.close()
        self._initialized = False
    
    async def _retry_with_backoff(self, func, max_retries=3, base_delay=1):
        """Retry function with exponential backoff."""
        for attempt in range(max_retries):
            try:
                return await func()
            except (NetworkError, ExchangeError) as e:
                if attempt == max_retries - 1:
                    raise
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay}s: {e}")
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                raise
    
    async def get_spot_price(self, symbol: str) -> float:
        """Get current spot price."""
        await self.initialize()
        try:
            ticker = await self._retry_with_backoff(
                lambda: self.spot_client.fetch_ticker(symbol)
            )
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error getting spot price for {symbol}: {e}")
            raise
    
    async def get_perp_price(self, symbol: str) -> float:
        """Get current perpetual futures price."""
        await self.initialize()
        try:
            ticker = await self._retry_with_backoff(
                lambda: self.futures_client.fetch_ticker(symbol)
            )
            return float(ticker['last'])
        except Exception as e:
            logger.error(f"Error getting perp price for {symbol}: {e}")
            raise
    
    async def get_funding_rate(self, symbol: str) -> Dict:
        """Get funding rate information using public API (no API key required)."""
        await self.initialize()
        try:
            
            # Use Binance public API directly (no API key needed)
            # https://fapi.binance.com/fapi/v1/premiumIndex?symbol=BTCUSDT
            url = f"https://fapi.binance.com/fapi/v1/premiumIndex?symbol={symbol}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        funding_rate = float(data.get('lastFundingRate', 0))
                        next_funding_time = data.get('nextFundingTime')
                        
                        return {
                            'funding_rate': funding_rate,
                            'next_funding_time': int(next_funding_time) if next_funding_time else None,
                            'timestamp': data.get('time')
                        }
                    else:
                        logger.warning(f"Binance API returned status {response.status} for {symbol}")
                        return {
                            'funding_rate': 0.0,
                            'next_funding_time': None,
                            'timestamp': None
                        }
        except Exception as e:
            logger.error(f"Error getting funding rate for {symbol}: {e}", exc_info=True)
            # Return default instead of raising to allow scanning to continue
            return {
                'funding_rate': 0.0,
                'next_funding_time': None,
                'timestamp': None
            }
    
    async def get_orderbook(self, symbol: str, market_type: str = 'spot', limit: int = 20) -> Dict:
        """Get orderbook snapshot."""
        await self.initialize()
        client = self.spot_client if market_type == 'spot' else self.futures_client
        
        try:
            orderbook = await self._retry_with_backoff(
                lambda: client.fetch_order_book(symbol, limit)
            )
            
            # Calculate spread
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])
            
            spread_bps = None
            if bids and asks:
                best_bid = float(bids[0][0])
                best_ask = float(asks[0][0])
                mid_price = (best_bid + best_ask) / 2
                spread_bps = ((best_ask - best_bid) / mid_price) * 10000
            
            return {
                'bids': bids[:limit],
                'asks': asks[:limit],
                'spread_bps': spread_bps
            }
        except Exception as e:
            logger.error(f"Error getting orderbook for {symbol}: {e}")
            raise
    
    async def place_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        market_type: str = 'spot',
        order_type: str = 'market',
        price: Optional[float] = None,
        leverage: Optional[int] = None,
        reduce_only: bool = False
    ) -> Dict:
        """
        Place an order.
        
        Args:
            symbol: Trading symbol
            side: 'buy'/'sell' for spot, 'long'/'short' for futures
            amount: Order amount (in base currency for spot, in contracts for futures)
            market_type: 'spot' or 'futures'
            order_type: 'market' or 'limit'
            price: Limit price (required for limit orders)
            leverage: Leverage for futures (optional)
            reduce_only: For futures, reduce position only
        
        Returns:
            Order information dict
        """
        await self.initialize()
        client = self.spot_client if market_type == 'spot' else self.futures_client
        
        # Convert side for futures
        if market_type == 'futures':
            if side == 'long':
                side = 'buy'
            elif side == 'short':
                side = 'sell'
        
        try:
            # Set leverage if provided for futures
            if market_type == 'futures' and leverage:
                await self._retry_with_backoff(
                    lambda: client.set_leverage(leverage, symbol)
                )
            
            # Build order params
            params = {}
            if market_type == 'futures' and reduce_only:
                params['reduceOnly'] = True
            
            # Place order
            if order_type == 'market':
                order = await self._retry_with_backoff(
                    lambda: client.create_market_order(symbol, side, amount, params=params)
                )
            else:
                if not price:
                    raise ValueError("Price required for limit orders")
                order = await self._retry_with_backoff(
                    lambda: client.create_limit_order(symbol, side, amount, price, params=params)
                )
            
            return {
                'id': order.get('id'),
                'symbol': order.get('symbol'),
                'side': order.get('side'),
                'amount': order.get('amount'),
                'price': order.get('price'),
                'status': order.get('status'),
                'filled': order.get('filled'),
                'remaining': order.get('remaining'),
                'info': order.get('info', {})
            }
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            raise
    
    async def fetch_open_orders(self, symbol: Optional[str] = None, market_type: str = 'spot') -> List[Dict]:
        """Fetch open orders."""
        await self.initialize()
        client = self.spot_client if market_type == 'spot' else self.futures_client
        
        try:
            orders = await self._retry_with_backoff(
                lambda: client.fetch_open_orders(symbol) if symbol else client.fetch_open_orders()
            )
            return [{
                'id': o.get('id'),
                'symbol': o.get('symbol'),
                'side': o.get('side'),
                'amount': o.get('amount'),
                'price': o.get('price'),
                'status': o.get('status'),
                'timestamp': o.get('timestamp'),
            } for o in orders]
        except Exception as e:
            logger.error(f"Error fetching open orders: {e}")
            return []
    
    async def fetch_position(self, symbol: str) -> Optional[Dict]:
        """Fetch futures position."""
        await self.initialize()
        try:
            positions = await self._retry_with_backoff(
                lambda: self.futures_client.fetch_positions([symbol])
            )
            
            # Find position for this symbol
            for pos in positions:
                if pos.get('symbol') == symbol and float(pos.get('contracts', 0)) != 0:
                    return {
                        'symbol': pos.get('symbol'),
                        'side': pos.get('side'),  # 'long' or 'short'
                        'size': float(pos.get('contracts', 0)),
                        'entry_price': float(pos.get('entryPrice', 0)),
                        'mark_price': float(pos.get('markPrice', 0)),
                        'unrealized_pnl': float(pos.get('unrealizedPnl', 0)),
                        'percentage': float(pos.get('percentage', 0)),
                        'leverage': float(pos.get('leverage', 1)),
                    }
            return None
        except Exception as e:
            logger.error(f"Error fetching position for {symbol}: {e}")
            return None
    
    async def fetch_balance(self, market_type: str = 'spot') -> Dict:
        """Fetch account balance."""
        await self.initialize()
        client = self.spot_client if market_type == 'spot' else self.futures_client
        
        try:
            balance = await self._retry_with_backoff(
                lambda: client.fetch_balance()
            )
            
            # Extract relevant balances
            result = {
                'total': {},
                'free': {},
                'used': {}
            }
            
            for currency, amounts in balance.items():
                if currency in ['info', 'free', 'used', 'total']:
                    continue
                if isinstance(amounts, dict):
                    result['total'][currency] = float(amounts.get('total', 0))
                    result['free'][currency] = float(amounts.get('free', 0))
                    result['used'][currency] = float(amounts.get('used', 0))
            
            return result
        except Exception as e:
            logger.error(f"Error fetching balance: {e}")
            return {'total': {}, 'free': {}, 'used': {}}
    
    async def fetch_margin_info(self) -> Dict:
        """Fetch futures margin information."""
        await self.initialize()
        try:
            balance = await self._retry_with_backoff(
                lambda: self.futures_client.fetch_balance()
            )
            
            # Calculate margin metrics
            total_margin = float(balance.get('USDT', {}).get('used', 0))
            free_margin = float(balance.get('USDT', {}).get('free', 0))
            total_balance = total_margin + free_margin
            
            margin_ratio = (total_margin / total_balance * 100) if total_balance > 0 else 0
            free_margin_pct = (free_margin / total_balance * 100) if total_balance > 0 else 100
            
            return {
                'total_margin': total_margin,
                'free_margin': free_margin,
                'used_margin': total_margin,
                'margin_ratio': margin_ratio,
                'free_margin_pct': free_margin_pct,
                'total_balance': total_balance
            }
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
    
    async def close_position(self, symbol: str) -> Dict:
        """Close futures position."""
        await self.initialize()
        try:
            position = await self.fetch_position(symbol)
            if not position:
                return {'status': 'no_position', 'message': 'No open position'}
            
            # Determine side to close
            close_side = 'sell' if position['side'] == 'long' else 'buy'
            
            # Close with market order, reduce only
            order = await self.place_order(
                symbol=symbol,
                side=close_side,
                amount=abs(position['size']),
                market_type='futures',
                order_type='market',
                reduce_only=True
            )
            
            return {
                'status': 'closed',
                'order': order
            }
        except Exception as e:
            logger.error(f"Error closing position for {symbol}: {e}")
            raise
    
    async def get_24h_volume(self, symbol: str, market_type: str = 'spot') -> float:
        """Get 24h volume for symbol."""
        await self.initialize()
        client = self.spot_client if market_type == 'spot' else self.futures_client
        
        try:
            ticker = await self._retry_with_backoff(
                lambda: client.fetch_ticker(symbol)
            )
            return float(ticker.get('quoteVolume', 0))  # USDT volume
        except Exception as e:
            logger.error(f"Error getting 24h volume for {symbol}: {e}")
            return 0.0
