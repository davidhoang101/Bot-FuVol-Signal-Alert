"""Alert message formatting."""
from typing import Dict, List
from datetime import datetime, timezone


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
                # Use emoji instead of colored spans (Telegram doesn't support inline styles)
                price_info = f"\n<b>Price:</b> ${current_price:.4f} {direction_icon} <b>({change_sign}{price_change_percent:.2f}%)</b>"
            
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
    def format_funding_alert(alert_info: Dict, format_type: str = "console") -> str:
        """
        Format funding rate alert message.
        
        Args:
            alert_info: Dict with funding alert information
            format_type: "console" or "telegram"
        
        Returns:
            Formatted message string
        """
        symbol = alert_info['symbol']
        funding_rate = alert_info['funding_rate']
        funding_rate_percent = alert_info['funding_rate_percent']
        mark_price = alert_info.get('mark_price', 0.0)
        next_funding_time = alert_info.get('next_funding_time', 0)
        alert_type = alert_info.get('alert_type', 'unknown')
        timestamp = alert_info.get('timestamp')
        average_funding_rate = alert_info.get('average_funding_rate')
        change_from_average = alert_info.get('change_from_average')
        
        # Determine alert type description
        if alert_type == 'high_positive':
            icon = "📈"
            description = "HIGH POSITIVE FUNDING RATE"
            explanation = "Longs are paying shorts (bullish sentiment)"
            color = "#ff6b6b"  # Red (costly for longs)
        elif alert_type == 'high_negative':
            icon = "📉"
            description = "HIGH NEGATIVE FUNDING RATE"
            explanation = "Shorts are paying longs (bearish sentiment)"
            color = "#51cf66"  # Green (costly for shorts)
        elif alert_type == 'significant_change':
            icon = "⚡"
            description = "SIGNIFICANT FUNDING RATE CHANGE"
            explanation = "Funding rate changed significantly from average"
            color = "#ffd43b"  # Yellow
        else:
            icon = "💰"
            description = "FUNDING RATE ALERT"
            explanation = ""
            color = "#339af0"  # Blue
        
        # Format funding rate
        funding_str = f"{funding_rate_percent:.4f}%"
        if funding_rate >= 0:
            funding_display = f"+{funding_str}"
        else:
            funding_display = funding_str
        
        # Format next funding time
        if next_funding_time:
            next_funding_dt = datetime.fromtimestamp(next_funding_time / 1000, tz=timezone.utc)
            next_funding_str = next_funding_dt.strftime("%H:%M:%S UTC")
            time_until = (next_funding_dt - datetime.now(timezone.utc)).total_seconds() / 3600
            time_until_str = f"({time_until:.1f}h)"
        else:
            next_funding_str = "N/A"
            time_until_str = ""
        
        # Format timestamp
        if timestamp:
            if isinstance(timestamp, datetime):
                time_str = timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")
            else:
                time_str = str(timestamp)
        else:
            time_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if format_type == "telegram":
            # Telegram format with HTML (no inline styles - Telegram doesn't support them)
            # Use emoji or bold text instead of colored spans
            funding_emoji = "🔴" if alert_type == 'high_positive' else "🟢" if alert_type == 'high_negative' else "🟡"
            message = f"""{icon} <b>{description}</b> {icon}

<b>Symbol:</b> <code>{symbol}</code>
<b>Funding Rate:</b> {funding_emoji} <b>{funding_display}</b>
<b>Mark Price:</b> ${mark_price:,.4f}
<b>Next Funding:</b> {next_funding_str} {time_until_str}"""
            
            if explanation:
                message += f"\n<i>{explanation}</i>"
            
            if average_funding_rate is not None:
                avg_str = f"{average_funding_rate * 100:.4f}%"
                message += f"\n<b>8-Period Average:</b> {avg_str}"
            
            if change_from_average is not None:
                change_str = f"{change_from_average * 100:.4f}%"
                change_sign = "+" if change_from_average >= 0 else ""
                message += f"\n<b>Change from Avg:</b> {change_sign}{change_str}"
            
            message += f"""

<i>Time: {time_str}</i>

<a href="https://www.binance.com/en/futures/{symbol}">View on Binance</a>"""
        else:
            # Console format
            message = f"""
{icon} {description} {icon}

Symbol: {symbol}
Funding Rate: {funding_display}
Mark Price: ${mark_price:,.4f}
Next Funding: {next_funding_str} {time_until_str}"""
            
            if explanation:
                message += f"\n{explanation}"
            
            if average_funding_rate is not None:
                avg_str = f"{average_funding_rate * 100:.4f}%"
                message += f"\n8-Period Average: {avg_str}"
            
            if change_from_average is not None:
                change_str = f"{change_from_average * 100:.4f}%"
                change_sign = "+" if change_from_average >= 0 else ""
                message += f"\nChange from Avg: {change_sign}{change_str}"
            
            message += f"\n\nTime: {time_str}"
        
        return message.strip()
    
    @staticmethod
    def format_funding_scan_summary(
        top_positive: List[Dict],
        top_negative: List[Dict],
        format_type: str = "console"
    ) -> str:
        """
        Format funding rate scan summary.
        
        Args:
            top_positive: List of top positive funding rates
            top_negative: List of top negative funding rates
            format_type: "console" or "telegram"
        
        Returns:
            Formatted summary message
        """
        current_time = datetime.now(timezone.utc)
        time_str = current_time.strftime("%Y-%m-%d %H:%M:%S UTC")
        
        if format_type == "telegram":
            message = "💰 <b>FUNDING RATE SCAN SUMMARY</b> 💰\n\n"
            
            if top_positive:
                message += "📈 <b>TOP POSITIVE FUNDING RATES</b> (Longs pay shorts)\n"
                for i, item in enumerate(top_positive[:10], 1):
                    symbol = item['symbol']
                    rate_pct = item['funding_rate_percent']
                    mark_price = item.get('mark_price', 0)
                    binance_link = f"https://www.binance.com/en/futures/{symbol}"
                    message += f"{i}. <a href=\"{binance_link}\"><b>{symbol}</b></a> "
                    message += f"🔴 <b>+{rate_pct:.4f}%</b> "
                    message += f"(${mark_price:,.4f})\n"
                message += "\n"
            
            if top_negative:
                message += "📉 <b>TOP NEGATIVE FUNDING RATES</b> (Shorts pay longs)\n"
                for i, item in enumerate(top_negative[:10], 1):
                    symbol = item['symbol']
                    rate_pct = item['funding_rate_percent']
                    mark_price = item.get('mark_price', 0)
                    binance_link = f"https://www.binance.com/en/futures/{symbol}"
                    message += f"{i}. <a href=\"{binance_link}\"><b>{symbol}</b></a> "
                    message += f"🟢 <b>{rate_pct:.4f}%</b> "
                    message += f"(${mark_price:,.4f})\n"
                message += "\n"
            
            message += f"<i>Time: {time_str}</i>"
        else:
            message = "\n💰 FUNDING RATE SCAN SUMMARY 💰\n\n"
            
            if top_positive:
                message += "📈 TOP POSITIVE FUNDING RATES (Longs pay shorts)\n"
                for i, item in enumerate(top_positive[:10], 1):
                    symbol = item['symbol']
                    rate_pct = item['funding_rate_percent']
                    mark_price = item.get('mark_price', 0)
                    message += f"{i}. {symbol} +{rate_pct:.4f}% (${mark_price:,.4f})\n"
                message += "\n"
            
            if top_negative:
                message += "📉 TOP NEGATIVE FUNDING RATES (Shorts pay longs)\n"
                for i, item in enumerate(top_negative[:10], 1):
                    symbol = item['symbol']
                    rate_pct = item['funding_rate_percent']
                    mark_price = item.get('mark_price', 0)
                    message += f"{i}. {symbol} {rate_pct:.4f}% (${mark_price:,.4f})\n"
                message += "\n"
            
            message += f"Time: {time_str}\n"
        
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

