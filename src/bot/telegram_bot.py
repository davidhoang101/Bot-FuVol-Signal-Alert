"""Telegram bot for sending volume spike alerts."""
import asyncio
from typing import Optional, List, Callable
import logging
from datetime import datetime

try:
    from telegram import Bot, Update
    from telegram.error import TelegramError, RetryAfter, TimedOut
    from telegram.ext import Application, CommandHandler, ContextTypes
except ImportError:
    Bot = None
    Update = None
    TelegramError = Exception
    RetryAfter = Exception
    TimedOut = Exception
    Application = None
    CommandHandler = None
    ContextTypes = None

from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class TelegramAlertBot:
    """Telegram bot for sending volume spike alerts."""
    
    def __init__(self):
        self.bot: Optional[Bot] = None
        self.application: Optional[Application] = None
        self.chat_ids: List[str] = []
        self.rate_limit_delay = 0.1  # Delay between messages to avoid rate limits
        self._initialized = False
        self._volume_calculator = None  # Will be set by main system
        self._binance_client = None  # Will be set by main system
        self._command_handler_task = None
    
    def set_volume_calculator(self, volume_calculator):
        """Set volume calculator for command handlers."""
        self._volume_calculator = volume_calculator
    
    def set_binance_client(self, binance_client):
        """Set Binance client for command handlers."""
        self._binance_client = binance_client
    
    async def initialize(self):
        """Initialize Telegram bot."""
        if not Bot or not Application:
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
            
            # Initialize application for command handling
            self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
            
            # Add command handlers
            if CommandHandler:
                self.application.add_handler(CommandHandler("top10", self._handle_top10_command))
                self.application.add_handler(CommandHandler("voltop", self._handle_top10_command))
                self.application.add_handler(CommandHandler("topgainers", self._handle_topgainers_command))
                self.application.add_handler(CommandHandler("gainers", self._handle_topgainers_command))
                self.application.add_handler(CommandHandler("start", self._handle_start_command))
                self.application.add_handler(CommandHandler("help", self._handle_help_command))
            
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
            
            # Start polling for commands in background
            if self.application and CommandHandler:
                await self.application.initialize()
                await self.application.start()
                self._command_handler_task = asyncio.create_task(self._run_polling())
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            return False
    
    async def _run_polling(self):
        """Run polling for commands in background."""
        try:
            if self.application:
                await self.application.updater.start_polling(drop_pending_updates=True)
                logger.info("Telegram bot polling started")
        except Exception as e:
            logger.error(f"Error in polling: {e}")
    
    async def _handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        if not update or not update.message:
            return
        
        chat_id = str(update.message.chat.id)
        if chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)
            logger.info(f"Added new chat ID: {chat_id}")
        
        message = """🤖 <b>Binance Futures Volume Alert Bot</b>

I will send alerts when volume spikes are detected on Binance Futures.

<b>Commands:</b>
/top10 - Top 10 pairs with highest volume (5 minutes)
/voltop - Same as /top10
/topgainers - Top 15 tokens with highest 24h price increase
/gainers - Same as /topgainers
/help - Show help

Start monitoring volume spikes! 🚀"""
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def _handle_help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        if not update or not update.message:
            return
        
        message = """📖 <b>Usage Guide</b>

<b>Commands:</b>
• <code>/top10</code> or <code>/voltop</code> - View top 10 pairs with highest volume in the last 5 minutes
• <code>/topgainers</code> or <code>/gainers</code> - View top 15 tokens with highest 24h price increase
• <code>/start</code> - Start the bot
• <code>/help</code> - Show this help message

<b>Alerts:</b>
The bot will automatically send alerts when volume spikes are detected (volume increases ≥{spike_ratio}x compared to baseline).

<b>Configuration:</b>
• Min Volume Threshold: {min_vol:,.0f} USDT
• Spike Ratio Threshold: {spike_ratio}x
• Baseline Window: {baseline_window} minutes
• Cooldown Period: {cooldown} minutes""".format(
            min_vol=Config.MIN_VOLUME_THRESHOLD,
            spike_ratio=Config.SPIKE_RATIO_THRESHOLD,
            baseline_window=Config.BASELINE_WINDOW_MINUTES,
            cooldown=Config.COOLDOWN_PERIOD_MINUTES
        )
        
        await update.message.reply_text(message, parse_mode='HTML')
    
    async def _handle_top10_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /top10 command."""
        if not update or not update.message:
            return
        
        if not self._volume_calculator:
            await update.message.reply_text("❌ Volume calculator not initialized. Please try again later.")
            return
        
        try:
            current_time = datetime.utcnow().timestamp()
            top_volumes = await self._volume_calculator.get_top_volumes(current_time, top_n=10)
            
            if not top_volumes:
                await update.message.reply_text("📊 No volume data available yet. Please wait a moment...")
                return
            
            # Format message
            message = "📊 <b>TOP 10 PAIRS WITH HIGHEST VOLUME (5 minutes)</b>\n\n"
            
            for i, (symbol, volume) in enumerate(top_volumes, 1):
                vol_str = self._format_volume(volume)
                message += f"{i}. <b>{symbol}</b>: {vol_str} USDT\n"
            
            message += f"\n<i>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error handling top10 command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    async def _handle_topgainers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /topgainers command."""
        if not update or not update.message:
            return
        
        if not self._binance_client:
            await update.message.reply_text("❌ Binance client not initialized. Please try again later.")
            return
        
        try:
            # Get 24h tickers
            await update.message.reply_text("⏳ Fetching 24h data...")
            tickers = await self._binance_client.get_24h_tickers()
            
            if not tickers:
                await update.message.reply_text("📊 No ticker data available. Please try again later.")
                return
            
            # Filter only positive price changes and sort by priceChangePercent descending
            gainers = [
                t for t in tickers 
                if t['priceChangePercent'] > 0
            ]
            gainers.sort(key=lambda x: x['priceChangePercent'], reverse=True)
            
            # Get top 15
            top_gainers = gainers[:15]
            
            if not top_gainers:
                await update.message.reply_text("📊 No gainers found in the last 24h.")
                return
            
            # Format message
            message = "📈 <b>TOP 15 TOKENS - 24H PRICE INCREASE</b>\n\n"
            
            for i, ticker in enumerate(top_gainers, 1):
                symbol = ticker['symbol']
                change_pct = ticker['priceChangePercent']
                price = ticker['lastPrice']
                vol_24h = ticker.get('volume24h', 0)
                
                # Format price
                if price >= 1:
                    price_str = f"${price:,.2f}"
                elif price >= 0.01:
                    price_str = f"${price:.4f}"
                else:
                    price_str = f"${price:.8f}"
                
                # Format volume
                vol_str = self._format_volume(vol_24h)
                
                message += f"{i}. <b>{symbol}</b>\n"
                message += f"   💰 {price_str} | 📈 +{change_pct:.2f}% | 📊 Vol: {vol_str}\n\n"
            
            message += f"<i>Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
            
            await update.message.reply_text(message, parse_mode='HTML')
            
        except Exception as e:
            logger.error(f"Error handling topgainers command: {e}")
            await update.message.reply_text(f"❌ Error: {str(e)}")
    
    def _format_volume(self, volume: float) -> str:
        """Format volume with appropriate units."""
        if volume >= 1_000_000_000:
            return f"{volume / 1_000_000_000:.2f}B"
        elif volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.2f}K"
        else:
            return f"{volume:.2f}"
    
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
        # Stop polling
        if self._command_handler_task:
            self._command_handler_task.cancel()
            try:
                await self._command_handler_task
            except asyncio.CancelledError:
                pass
        
        # Stop application
        if self.application:
            try:
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
            except Exception as e:
                logger.debug(f"Error stopping application: {e}")
        
        # Close bot
        if self.bot:
            try:
                await self.bot.close()
            except Exception:
                pass
        logger.info("Telegram bot closed")

