#!/usr/bin/env python3
"""Script to check which bot instance is actively receiving updates."""
import asyncio
from telegram import Bot
from telegram.error import Conflict
from src.utils.config import Config

async def main():
    """Check which bot instance is active."""
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    try:
        bot_info = await bot.get_me()
        print(f"✅ Bot: @{bot_info.username}")
        
        # Check webhook
        webhook_info = await bot.get_webhook_info()
        print(f"\n📡 Webhook Status:")
        if webhook_info.url:
            print(f"   ⚠️  Webhook is SET: {webhook_info.url}")
            print(f"   → Commands will go to: WEBHOOK (Railway/Server)")
            print(f"   → Local bot cannot receive commands via polling")
            return
        else:
            print(f"   ✅ No webhook (Polling mode)")
        
        # Try to get updates to see which instance is active
        print(f"\n🔍 Checking which instance is receiving updates...")
        try:
            # This will fail if another instance is polling
            updates = await bot.get_updates(limit=1, timeout=2)
            print(f"   ✅ THIS INSTANCE (Local) can get updates")
            print(f"   → Commands will go to: LOCAL BOT")
            if updates:
                print(f"   📬 Found {len(updates)} pending update(s)")
        except Conflict as e:
            print(f"   ⚠️  CONFLICT: Another instance is polling")
            print(f"   → Commands are going to: RAILWAY/SERVER (other instance)")
            print(f"   → Local bot cannot receive commands")
            print(f"\n💡 Solutions:")
            print(f"   1. Stop bot on Railway (if running)")
            print(f"   2. Or stop local bot if you want Railway to handle commands")
            print(f"   3. Only ONE instance can use polling at a time")
        except Exception as e:
            print(f"   ❌ Error: {e}")
        
        print(f"\n📋 Summary:")
        if webhook_info.url:
            print(f"   • Webhook: {webhook_info.url}")
            print(f"   • Commands → Webhook endpoint (Railway/Server)")
        else:
            print(f"   • Webhook: Not set")
            print(f"   • Commands → Instance that successfully polls")
            print(f"   • Check logs to see which instance is polling successfully")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            await bot.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

