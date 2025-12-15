#!/usr/bin/env python3
"""Script to switch bot to local instance."""
import asyncio
from telegram import Bot
from telegram.error import Conflict
from src.utils.config import Config

async def main():
    """Switch bot to local instance."""
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    try:
        bot_info = await bot.get_me()
        print(f"✅ Bot: @{bot_info.username}")
        
        # Check webhook
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            print(f"\n⚠️  Webhook is set: {webhook_info.url}")
            print(f"   Deleting webhook to enable polling...")
            await bot.delete_webhook(drop_pending_updates=True)
            print(f"   ✅ Webhook deleted")
        else:
            print(f"\n✅ No webhook (ready for polling)")
        
        # Try to get updates to check if we can poll
        print(f"\n🔍 Checking if local can poll...")
        try:
            updates = await bot.get_updates(limit=1, timeout=2)
            print(f"   ✅ Local bot can poll - Ready!")
            print(f"   → Commands will go to LOCAL")
        except Conflict as e:
            print(f"   ⚠️  CONFLICT: Railway instance is still polling")
            print(f"\n📋 To switch to local:")
            print(f"   1. Go to Railway dashboard")
            print(f"   2. Stop the service/deployment")
            print(f"   3. Wait 10-20 seconds")
            print(f"   4. Restart local bot: python main.py")
            print(f"\n   Or run: kill <railway_process> (if you have access)")
            return
        
        print(f"\n✅ Local bot is ready to receive commands!")
        print(f"   → Make sure local bot is running: python main.py")
        print(f"   → Commands will go to LOCAL instance")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            await bot.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

