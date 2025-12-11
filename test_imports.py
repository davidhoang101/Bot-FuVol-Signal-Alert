#!/usr/bin/env python3
"""Quick test to check if all imports work."""
import sys

def test_imports():
    """Test all imports."""
    print("Testing imports...")
    
    try:
        from src.utils.config import Config
        print("✅ Config imported")
    except Exception as e:
        print(f"❌ Config import failed: {e}")
        return False
    
    try:
        from src.utils.logger import setup_logger
        logger = setup_logger("test")
        print("✅ Logger imported and initialized")
    except Exception as e:
        print(f"❌ Logger import failed: {e}")
        return False
    
    try:
        from binance import AsyncClient, BinanceSocketManager
        print("✅ Binance library imported")
    except ImportError as e:
        print(f"❌ Binance library not found: {e}")
        print("   Run: pip install python-binance")
        return False
    
    try:
        import pandas as pd
        import numpy as np
        print("✅ Data processing libraries imported")
    except ImportError as e:
        print(f"❌ Data processing libraries not found: {e}")
        return False
    
    print("\n✅ All imports successful!")
    return True

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)

