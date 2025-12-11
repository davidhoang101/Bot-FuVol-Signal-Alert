#!/usr/bin/env python3
"""Script to get Telegram chat ID."""
import asyncio
from telegram import Bot
from src.utils.config import Config

async def main():
    """Get chat ID from bot."""
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    try:
        # Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot: @{bot_info.username} ({bot_info.first_name})")
        print("\n📱 To get your chat ID:")
        print("1. Start a chat with your bot on Telegram")
        print("2. Send any message to the bot")
        print("3. Run this command to get updates:")
        print(f"   curl https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/getUpdates")
        print("\n   Or visit:")
        print(f"   https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}/getUpdates")
        print("\n   Look for 'chat': {'id': YOUR_CHAT_ID}")
        print("\n   Then set in .env:")
        print("   TELEGRAM_CHAT_ID=YOUR_CHAT_ID")
        
        # Try to get updates
        updates = await bot.get_updates()
        if updates:
            print("\n📬 Recent updates:")
            for update in updates[-5:]:  # Last 5 updates
                if update.message:
                    chat_id = update.message.chat.id
                    print(f"   Chat ID: {chat_id} (from @{update.message.chat.username or update.message.chat.first_name})")
        else:
            print("\n⚠️  No updates found. Send a message to your bot first!")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            await bot.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

