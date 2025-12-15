#!/usr/bin/env python3
"""Script to test if bot can receive commands."""
import asyncio
from telegram import Bot
from src.utils.config import Config

async def main():
    """Test bot command reception."""
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    try:
        # Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot: @{bot_info.username} ({bot_info.first_name})")
        
        # Check webhook status
        webhook_info = await bot.get_webhook_info()
        print(f"\n📡 Webhook Status: {'Set' if webhook_info.url else 'Not set (Polling mode)'}")
        if webhook_info.url:
            print(f"   URL: {webhook_info.url}")
            print(f"   ⚠️  Webhook is set! Bot cannot use polling mode.")
            print(f"   Run: python delete_webhook.py")
        else:
            print(f"   ✅ No webhook, bot can use polling mode")
        
        # Try to get recent updates
        print(f"\n📬 Checking for recent updates...")
        try:
            updates = await bot.get_updates(limit=5, timeout=5)
            if updates:
                print(f"   ✅ Found {len(updates)} recent update(s)")
                for update in updates:
                    if update.message:
                        chat_id = update.message.chat.id
                        text = update.message.text or "(no text)"
                        print(f"   - Chat ID: {chat_id}, Text: {text[:50]}")
            else:
                print(f"   ⚠️  No recent updates found")
                print(f"   💡 Send a message to your bot to test")
        except Exception as e:
            print(f"   ❌ Error getting updates: {e}")
        
        print(f"\n💡 To test bot commands:")
        print(f"   1. Make sure bot is running (python main.py)")
        print(f"   2. Send /start or /help to @{bot_info.username} on Telegram")
        print(f"   3. Bot should respond if polling is working")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            await bot.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

