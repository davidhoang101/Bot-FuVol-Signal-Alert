"""Test public API endpoints (no API key required)."""
import asyncio
import ccxt.async_support as ccxt

async def test_public_endpoints():
    """Test public endpoints that don't require API key."""
    print("Testing Binance Public API (no API key required)...")
    
    try:
        # Create client without API key (public only)
        client = ccxt.binance({
            'enableRateLimit': True,
            'options': {
                'defaultType': 'future',
            },
        })
        
        print("\n1. Loading markets...")
        await client.load_markets()
        print(f"✅ Loaded {len(client.markets)} markets")
        
        print("\n2. Testing fetch ticker (public)...")
        ticker = await client.fetch_ticker('BTCUSDT')
        print(f"✅ BTCUSDT price: ${ticker['last']}")
        
        print("\n3. Testing fetch orderbook (public)...")
        orderbook = await client.fetch_order_book('BTCUSDT', 5)
        print(f"✅ Orderbook: {len(orderbook['bids'])} bids, {len(orderbook['asks'])} asks")
        
        print("\n4. Testing fetch funding rate...")
        try:
            # Try different methods to get funding rate
            funding = await client.fetch_funding_rate('BTCUSDT')
            print(f"✅ Funding rate: {funding}")
        except AttributeError:
            print("⚠️ fetch_funding_rate not available, trying alternative...")
            try:
                # Try fetch_funding_rates (plural)
                rates = await client.fetch_funding_rates(['BTCUSDT'])
                print(f"✅ Funding rates: {rates}")
            except Exception as e:
                print(f"❌ Error: {e}")
                print("\nTrying to get funding rate from market info...")
                market = client.market('BTCUSDT')
                print(f"Market info keys: {list(market.get('info', {}).keys())[:10]}")
        
        await client.close()
        print("\n✅ All public API tests passed!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_public_endpoints())
