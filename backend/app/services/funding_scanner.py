"""Funding rate scanner service."""
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime

from app.exchange.binance_ccxt import BinanceExchangeAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class FundingScannerService:
    """Service for scanning funding rates."""
    
    def __init__(self):
        """Initialize funding scanner service."""
        self.exchange = BinanceExchangeAdapter()
        self._initialized = False
    
    async def initialize(self):
        """Initialize exchange adapter."""
        if not self._initialized:
            await self.exchange.initialize()
            self._initialized = True
    
    async def scan_funding_opportunities(
        self,
        min_rate: Optional[float] = None,
        max_spread_bps: Optional[float] = None,
        quote: str = "USDT",
        exclude_low_volume: bool = True
    ) -> List[Dict]:
        """
        Scan funding opportunities.
        
        Returns list of symbols with funding rate data, sorted by funding rate (descending).
        """
        await self.initialize()
        
        if min_rate is None:
            min_rate = settings.FUNDING_SCANNER_MIN_RATE
        if max_spread_bps is None:
            max_spread_bps = settings.FUNDING_SCANNER_MAX_SPREAD_BPS
        
        try:
            # Get all USDT perpetual symbols
            if not self.exchange.futures_client:
                await self.exchange.initialize()
            
            logger.info("Loading markets...")
            await self.exchange.futures_client.load_markets()
            markets = self.exchange.futures_client.markets
            logger.info(f"Loaded {len(markets)} markets")
            
            # Filter USDT perpetuals
            symbols = [
                symbol for symbol, market in markets.items()
                if market.get('quote') == quote
                and market.get('type') == 'swap'  # Perpetual futures
                and market.get('active', True)
            ]
            
            results = []
            
            # Fetch funding rates and prices for all symbols (with rate limiting)
            semaphore = asyncio.Semaphore(10)  # Limit concurrent requests
            
            async def fetch_symbol_data(symbol: str):
                """Fetch data for a single symbol."""
                async with semaphore:
                    try:
                        # Get funding rate
                        funding_info = await self.exchange.get_funding_rate(symbol)
                        funding_rate = funding_info.get('funding_rate', 0)
                        
                        # Skip if below minimum (only if we have a valid rate)
                        if funding_rate == 0 or funding_rate < min_rate:
                            return None
                        
                        # Get prices
                        spot_price = await self.exchange.get_spot_price(symbol)
                        perp_price = await self.exchange.get_perp_price(symbol)
                        
                        # Calculate basis and spread
                        basis_pct = ((perp_price - spot_price) / spot_price * 100) if spot_price > 0 else 0
                        spread_bps = abs(basis_pct * 100)
                        
                        # Skip if spread too high
                        if spread_bps > max_spread_bps:
                            return None
                        
                        # Get orderbook for liquidity proxy
                        orderbook = await self.exchange.get_orderbook(symbol, 'futures', limit=5)
                        orderbook_spread_bps = orderbook.get('spread_bps', 0)
                        
                        # Get 24h volume
                        volume_24h = await self.exchange.get_24h_volume(symbol, 'futures')
                        
                        # Skip low volume if requested
                        if exclude_low_volume and volume_24h < 1000000:  # 1M USDT minimum
                            return None
                        
                        return {
                            'symbol': symbol,
                            'funding_rate': funding_rate,
                            'funding_rate_percent': funding_rate * 100,
                            'next_funding_time': funding_info.get('next_funding_time'),
                            'spot_price': spot_price,
                            'perp_price': perp_price,
                            'basis_pct': basis_pct,
                            'spread_bps': spread_bps,
                            'orderbook_spread_bps': orderbook_spread_bps,
                            'volume_24h': volume_24h,
                        }
                    except Exception as e:
                        logger.debug(f"Error fetching data for {symbol}: {e}")
                        return None
            
            # Fetch all symbols in parallel
            tasks = [fetch_symbol_data(symbol) for symbol in symbols]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out None and exceptions
            valid_results = [
                r for r in results
                if r is not None and not isinstance(r, Exception)
            ]
            
            # Sort by funding rate (descending)
            valid_results.sort(key=lambda x: x['funding_rate'], reverse=True)
            
            return valid_results
            
        except Exception as e:
            logger.error(f"Error scanning funding opportunities: {e}", exc_info=True)
            raise  # Re-raise to be caught by API endpoint
    
    async def get_symbol_snapshot(self, symbol: str) -> Dict:
        """Get detailed snapshot for a symbol."""
        await self.initialize()
        
        try:
            # Get all relevant data
            spot_price = await self.exchange.get_spot_price(symbol)
            perp_price = await self.exchange.get_perp_price(symbol)
            funding_info = await self.exchange.get_funding_rate(symbol)
            spot_orderbook = await self.exchange.get_orderbook(symbol, 'spot', limit=10)
            perp_orderbook = await self.exchange.get_orderbook(symbol, 'futures', limit=10)
            volume_24h_spot = await self.exchange.get_24h_volume(symbol, 'spot')
            volume_24h_perp = await self.exchange.get_24h_volume(symbol, 'futures')
            
            # Calculate metrics
            basis_pct = ((perp_price - spot_price) / spot_price * 100) if spot_price > 0 else 0
            spread_bps = abs(basis_pct * 100)
            
            return {
                'symbol': symbol,
                'spot_price': spot_price,
                'perp_price': perp_price,
                'basis_pct': basis_pct,
                'spread_bps': spread_bps,
                'funding_rate': funding_info.get('funding_rate', 0),
                'funding_rate_percent': funding_info.get('funding_rate', 0) * 100,
                'next_funding_time': funding_info.get('next_funding_time'),
                'spot_orderbook': spot_orderbook,
                'perp_orderbook': perp_orderbook,
                'volume_24h_spot': volume_24h_spot,
                'volume_24h_perp': volume_24h_perp,
            }
        except Exception as e:
            logger.error(f"Error getting snapshot for {symbol}: {e}")
            raise
