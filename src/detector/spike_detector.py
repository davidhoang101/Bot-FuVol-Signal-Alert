"""Volume spike detection logic."""
from typing import Dict, Optional
from datetime import datetime, timedelta
import logging

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.detector.baseline import BaselineCalculator

logger = setup_logger(__name__)


class SpikeDetector:
    """Detect volume spikes compared to baseline."""
    
    def __init__(self):
        # Track recent spikes for confirmation
        self.recent_spikes: Dict[str, list] = {}  # {symbol: [spike_ratios]}
        
        # Cooldown tracking: {symbol: last_alert_time}
        self.cooldowns: Dict[str, datetime] = {}
        
        # Maximum retention for cooldowns (cleanup old entries)
        # Constant: 24 hours in minutes
        self.MAX_COOLDOWN_RETENTION_MINUTES = 24 * 60
    
    def check_spike(
        self,
        symbol: str,
        current_volume: float,
        baseline_volume: float,
        current_time: datetime
    ) -> Optional[Dict]:
        """
        Check if current volume represents a spike.
        
        Args:
            symbol: Trading symbol
            current_volume: Current 5-minute volume
            baseline_volume: Calculated baseline volume
            current_time: Current timestamp
        
        Returns:
            Dict with spike info if detected, None otherwise
        """
        # Check minimum volume threshold
        if current_volume < Config.MIN_VOLUME_THRESHOLD:
            return None
        
        # Check baseline is valid
        if baseline_volume <= 0:
            return None
        
        # Calculate spike ratio
        spike_ratio = current_volume / baseline_volume
        
        # Check if ratio exceeds threshold
        if spike_ratio < Config.SPIKE_RATIO_THRESHOLD:
            # Reset recent spikes if below threshold
            if symbol in self.recent_spikes:
                self.recent_spikes[symbol] = []
            return None
        
        # Check cooldown
        if self._is_in_cooldown(symbol, current_time):
            return None
        
        # Track for confirmation
        if symbol not in self.recent_spikes:
            self.recent_spikes[symbol] = []
        
        self.recent_spikes[symbol].append({
            'ratio': spike_ratio,
            'time': current_time,
            'volume': current_volume,
            'baseline': baseline_volume
        })
        
        # Keep only last 3 intervals
        self.recent_spikes[symbol] = self.recent_spikes[symbol][-3:]
        
        # Confirm spike: need at least 2 intervals above threshold
        confirmed_spikes = [
            s for s in self.recent_spikes[symbol]
            if s['ratio'] >= Config.SPIKE_RATIO_THRESHOLD
        ]
        
        if len(confirmed_spikes) >= 2:
            # Spike confirmed!
            latest = confirmed_spikes[-1]
            
            # Update cooldown
            self.cooldowns[symbol] = current_time
            
            # Clear recent spikes
            self.recent_spikes[symbol] = []
            
            return {
                'symbol': symbol,
                'current_volume': latest['volume'],
                'baseline_volume': latest['baseline'],
                'spike_ratio': latest['ratio'],
                'timestamp': latest['time'],
                'confirmed': True
            }
        
        return None
    
    def _is_in_cooldown(self, symbol: str, current_time: datetime) -> bool:
        """Check if symbol is in cooldown period."""
        # Cleanup old cooldowns to prevent memory leak
        self._cleanup_old_cooldowns(current_time)
        
        if symbol not in self.cooldowns:
            return False
        
        last_alert = self.cooldowns[symbol]
        cooldown_delta = timedelta(minutes=Config.COOLDOWN_PERIOD_MINUTES)
        
        return (current_time - last_alert) < cooldown_delta
    
    def _cleanup_old_cooldowns(self, current_time: datetime):
        """Cleanup cooldowns older than retention period to prevent memory leak."""
        cutoff_time = current_time - timedelta(minutes=self.MAX_COOLDOWN_RETENTION_MINUTES)
        self.cooldowns = {
            symbol: alert_time
            for symbol, alert_time in self.cooldowns.items()
            if alert_time >= cutoff_time
        }
        
        # Also cleanup recent_spikes for symbols not in cooldowns
        active_symbols = set(self.cooldowns.keys())
        self.recent_spikes = {
            symbol: spikes
            for symbol, spikes in self.recent_spikes.items()
            if symbol in active_symbols or len(spikes) > 0
        }
    
    def get_cooldown_remaining(self, symbol: str, current_time: datetime) -> int:
        """Get remaining cooldown time in minutes."""
        if symbol not in self.cooldowns:
            return 0
        
        last_alert = self.cooldowns[symbol]
        cooldown_delta = timedelta(minutes=Config.COOLDOWN_PERIOD_MINUTES)
        elapsed = current_time - last_alert
        
        if elapsed >= cooldown_delta:
            return 0
        
        remaining = cooldown_delta - elapsed
        return int(remaining.total_seconds() / 60)
