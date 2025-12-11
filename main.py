"""Main entry point for volume alert system."""
import asyncio
import signal
from datetime import datetime
from typing import Dict

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.data.binance_client import BinanceFuturesClient
from src.data.volume_calculator import VolumeCalculator
from src.detector.baseline import BaselineCalculator
from src.detector.spike_detector import SpikeDetector
from src.alert.formatter import AlertFormatter
from src.bot.telegram_bot import TelegramAlertBot

logger = setup_logger("main")


class VolumeAlertSystem:
    """Main volume alert system."""
    
    def __init__(self):
        self.binance_client = BinanceFuturesClient()
        self.volume_calculator = VolumeCalculator()
        self.baseline_calculator = BaselineCalculator()
        self.spike_detector = SpikeDetector()
        self.alert_formatter = AlertFormatter()
        self.telegram_bot = TelegramAlertBot()
        
        self.running = False
        self.stats = {
            'trades_processed': 0,
            'alerts_triggered': 0,
            'symbols_monitored': 0
        }
    
    async def initialize(self):
        """Initialize all components."""
        logger.info("Initializing volume alert system...")
        
        # Validate config
        if not Config.validate():
            raise ValueError("Invalid configuration")
        
        # Initialize Binance client
        await self.binance_client.initialize()
        self.stats['symbols_monitored'] = len(self.binance_client.symbols)
        
        # Initialize Telegram bot
        telegram_enabled = await self.telegram_bot.initialize()
        if telegram_enabled:
            logger.info("Telegram alerts enabled")
        else:
            logger.info("Telegram alerts disabled (using console only)")
        
        logger.info(f"System initialized. Monitoring {self.stats['symbols_monitored']} symbols")
        logger.info(f"Detection parameters:")
        logger.info(f"  - Min volume threshold: {Config.MIN_VOLUME_THRESHOLD:,.0f} USDT")
        logger.info(f"  - Spike ratio threshold: {Config.SPIKE_RATIO_THRESHOLD}x")
        logger.info(f"  - Baseline window: {Config.BASELINE_WINDOW_MINUTES} minutes")
        logger.info(f"  - Cooldown period: {Config.COOLDOWN_PERIOD_MINUTES} minutes")
    
    async def trade_handler(self, symbol: str, price: float, quantity: float, timestamp: float):
        """Handle incoming trade data."""
        try:
            await self.volume_calculator.add_trade(symbol, price, quantity, timestamp)
            self.stats['trades_processed'] += 1
            
            # Log periodically
            if self.stats['trades_processed'] % 1000 == 0:
                logger.debug(f"Processed {self.stats['trades_processed']} trades")
                
        except Exception as e:
            logger.warning(f"Error handling trade for {symbol}: {e}")
    
    async def check_spikes(self):
        """Check for volume spikes across all symbols."""
        current_time = datetime.utcnow()
        current_timestamp = current_time.timestamp()
        
        symbols = await self.volume_calculator.get_all_symbols()
        
        if not symbols:
            return
        
        logger.debug(f"Checking spikes for {len(symbols)} symbols...")
        
        for symbol in symbols:
            try:
                # Get current volume
                current_volume = await self.volume_calculator.get_current_volume(
                    symbol, current_timestamp
                )
                
                if current_volume == 0:
                    continue
                
                # Get volume history for baseline
                history = await self.volume_calculator.get_volume_history(
                    symbol,
                    current_timestamp,
                    minutes_back=Config.BASELINE_WINDOW_MINUTES
                )
                
                if len(history) < 3:
                    # Not enough data yet
                    continue
                
                # Calculate baseline (exclude current interval)
                history_for_baseline = history[:-1] if history else []
                baseline_volume = self.baseline_calculator.calculate_baseline(
                    history_for_baseline,
                    method="median"
                )
                
                if baseline_volume <= 0:
                    continue
                
                # Check for spike
                spike_info = self.spike_detector.check_spike(
                    symbol,
                    current_volume,
                    baseline_volume,
                    current_time
                )
                
                if spike_info:
                    # Spike detected!
                    self.stats['alerts_triggered'] += 1
                    
                    # Format alert messages
                    console_message = self.alert_formatter.format_spike_alert(spike_info, "console")
                    telegram_message = self.alert_formatter.format_spike_alert(spike_info, "telegram")
                    
                    # Console output
                    logger.info("=" * 60)
                    logger.info(console_message)
                    logger.info("=" * 60)
                    
                    # Send Telegram alert
                    await self.telegram_bot.send_alert(telegram_message)
                    
                    # Print stats
                    logger.info(f"Stats: {self.stats['trades_processed']} trades processed, "
                              f"{self.stats['alerts_triggered']} alerts triggered")
                
            except Exception as e:
                logger.warning(f"Error checking spike for {symbol}: {e}")
    
    async def run(self):
        """Run the main monitoring loop."""
        self.running = True
        
        # Start WebSocket in background
        websocket_task = asyncio.create_task(
            self.binance_client.start_websocket(self.trade_handler)
        )
        
        # Wait a bit for initial data
        await asyncio.sleep(10)
        
        logger.info("Starting spike detection loop...")
        
        try:
            while self.running:
                # Check for spikes every UPDATE_INTERVAL seconds
                await self.check_spikes()
                await asyncio.sleep(Config.UPDATE_INTERVAL_SECONDS)
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            raise
        finally:
            self.running = False
            await self.binance_client.close()
            await self.telegram_bot.close()
            websocket_task.cancel()
            
            logger.info("System shutdown complete")
            logger.info(f"Final stats: {self.stats}")


async def main():
    """Main entry point."""
    system = VolumeAlertSystem()
    
    try:
        await system.initialize()
        await system.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info("Received interrupt signal")
        raise KeyboardInterrupt
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Run the system
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Exiting...")
