"""Volume calculation and aggregation."""
from typing import Dict, List, Tuple
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
import logging

from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class VolumeCalculator:
    """Calculate and aggregate volume in 5-minute intervals."""
    
    def __init__(self):
        # Store trades: {symbol: [(timestamp, price, quantity), ...]}
        self.trades: Dict[str, List[Tuple[float, float, float]]] = defaultdict(list)
        self.lock = asyncio.Lock()
        
        # Aggregated volume: {symbol: {interval_start: volume}}
        self.volume_intervals: Dict[str, Dict[int, float]] = defaultdict(dict)
        
        # Average prices per interval: {symbol: {interval_start: avg_price}}
        self.price_intervals: Dict[str, Dict[int, float]] = defaultdict(dict)
    
    async def add_trade(self, symbol: str, price: float, quantity: float, timestamp: float):
        """Add a trade to the collection."""
        async with self.lock:
            self.trades[symbol].append((timestamp, price, quantity))
            
            # Clean old trades (older than 2 hours)
            cutoff_time = timestamp - 7200  # 2 hours
            self.trades[symbol] = [
                t for t in self.trades[symbol] 
                if t[0] >= cutoff_time
            ]
    
    def _get_interval_start(self, timestamp: float) -> int:
        """Get the start timestamp of the 5-minute interval."""
        # Round down to nearest 5-minute interval
        interval_seconds = Config.VOLUME_INTERVAL_MINUTES * 60
        return int(timestamp // interval_seconds) * interval_seconds
    
    async def aggregate_volume(self, symbol: str, current_time: float) -> Dict[int, float]:
        """Aggregate volume for a symbol into 5-minute intervals."""
        async with self.lock:
            if symbol not in self.trades:
                return {}
            
            # Get current interval start
            current_interval = self._get_interval_start(current_time)
            
            # Aggregate trades into intervals
            interval_volumes: Dict[int, float] = defaultdict(float)
            interval_prices: Dict[int, List[float]] = defaultdict(list)  # Store prices for averaging
            
            for timestamp, price, quantity in self.trades[symbol]:
                interval_start = self._get_interval_start(timestamp)
                
                # Only include intervals up to current
                if interval_start <= current_interval:
                    # Calculate quote volume (USDT)
                    quote_volume = price * quantity
                    interval_volumes[interval_start] += quote_volume
                    # Store price for averaging
                    interval_prices[interval_start].append(price)
            
            # Calculate average prices per interval
            avg_prices: Dict[int, float] = {}
            for interval_start, prices in interval_prices.items():
                if prices:
                    avg_prices[interval_start] = sum(prices) / len(prices)
            
            # Update stored intervals
            self.volume_intervals[symbol] = dict(interval_volumes)
            self.price_intervals[symbol] = avg_prices
            
            return interval_volumes
    
    async def get_current_volume(self, symbol: str, current_time: float) -> float:
        """Get volume for the current 5-minute interval."""
        intervals = await self.aggregate_volume(symbol, current_time)
        current_interval = self._get_interval_start(current_time)
        return intervals.get(current_interval, 0.0)
    
    async def get_volume_history(
        self, 
        symbol: str, 
        current_time: float,
        minutes_back: int = 60
    ) -> List[Tuple[int, float]]:
        """Get volume history for the last N minutes."""
        intervals = await self.aggregate_volume(symbol, current_time)
        current_interval = self._get_interval_start(current_time)
        
        # Get intervals within the time window
        cutoff_interval = current_interval - (minutes_back * 60)
        
        history = [
            (interval_start, volume)
            for interval_start, volume in intervals.items()
            if cutoff_interval <= interval_start <= current_interval
        ]
        
        # Sort by timestamp
        history.sort(key=lambda x: x[0])
        
        return history
    
    async def get_all_symbols(self) -> List[str]:
        """Get list of all symbols with trade data."""
        async with self.lock:
            return list(self.trades.keys())
    
    async def get_top_volumes(self, current_time: float, top_n: int = 10) -> List[Tuple[str, float]]:
        """
        Get top N symbols by current volume.
        
        Args:
            current_time: Current timestamp
            top_n: Number of top symbols to return
            
        Returns:
            List of (symbol, volume) tuples sorted by volume descending
        """
        symbols = await self.get_all_symbols()
        if not symbols:
            return []
        
        # Get current volume for all symbols
        volumes = []
        for symbol in symbols:
            volume = await self.get_current_volume(symbol, current_time)
            if volume > 0:
                volumes.append((symbol, volume))
        
        # Sort by volume descending
        volumes.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N
        return volumes[:top_n]
    
    async def get_current_price(self, symbol: str, current_time: float) -> float:
        """
        Get average price for the current 5-minute interval.
        
        Args:
            symbol: Trading symbol
            current_time: Current timestamp
            
        Returns:
            Average price for current interval, or 0.0 if no data
        """
        # Ensure prices are calculated
        await self.aggregate_volume(symbol, current_time)
        current_interval = self._get_interval_start(current_time)
        return self.price_intervals.get(symbol, {}).get(current_interval, 0.0)
    
    async def get_baseline_price(self, symbol: str, current_time: float, minutes_back: int = 60) -> float:
        """
        Get baseline (average) price from history.
        
        Args:
            symbol: Trading symbol
            current_time: Current timestamp
            minutes_back: Minutes to look back for baseline
            
        Returns:
            Average baseline price, or 0.0 if no data
        """
        await self.aggregate_volume(symbol, current_time)
        current_interval = self._get_interval_start(current_time)
        cutoff_interval = current_interval - (minutes_back * 60)
        
        prices = []
        for interval_start, price in self.price_intervals.get(symbol, {}).items():
            # Exclude current interval and only include history
            if cutoff_interval <= interval_start < current_interval:
                prices.append(price)
        
        if not prices:
            return 0.0
        
        # Return median price (more robust than average)
        prices.sort()
        mid = len(prices) // 2
        if len(prices) % 2 == 0:
            return (prices[mid - 1] + prices[mid]) / 2
        else:
            return prices[mid]