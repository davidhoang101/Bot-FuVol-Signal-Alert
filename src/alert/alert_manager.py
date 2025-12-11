"""
Alert management and formatting for console output (Telegram integration later).
"""
from datetime import datetime
from typing import Dict
import structlog

logger = structlog.get_logger()


class AlertManager:
    """
    Manage and format alerts.
    
    Currently outputs to console, will be extended for Telegram.
    """
    
    def __init__(self):
        """Initialize alert manager."""
        self.alert_count = 0
    
    def format_alert(self, spike_info: Dict) -> str:
        """
        Format spike alert message.
        
        Args:
            spike_info: Spike detection information
            
        Returns:
            Formatted alert message
        """
        symbol = spike_info["symbol"]
        current_volume = spike_info["current_volume"]
        baseline = spike_info["baseline"]
        ratio = spike_info["ratio"]
        timestamp = spike_info["timestamp"]
        
        # Format numbers
        current_vol_str = self._format_volume(current_volume)
        baseline_str = self._format_volume(baseline)
        
        message = f"""
{'='*80}
🚨 VOLUME SPIKE ALERT #{self.alert_count + 1}
{'='*80}
Symbol:        {symbol}
Current 5min:  {current_vol_str} USDT
Baseline:      {baseline_str} USDT
Spike Ratio:   {ratio:.2f}x
Time:          {timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}
{'='*80}
"""
        return message
    
    def _format_volume(self, volume: float) -> str:
        """Format volume with appropriate units."""
        if volume >= 1_000_000_000:
            return f"{volume / 1_000_000_000:.2f}B"
        elif volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.2f}K"
        else:
            return f"{volume:.2f}"
    
    async def send_alert(self, spike_info: Dict):
        """
        Send alert (currently to console).
        
        Args:
            spike_info: Spike detection information
        """
        self.alert_count += 1
        message = self.format_alert(spike_info)
        
        # Console output with color
        print(message)
        
        # Also log
        logger.info(
            "Alert sent",
            symbol=spike_info["symbol"],
            ratio=spike_info["ratio"],
            alert_count=self.alert_count
        )

