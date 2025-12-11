"""Telegram bot for sending volume spike alerts."""
import asyncio
from typing import Optional, List
import logging

try:
    from telegram import Bot
    from telegram.error import TelegramError, RetryAfter, TimedOut
except ImportError:
    Bot = None
    TelegramError = Exception
    RetryAfter = Exception
    TimedOut = Exception

from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class TelegramAlertBot:
    """Telegram bot for sending volume spike alerts."""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.chat_ids: List[str] = []
        self.rate_limit_delay = 0.1  # Delay between messages to avoid rate limits
        self._initialized = False
    
    async def initialize(self):
        """Initialize Telegram bot."""
        if not Bot:
            logger.warning("python-telegram-bot not installed. Telegram alerts disabled.")
            return False
        
        if not Config.TELEGRAM_BOT_TOKEN:
            logger.warning("TELEGRAM_BOT_TOKEN not set. Telegram alerts disabled.")
            return False
        
        try:
            self.bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
            
            # Test connection
            bot_info = await self.bot.get_me()
            logger.info(f"✅ Telegram bot initialized: @{bot_info.username}")
            
            # Get chat IDs (if specified, or try to get from recent updates)
            if Config.TELEGRAM_CHAT_ID:
                self.chat_ids = [Config.TELEGRAM_CHAT_ID]
                logger.info(f"Using configured chat ID: {Config.TELEGRAM_CHAT_ID}")
            else:
                # Try to get chat ID from recent updates
                try:
                    updates = await self.bot.get_updates(limit=10)
                    if updates:
                        # Get unique chat IDs from recent messages
                        chat_ids_found = set()
                        for update in updates:
                            if update.message:
                                chat_ids_found.add(str(update.message.chat.id))
                        
                        if chat_ids_found:
                            self.chat_ids = list(chat_ids_found)
                            logger.info(f"Found {len(self.chat_ids)} chat ID(s) from recent messages: {self.chat_ids}")
                        else:
                            logger.warning("TELEGRAM_CHAT_ID not set and no recent messages found.")
                            logger.warning("Please send a message to your bot, or set TELEGRAM_CHAT_ID in .env")
                    else:
                        logger.warning("TELEGRAM_CHAT_ID not set and no updates found.")
                        logger.warning("Please send a message to your bot first, or set TELEGRAM_CHAT_ID in .env")
                except Exception as e:
                    logger.warning(f"Could not get chat IDs from updates: {e}")
                    logger.warning("Please set TELEGRAM_CHAT_ID in .env file")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            return False
    
    async def send_alert(self, message: str, chat_id: Optional[str] = None):
        """
        Send alert message to Telegram.
        
        Args:
            message: Alert message to send
            chat_id: Optional chat ID, if None uses configured chat IDs
        """
        if not self._initialized or not self.bot:
            logger.debug("Telegram bot not initialized, skipping alert")
            return False
        
        try:
            # Determine chat IDs to send to
            target_chat_ids = [chat_id] if chat_id else self.chat_ids
            
            if not target_chat_ids:
                logger.warning("No chat IDs configured. Cannot send Telegram alert.")
                return False
            
            # Send to all configured chat IDs
            for cid in target_chat_ids:
                try:
                    await self.bot.send_message(
                        chat_id=cid,
                        text=message,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    logger.info(f"✅ Telegram alert sent to chat {cid}")
                    
                    # Rate limiting - small delay between messages
                    await asyncio.sleep(self.rate_limit_delay)
                    
                except RetryAfter as e:
                    # Rate limited, wait and retry
                    wait_time = e.retry_after
                    logger.warning(f"Telegram rate limit, waiting {wait_time}s")
                    await asyncio.sleep(wait_time)
                    # Retry once
                    try:
                        await self.bot.send_message(
                            chat_id=cid,
                            text=message,
                            parse_mode='HTML',
                            disable_web_page_preview=True
                        )
                    except Exception as retry_error:
                        logger.error(f"Failed to send after rate limit wait: {retry_error}")
                        
                except TimedOut:
                    logger.warning(f"Telegram timeout for chat {cid}, message may not be delivered")
                    
                except TelegramError as e:
                    logger.error(f"Telegram error sending to chat {cid}: {e}")
                    
                except Exception as e:
                    logger.error(f"Unexpected error sending Telegram alert: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending Telegram alert: {e}")
            return False
    
    async def add_chat_id(self, chat_id: str):
        """Add a chat ID to receive alerts."""
        if chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)
            logger.info(f"Added chat ID: {chat_id}")
    
    async def close(self):
        """Close bot connection."""
        if self.bot:
            try:
                await self.bot.close()
            except Exception:
                pass
        logger.info("Telegram bot closed")

