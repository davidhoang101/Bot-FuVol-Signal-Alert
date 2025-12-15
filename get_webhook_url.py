#!/usr/bin/env python3
"""Script to get current webhook URL of Telegram bot."""
import asyncio
from telegram import Bot
from src.utils.config import Config

async def main():
    """Get webhook info from bot."""
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    try:
        # Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot: @{bot_info.username} ({bot_info.first_name})")
        
        # Get webhook info
        webhook_info = await bot.get_webhook_info()
        
        print("\n📡 Webhook Information:")
        print("=" * 60)
        
        if webhook_info.url:
            print(f"✅ Webhook URL: {webhook_info.url}")
            print(f"   Pending updates: {webhook_info.pending_update_count}")
            print(f"   Last error date: {webhook_info.last_error_date or 'None'}")
            print(f"   Last error message: {webhook_info.last_error_message or 'None'}")
            print(f"   Max connections: {webhook_info.max_connections or 'None'}")
            print(f"   Allowed updates: {webhook_info.allowed_updates or 'All'}")
        else:
            print("⚠️  No webhook is set. Bot is using polling mode.")
            print("\n💡 To set a webhook, use:")
            print(f"   curl -X POST https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook?url=YOUR_WEBHOOK_URL")
            print("\n   Or visit:")
            print(f"   https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/setWebhook?url=YOUR_WEBHOOK_URL")
        
        print("=" * 60)
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            await bot.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

