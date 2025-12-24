"""Simple test script to check API endpoints."""
import asyncio
import sys
from app.exchange.binance_ccxt import BinanceExchangeAdapter
from app.core.config import settings

async def test_exchange():
    """Test exchange adapter."""
    print("Testing Binance Exchange Adapter...")
    print(f"API Key set: {bool(settings.BINANCE_API_KEY)}")
    print(f"Testnet: {settings.BINANCE_ENABLE_TESTNET}")
    
    try:
        exchange = BinanceExchangeAdapter()
        await exchange.initialize()
        print("✅ Exchange initialized successfully")
        
        # Test getting a price
        print("\nTesting price fetch...")
        try:
            price = await exchange.get_perp_price("BTCUSDT")
            print(f"✅ BTCUSDT price: ${price}")
        except Exception as e:
            print(f"❌ Error getting price: {e}")
        
        # Test funding rate
        print("\nTesting funding rate fetch...")
        try:
            funding = await exchange.get_funding_rate("BTCUSDT")
            print(f"✅ BTCUSDT funding rate: {funding}")
        except Exception as e:
            print(f"❌ Error getting funding rate: {e}")
            import traceback
            traceback.print_exc()
        
        await exchange.close()
        
    except Exception as e:
        print(f"❌ Failed to initialize exchange: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(test_exchange())
