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
        
        # Get price info (if available)
        current_price = spike_info.get('current_price', 0.0)
        baseline_price = spike_info.get('baseline_price', 0.0)
        
        # Determine direction based on PRICE (not volume)
        # Volume spike means volume increased, but we show price direction
        if current_price > 0 and baseline_price > 0:
            price_is_up = current_price > baseline_price
            price_change_percent = ((current_price - baseline_price) / baseline_price) * 100
        else:
            # Fallback to volume if price not available
            price_is_up = current_vol > baseline_vol
            price_change_percent = ((current_vol - baseline_vol) / baseline_vol) * 100
        
        # Choose icon based on PRICE direction
        direction_icon = "📈" if price_is_up else "📉"
        change_sign = "+" if price_is_up else ""
        
        # Volume change (always positive for spike)
        volume_change_percent = ((current_vol - baseline_vol) / baseline_vol) * 100
        
        # Format volumes
        current_vol_str = AlertFormatter._format_volume(current_vol)
        baseline_vol_str = AlertFormatter._format_volume(baseline_vol)
        
        # Format timestamp
        time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if format_type == "telegram":
            # Telegram format with HTML
            price_info = ""
            if current_price > 0 and baseline_price > 0:
                price_info = f"\n<b>Price:</b> ${current_price:.4f} {direction_icon} ({change_sign}{price_change_percent:.2f}%)"
            
            message = f"""{direction_icon} <b>VOLUME SPIKE ALERT</b> {direction_icon}

<b>Symbol:</b> <code>{symbol}</code>
<b>Current 5min Volume:</b> {current_vol_str} USDT (+{volume_change_percent:.1f}%)
<b>Baseline Volume:</b> {baseline_vol_str} USDT
<b>Spike Ratio:</b> <b>{ratio:.2f}x</b>{price_info}

<i>Time: {time_str}</i>

<a href="https://www.binance.com/en/futures/{symbol}">View on Binance</a>"""
        else:
            # Console format
            price_info = ""
            if current_price > 0 and baseline_price > 0:
                price_info = f"\nPrice: ${current_price:.4f} {direction_icon} ({change_sign}{price_change_percent:.2f}%)"
            
            message = f"""
{direction_icon} VOLUME SPIKE ALERT {direction_icon}

Symbol: {symbol}
Current 5min Volume: {current_vol_str} USDT (+{volume_change_percent:.1f}%)
Baseline Volume: {baseline_vol_str} USDT
Spike Ratio: {ratio:.2f}x{price_info}

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

