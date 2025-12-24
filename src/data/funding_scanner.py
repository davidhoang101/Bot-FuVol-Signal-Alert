"""Binance Futures Funding Rate Scanner with monitoring and alerting."""
import asyncio
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone, timedelta
from collections import defaultdict, deque
import logging

try:
    from binance import AsyncClient
    from binance.exceptions import BinanceAPIException
except ImportError:
    AsyncClient = None
    BinanceAPIException = Exception

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.data.binance_client import RateLimiter

logger = setup_logger(__name__)


class FundingRateData:
    """Data class for funding rate information."""
    
    def __init__(
        self,
        symbol: str,
        funding_rate: float,
        mark_price: float,
        next_funding_time: int,
        timestamp: datetime
    ):
        self.symbol = symbol
        self.funding_rate = funding_rate  # As decimal (e.g., 0.0001 = 0.01%)
        self.funding_rate_percent = funding_rate * 100  # As percentage
        self.mark_price = mark_price
        self.next_funding_time = next_funding_time
        self.timestamp = timestamp
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'symbol': self.symbol,
            'funding_rate': self.funding_rate,
            'funding_rate_percent': self.funding_rate_percent,
            'mark_price': self.mark_price,
            'next_funding_time': self.next_funding_time,
            'timestamp': self.timestamp
        }


class FundingRateHistory:
    """Manages funding rate history for a symbol."""
    
    def __init__(self, max_history: int = 100):
        self.max_history = max_history
        self.history: deque = deque(maxlen=max_history)
        self._lock = asyncio.Lock()
    
    async def add(self, data: FundingRateData):
        """Add funding rate data to history."""
        async with self._lock:
            self.history.append(data)
    
    async def get_latest(self) -> Optional[FundingRateData]:
        """Get latest funding rate data."""
        async with self._lock:
            return self.history[-1] if self.history else None
    
    async def get_history(self, limit: int = None) -> List[FundingRateData]:
        """Get funding rate history."""
        async with self._lock:
            history_list = list(self.history)
            if limit:
                return history_list[-limit:]
            return history_list
    
    async def get_average(self, periods: int = 8) -> Optional[float]:
        """Get average funding rate over last N periods."""
        async with self._lock:
            if len(self.history) < periods:
                return None
            recent = list(self.history)[-periods:]
            return sum(d.funding_rate for d in recent) / len(recent)


class FundingScanner:
    """Binance Futures Funding Rate Scanner."""
    
    def __init__(self, binance_client: Optional[AsyncClient] = None):
        """
        Initialize funding scanner.
        
        Args:
            binance_client: Binance AsyncClient instance (optional, will create if not provided)
        """
        self.client = binance_client
        self._own_client = binance_client is None
        self.rate_limiter = RateLimiter(Config.MAX_REQUESTS_PER_SECOND)
        
        # Funding rate history per symbol
        self.histories: Dict[str, FundingRateHistory] = defaultdict(
            lambda: FundingRateHistory(max_history=100)
        )
        
        # Last scan timestamp
        self.last_scan_time: Optional[datetime] = None
        
        # Cooldown tracking for alerts (symbol -> last alert time)
        self.alert_cooldowns: Dict[str, datetime] = {}
        
        # Statistics
        self.stats = {
            'scans_performed': 0,
            'funding_rates_fetched': 0,
            'alerts_triggered': 0
        }
        self._stats_lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize the funding scanner."""
        if not AsyncClient:
            raise ImportError("python-binance is required for funding scanner")
        
        if not self.client:
            # Create own client if not provided
            import ssl
            import aiohttp
            
            try:
                self.client = await AsyncClient.create(
                    api_key=Config.BINANCE_API_KEY,
                    api_secret=Config.BINANCE_API_SECRET,
                    testnet=Config.BINANCE_TESTNET
                )
            except Exception as ssl_error:
                logger.warning(f"SSL verification failed, using custom SSL context: {ssl_error}")
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                custom_session = aiohttp.ClientSession(connector=connector)
                self.client = AsyncClient(
                    api_key=Config.BINANCE_API_KEY,
                    api_secret=Config.BINANCE_API_SECRET,
                    testnet=Config.BINANCE_TESTNET
                )
                if hasattr(self.client, 'session') and self.client.session:
                    await self.client.session.close()
                self.client.session = custom_session
                await self.client.ping()
        
        logger.info("✅ Funding scanner initialized")
    
    async def fetch_funding_rates(
        self,
        symbols: Optional[List[str]] = None
    ) -> Dict[str, FundingRateData]:
        """
        Fetch current funding rates for symbols.
        
        Args:
            symbols: List of symbols to fetch. If None, fetches all perpetual contracts.
        
        Returns:
            Dictionary mapping symbol to FundingRateData
        """
        if not self.client:
            await self.initialize()
        
        try:
            await self.rate_limiter.acquire()
            # Fetch all perpetual funding rates
            funding_info = await self.client.futures_funding_rate()
            
            result = {}
            current_time = datetime.now(timezone.utc)
            
            # Process funding rate data
            for item in funding_info:
                symbol = item.get('symbol', '')
                
                # Filter by symbols if provided
                if symbols and symbol not in symbols:
                    continue
                
                # Only process USDT perpetual contracts
                if not symbol.endswith('USDT'):
                    continue
                
                try:
                    funding_rate = float(item.get('fundingRate', 0))
                    mark_price = float(item.get('markPrice', 0))
                    next_funding_time = int(item.get('nextFundingTime', 0))
                    
                    funding_data = FundingRateData(
                        symbol=symbol,
                        funding_rate=funding_rate,
                        mark_price=mark_price,
                        next_funding_time=next_funding_time,
                        timestamp=current_time
                    )
                    
                    result[symbol] = funding_data
                    
                    # Store in history
                    await self.histories[symbol].add(funding_data)
                    
                except (ValueError, KeyError) as e:
                    logger.debug(f"Error parsing funding data for {symbol}: {e}")
                    continue
            
            async with self._stats_lock:
                self.stats['funding_rates_fetched'] += len(result)
            
            return result
            
        except BinanceAPIException as e:
            logger.error(f"Binance API error fetching funding rates: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error fetching funding rates: {e}")
            return {}
    
    async def scan_funding_rates(
        self,
        symbols: Optional[List[str]] = None,
        min_funding_rate: Optional[float] = None,
        max_funding_rate: Optional[float] = None
    ) -> Dict[str, FundingRateData]:
        """
        Scan funding rates and return filtered results.
        
        Args:
            symbols: List of symbols to scan. If None, scans all.
            min_funding_rate: Minimum funding rate threshold (as decimal, e.g., 0.001 = 0.1%)
            max_funding_rate: Maximum funding rate threshold (as decimal, e.g., -0.001 = -0.1%)
        
        Returns:
            Dictionary of filtered funding rate data
        """
        funding_rates = await self.fetch_funding_rates(symbols)
        
        if min_funding_rate is None:
            min_funding_rate = Config.MIN_FUNDING_RATE_THRESHOLD
        if max_funding_rate is None:
            max_funding_rate = Config.MAX_FUNDING_RATE_THRESHOLD
        
        # Filter by thresholds
        filtered = {}
        for symbol, data in funding_rates.items():
            if min_funding_rate is not None and data.funding_rate < min_funding_rate:
                continue
            if max_funding_rate is not None and data.funding_rate > max_funding_rate:
                continue
            filtered[symbol] = data
        
        self.last_scan_time = datetime.now(timezone.utc)
        async with self._stats_lock:
            self.stats['scans_performed'] += 1
        
        return filtered
    
    async def get_top_funding_rates(
        self,
        top_n: int = 10,
        highest: bool = True,
        symbols: Optional[List[str]] = None
    ) -> List[FundingRateData]:
        """
        Get top N funding rates (highest or lowest).
        
        Args:
            top_n: Number of top results to return
            highest: If True, return highest rates; if False, return lowest rates
            symbols: Optional list of symbols to filter
        
        Returns:
            List of FundingRateData sorted by funding rate
        """
        funding_rates = await self.fetch_funding_rates(symbols)
        
        # Convert to list and sort
        rates_list = list(funding_rates.values())
        rates_list.sort(key=lambda x: x.funding_rate, reverse=highest)
        
        return rates_list[:top_n]
    
    async def check_funding_rate_alerts(
        self,
        symbols: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Check for funding rate alerts based on configured thresholds.
        
        Args:
            symbols: Optional list of symbols to check
        
        Returns:
            List of alert dictionaries
        """
        funding_rates = await self.fetch_funding_rates(symbols)
        alerts = []
        current_time = datetime.now(timezone.utc)
        
        for symbol, data in funding_rates.items():
            # Check cooldown
            last_alert = self.alert_cooldowns.get(symbol)
            if last_alert:
                time_since_alert = (current_time - last_alert).total_seconds() / 60
                if time_since_alert < Config.FUNDING_ALERT_COOLDOWN_MINUTES:
                    continue
            
            # Check thresholds
            should_alert = False
            alert_type = None
            
            # High positive funding rate (longs pay shorts)
            if data.funding_rate >= Config.HIGH_FUNDING_RATE_THRESHOLD:
                should_alert = True
                alert_type = 'high_positive'
            
            # High negative funding rate (shorts pay longs)
            elif data.funding_rate <= Config.LOW_FUNDING_RATE_THRESHOLD:
                should_alert = True
                alert_type = 'high_negative'
            
            # Significant change from average
            elif Config.FUNDING_RATE_CHANGE_THRESHOLD > 0:
                history = await self.histories[symbol].get_average(periods=8)
                if history is not None:
                    change = abs(data.funding_rate - history)
                    if change >= Config.FUNDING_RATE_CHANGE_THRESHOLD:
                        should_alert = True
                        alert_type = 'significant_change'
            
            if should_alert:
                # Get historical context
                history = await self.histories[symbol].get_average(periods=8)
                
                alert_info = {
                    'symbol': symbol,
                    'funding_rate': data.funding_rate,
                    'funding_rate_percent': data.funding_rate_percent,
                    'mark_price': data.mark_price,
                    'next_funding_time': data.next_funding_time,
                    'alert_type': alert_type,
                    'timestamp': current_time,
                    'average_funding_rate': history,
                    'change_from_average': (data.funding_rate - history) if history else None
                }
                
                alerts.append(alert_info)
                
                # Update cooldown
                self.alert_cooldowns[symbol] = current_time
                
                async with self._stats_lock:
                    self.stats['alerts_triggered'] += 1
        
        return alerts
    
    async def get_funding_rate_history(
        self,
        symbol: str,
        limit: int = 24
    ) -> List[FundingRateData]:
        """
        Get funding rate history for a symbol.
        
        Args:
            symbol: Symbol to get history for
            limit: Maximum number of historical records
        
        Returns:
            List of FundingRateData
        """
        return await self.histories[symbol].get_history(limit=limit)
    
    async def get_funding_rate_stats(self) -> Dict:
        """Get scanner statistics."""
        async with self._stats_lock:
            return self.stats.copy()
    
    async def close(self):
        """Close connections."""
        if self._own_client and self.client:
            await self.client.close_connection()
        logger.info("Funding scanner closed")
