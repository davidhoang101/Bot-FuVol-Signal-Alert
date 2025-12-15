#!/usr/bin/env python3
"""Script to check bot status and diagnose issues."""
import asyncio
import sys
from telegram import Bot
from telegram.error import Conflict
from src.utils.config import Config

async def main():
    """Check bot status."""
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    try:
        # Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot: @{bot_info.username} ({bot_info.first_name})")
        
        # Check webhook
        webhook_info = await bot.get_webhook_info()
        print(f"\n📡 Webhook: {'✅ Not set (Polling OK)' if not webhook_info.url else '⚠️  Set: ' + webhook_info.url}")
        
        # Try to get updates (this will fail if another instance is polling)
        print(f"\n🔍 Checking for polling conflicts...")
        try:
            # Try with very short timeout to check if we can get updates
            updates = await bot.get_updates(limit=1, timeout=1)
            print(f"   ✅ Can get updates - No conflict detected")
            if updates:
                print(f"   📬 Found {len(updates)} pending update(s)")
        except Conflict as e:
            print(f"   ⚠️  CONFLICT DETECTED: Another bot instance is using polling")
            print(f"   Error: {e}")
            print(f"\n💡 Solutions:")
            print(f"   1. If bot is running on Railway:")
            print(f"      - Go to Railway dashboard and STOP the service")
            print(f"      - Or ensure Railway bot is using webhook, not polling")
            print(f"   2. If bot is running locally:")
            print(f"      - Check: ps aux | grep 'python.*main.py'")
            print(f"      - Kill the process if needed")
            print(f"   3. Only ONE instance can use polling at a time")
            return
        except Exception as e:
            print(f"   ❌ Error: {e}")
            return
        
        print(f"\n✅ Bot status: OK")
        print(f"   - Webhook: {'Set' if webhook_info.url else 'Not set (Polling mode)'}")
        print(f"   - Polling: Available")
        print(f"\n💡 Next steps:")
        print(f"   1. Make sure bot is running: python main.py")
        print(f"   2. Send /start to @{bot_info.username} on Telegram")
        print(f"   3. Bot should respond if everything is working")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            await bot.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

