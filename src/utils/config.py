"""Configuration management with environment variables."""
import os
from typing import Optional
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


class Config:
    """Application configuration."""
    
    # Binance API
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")
    BINANCE_TESTNET: bool = os.getenv("BINANCE_TESTNET", "false").lower() == "true"
    
    # Detection Parameters
    MIN_VOLUME_THRESHOLD: float = float(os.getenv("MIN_VOLUME_THRESHOLD", "1000000"))
    SPIKE_RATIO_THRESHOLD: float = float(os.getenv("SPIKE_RATIO_THRESHOLD", "2.0"))
    BASELINE_WINDOW_MINUTES: int = int(os.getenv("BASELINE_WINDOW_MINUTES", "60"))
    COOLDOWN_PERIOD_MINUTES: int = int(os.getenv("COOLDOWN_PERIOD_MINUTES", "15"))
    UPDATE_INTERVAL_SECONDS: int = int(os.getenv("UPDATE_INTERVAL_SECONDS", "5"))
    
    # Volume aggregation
    VOLUME_INTERVAL_MINUTES: int = 5  # Fixed 5-minute intervals
    
    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "logs/volume_alert.log")
    
    # Rate limiting (to avoid Binance API limits)
    MAX_REQUESTS_PER_SECOND: int = 10
    WEBSOCKET_RECONNECT_DELAY: int = 5  # seconds
    MAX_RECONNECT_ATTEMPTS: int = 10
    
    # Symbol filtering
    MIN_24H_VOLUME: float = 1000000  # Only monitor symbols with > 1M 24h volume
    MAX_SYMBOLS: int = 200  # Limit number of symbols to monitor
    
    # Telegram Bot
    TELEGRAM_BOT_TOKEN: Optional[str] = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: Optional[str] = os.getenv("TELEGRAM_CHAT_ID")  # Optional: specific chat ID, if None will auto-detect from recent messages
    
    @classmethod
    def validate(cls) -> bool:
        """
        Validate required configuration.
        
        Returns:
            True if configuration is valid, False otherwise
        """
        # Validate numeric parameters
        if cls.MIN_VOLUME_THRESHOLD <= 0:
            logger.error("MIN_VOLUME_THRESHOLD must be > 0")
            return False
        
        if cls.SPIKE_RATIO_THRESHOLD <= 0:
            logger.error("SPIKE_RATIO_THRESHOLD must be > 0")
            return False
        
        if cls.BASELINE_WINDOW_MINUTES <= 0:
            logger.error("BASELINE_WINDOW_MINUTES must be > 0")
            return False
        
        if cls.UPDATE_INTERVAL_SECONDS <= 0:
            logger.error("UPDATE_INTERVAL_SECONDS must be > 0")
            return False
        
        if cls.MAX_SYMBOLS <= 0:
            logger.error("MAX_SYMBOLS must be > 0")
            return False
        
        # API keys are optional for public data (volume)
        return True
