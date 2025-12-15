#!/usr/bin/env python3
"""Script to help switch bot from Railway to local."""
import asyncio
import time
import subprocess
import sys
from telegram import Bot
from telegram.error import Conflict
from src.utils.config import Config

async def check_polling_available():
    """Check if polling is available."""
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    try:
        updates = await bot.get_updates(limit=1, timeout=2)
        await bot.close()
        return True, None
    except Conflict as e:
        await bot.close()
        return False, str(e)
    except Exception as e:
        await bot.close()
        return False, str(e)

async def main():
    """Switch bot to local instance."""
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    print("🔄 Switching bot to LOCAL instance...\n")
    
    # Check current status
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    try:
        bot_info = await bot.get_me()
        print(f"✅ Bot: @{bot_info.username}\n")
        
        # Check webhook
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url:
            print(f"⚠️  Webhook is set: {webhook_info.url}")
            print(f"   Deleting webhook...")
            await bot.delete_webhook(drop_pending_updates=True)
            print(f"   ✅ Webhook deleted\n")
        else:
            print(f"✅ No webhook (ready for polling)\n")
        
        await bot.close()
    except Exception as e:
        print(f"❌ Error: {e}")
        return
    
    # Check if polling is available
    print("🔍 Checking if polling is available...")
    can_poll, error = await check_polling_available()
    
    if not can_poll:
        print(f"   ⚠️  CONFLICT: Railway instance is still polling")
        print(f"   Error: {error}\n")
        print("📋 Steps to switch to local:\n")
        print("   1. Go to Railway dashboard: https://railway.app")
        print("   2. Find your project: bot-fuvol-signal-alert")
        print("   3. Click on the service")
        print("   4. Click 'Settings' → 'Delete' or 'Stop'")
        print("   5. Wait 10-20 seconds for Railway to release polling\n")
        print("   6. Then run this script again OR:")
        print("      ./restart_local_bot.sh\n")
        
        # Ask if user wants to wait and retry
        print("💡 Or wait here and I'll check again in 30 seconds...")
        print("   (Press Ctrl+C to cancel)\n")
        
        try:
            for i in range(6):  # Check 6 times, every 5 seconds
                print(f"   Waiting... ({i*5}/30 seconds)", end='\r')
                await asyncio.sleep(5)
                can_poll, error = await check_polling_available()
                if can_poll:
                    print(f"\n   ✅ Polling is now available!")
                    break
            print()
        except KeyboardInterrupt:
            print("\n   Cancelled")
            return
        
        if not can_poll:
            print("   ⚠️  Railway is still polling. Please stop it manually.")
            return
    
    # Polling is available!
    print("   ✅ Polling is available!\n")
    
    # Check if local bot is running
    try:
        result = subprocess.run(
            ["ps", "aux"], 
            capture_output=True, 
            text=True
        )
        local_running = "python" in result.stdout and "main.py" in result.stdout
        
        if local_running:
            print("⚠️  Local bot is already running")
            print("   It should now be able to receive commands!")
            print("   If not, restart it: kill <pid> && python main.py\n")
        else:
            print("📋 Next steps:")
            print("   1. Start local bot: python main.py")
            print("   2. Bot will start polling and receive commands")
            print("   3. Test by sending /start to bot on Telegram\n")
        
        print("✅ Setup complete! Commands will now go to LOCAL bot")
        
    except Exception as e:
        print(f"   Error checking processes: {e}")

if __name__ == "__main__":
    asyncio.run(main())

