#!/usr/bin/env python3
"""Script to delete webhook and enable polling mode."""
import asyncio
from telegram import Bot
from src.utils.config import Config

async def main():
    """Delete webhook to enable polling."""
    if not Config.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set!")
        return
    
    bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
    
    try:
        # Get bot info
        bot_info = await bot.get_me()
        print(f"✅ Bot: @{bot_info.username} ({bot_info.first_name})")
        
        # Get current webhook info
        webhook_info = await bot.get_webhook_info()
        
        if webhook_info.url:
            print(f"\n⚠️  Webhook đang được set: {webhook_info.url}")
            print("   Đang xóa webhook để enable polling mode...")
            
            # Delete webhook
            result = await bot.delete_webhook(drop_pending_updates=True)
            if result:
                print("✅ Đã xóa webhook thành công!")
                print("   Bot giờ có thể dùng polling mode để nhận commands.")
        else:
            print("\n✅ Không có webhook nào được set.")
            print("   Bot đang ở polling mode.")
        
        # Verify
        webhook_info_after = await bot.get_webhook_info()
        if not webhook_info_after.url:
            print("\n✅ Xác nhận: Không có webhook, bot sẵn sàng cho polling mode.")
        else:
            print(f"\n⚠️  Vẫn còn webhook: {webhook_info_after.url}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        try:
            await bot.close()
        except Exception:
            pass

if __name__ == "__main__":
    asyncio.run(main())

