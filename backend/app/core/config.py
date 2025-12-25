"""Application configuration."""
import os
import yaml
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load .env file
load_dotenv()

# Load config.yaml
CONFIG_FILE = Path(__file__).parent.parent.parent.parent / "config.yaml"
config_data = {}
if CONFIG_FILE.exists():
    with open(CONFIG_FILE, 'r') as f:
        config_data = yaml.safe_load(f) or {}


class Settings(BaseSettings):
    """Application settings."""
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = int(os.getenv("PORT", "8000"))  # Railway sets PORT env var
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # CORS - Allow all origins by default (can restrict via CORS_ORIGINS env var)
    _cors_origins_env = os.getenv("CORS_ORIGINS", "")
    CORS_ORIGINS: List[str] = (
        _cors_origins_env.split(",") if _cors_origins_env 
        else ["*"]  # Allow all in production
    )
    
    # Binance API
    BINANCE_API_KEY: Optional[str] = os.getenv("BINANCE_API_KEY")
    BINANCE_API_SECRET: Optional[str] = os.getenv("BINANCE_API_SECRET")
    BINANCE_ENABLE_TESTNET: bool = os.getenv("BINANCE_ENABLE_TESTNET", "false").lower() == "true"
    
    # Database
    DATABASE_URL: str = "sqlite:///./trading_console.db"
    
    # Funding Scanner Config
    FUNDING_SCANNER_MIN_RATE: float = config_data.get("funding_scanner", {}).get("min_rate", 0.0002)
    FUNDING_SCANNER_MAX_SPREAD_BPS: float = config_data.get("funding_scanner", {}).get("max_spread_bps", 8.0)
    FUNDING_SCANNER_REFRESH_SEC: int = config_data.get("funding_scanner", {}).get("refresh_sec", 10)
    
    # Trading Config
    TRADING_MAX_NOTIONAL_PER_SYMBOL: float = config_data.get("trading", {}).get("max_notional_per_symbol", 2000.0)
    TRADING_MAX_TOTAL_NOTIONAL: float = config_data.get("trading", {}).get("max_total_notional", 5000.0)
    TRADING_MIN_FREE_MARGIN_PCT: float = config_data.get("trading", {}).get("min_free_margin_pct", 30.0)
    TRADING_DEFAULT_LEVERAGE: int = config_data.get("trading", {}).get("default_leverage", 1)
    TRADING_TAKER_FEE_BPS_SPOT: float = config_data.get("trading", {}).get("taker_fee_bps_spot", 10.0)
    TRADING_TAKER_FEE_BPS_PERP: float = config_data.get("trading", {}).get("taker_fee_bps_perp", 4.0)
    TRADING_PAPER_MODE: bool = config_data.get("trading", {}).get("paper_mode", True)
    
    # Auth (minimal - single admin password or token)
    ADMIN_PASSWORD: Optional[str] = os.getenv("ADMIN_PASSWORD")
    ADMIN_TOKEN: Optional[str] = os.getenv("ADMIN_TOKEN")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
