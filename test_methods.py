#!/usr/bin/env python3
"""Test Binance AsyncClient methods."""
import asyncio
from binance import AsyncClient

async def test():
    try:
        client = await AsyncClient.create()
        methods = [m for m in dir(client) if 'ticker' in m.lower() and 'futures' in m.lower()]
        print("Futures ticker methods:", methods)
        
        # Also check all futures methods
        all_futures = [m for m in dir(client) if 'futures' in m.lower()]
        print("\nAll futures methods (first 20):", all_futures[:20])
        
        await client.close_connection()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test())

