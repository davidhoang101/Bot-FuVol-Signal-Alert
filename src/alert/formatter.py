"""Alert message formatting."""
from typing import Dict
from datetime import datetime


class AlertFormatter:
    """Format spike alerts for display."""
    
    @staticmethod
    def format_spike_alert(spike_info: Dict, format_type: str = "console") -> str:
        """
        Format spike alert message.
        
        Args:
            spike_info: Dict with spike information
            format_type: "console" or "telegram"
        
        Returns:
            Formatted message string
        """
        symbol = spike_info['symbol']
        current_vol = spike_info['current_volume']
        baseline_vol = spike_info['baseline_volume']
        ratio = spike_info['spike_ratio']
        timestamp = spike_info['timestamp']
        
        # Format volumes
        current_vol_str = AlertFormatter._format_volume(current_vol)
        baseline_vol_str = AlertFormatter._format_volume(baseline_vol)
        
        # Format timestamp
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if format_type == "telegram":
            # Telegram format with HTML
            message = f"""🚨 <b>VOLUME SPIKE ALERT</b> 🚨

<b>Symbol:</b> <code>{symbol}</code>
<b>Current 5min Volume:</b> {current_vol_str} USDT
<b>Baseline Volume:</b> {baseline_vol_str} USDT
<b>Spike Ratio:</b> <b>{ratio:.2f}x</b>

<i>Time: {time_str}</i>

<a href="https://www.binance.com/en/futures/{symbol}">View on Binance</a>"""
        else:
            # Console format
            message = f"""
🚨 VOLUME SPIKE ALERT 🚨

Symbol: {symbol}
Current 5min Volume: {current_vol_str} USDT
Baseline Volume: {baseline_vol_str} USDT
Spike Ratio: {ratio:.2f}x

Time: {time_str}
"""
        
        return message.strip()
    
    @staticmethod
    def _format_volume(volume: float) -> str:
        """Format volume with appropriate units."""
        if volume >= 1_000_000_000:
            return f"{volume / 1_000_000_000:.2f}B"
        elif volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.2f}K"
        else:
            return f"{volume:.2f}"

