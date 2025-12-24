"""Telegram bot for sending volume spike alerts."""
import asyncio
from typing import Optional, List, Callable
import logging
from datetime import datetime, timezone

try:
    from telegram import Bot, Update, ReplyKeyboardMarkup, KeyboardButton
    from telegram.error import TelegramError, RetryAfter, TimedOut, Conflict
    from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
except ImportError:
    Bot = None
    Update = None
    ReplyKeyboardMarkup = None
    KeyboardButton = None
    TelegramError = Exception
    RetryAfter = Exception
    TimedOut = Exception
    Conflict = Exception
    Application = None
    CommandHandler = None
    ContextTypes = None
    MessageHandler = None
    filters = None

from src.utils.config import Config
from src.utils.logger import setup_logger
from src.detector.baseline import BaselineCalculator

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
        self._baseline_calculator = None  # Will be set by main system
        self._funding_scanner = None  # Will be set by main system
        self._command_handler_task = None
        self._menu_labels = {
            "top10": "📊 Top 10 volume spike (5m)",
            "topgainers": "📈 Top gainers (24h)",
            "funding": "💰 Funding rates scan",
        }
    
    def set_volume_calculator(self, volume_calculator):
        """Set volume calculator for command handlers."""
        self._volume_calculator = volume_calculator
    
    def set_binance_client(self, binance_client):
        """Set Binance client for command handlers."""
        self._binance_client = binance_client
    
    def set_baseline_calculator(self, baseline_calculator):
        """Set baseline calculator for command handlers."""
        self._baseline_calculator = baseline_calculator
    
    def set_funding_scanner(self, funding_scanner):
        """Set funding scanner for command handlers."""
        self._funding_scanner = funding_scanner
    
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
            
            # Ensure webhook is deleted before starting polling
            try:
                webhook_info = await self.bot.get_webhook_info()
                if webhook_info.url:
                    logger.warning(f"Webhook detected: {webhook_info.url}. Deleting to enable polling...")
                    await self.bot.delete_webhook(drop_pending_updates=True)
                    logger.info("✅ Webhook deleted, polling mode enabled")
            except Exception as e:
                logger.debug(f"Error checking/deleting webhook: {e}")
            
            # Initialize application for command handling
            self.application = Application.builder().token(Config.TELEGRAM_BOT_TOKEN).build()
            
            # Add handlers - commands + clickable menu
            if CommandHandler and MessageHandler and filters:
                self.application.add_handler(CommandHandler("top10", self._handle_top10_command))
                self.application.add_handler(CommandHandler("topgainers", self._handle_topgainers_command))
                self.application.add_handler(CommandHandler("funding", self._handle_funding_command))
                self.application.add_handler(CommandHandler("topfunding", self._handle_topfunding_command))
                # Keep start command for adding chat IDs, but simplified
                self.application.add_handler(CommandHandler("start", self._handle_start_command))
                # Menu clicks: any normal text (not a command)
                self.application.add_handler(
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_menu_click)
                )
            
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
                except Conflict as e:
                    # Another bot instance is running - this is expected in production
                    logger.warning(f"Telegram bot conflict when getting updates (another instance running): {e}")
                    logger.warning("Please set TELEGRAM_CHAT_ID in .env file to use alerts")
                except Exception as e:
                    logger.warning(f"Could not get chat IDs from updates: {e}")
                    logger.warning("Please set TELEGRAM_CHAT_ID in .env file")
            
            # Start polling for commands in background
            if self.application and CommandHandler:
                await self.application.initialize()
                await self.application.start()
                self._command_handler_task = asyncio.create_task(self._run_polling())

                # Optional: auto-push scan summary (Top10) periodically
                if Config.TELEGRAM_AUTO_TOP10_INTERVAL_MINUTES > 0:
                    try:
                        interval_seconds = Config.TELEGRAM_AUTO_TOP10_INTERVAL_MINUTES * 60
                        if getattr(self.application, "job_queue", None):
                            self.application.job_queue.run_repeating(
                                self._job_send_top10_summary,
                                interval=interval_seconds,
                                first=10,  # wait a bit after startup
                                name="auto_top10_summary",
                            )
                            logger.info(
                                "✅ Auto Top10 summary enabled every %s minutes",
                                Config.TELEGRAM_AUTO_TOP10_INTERVAL_MINUTES,
                            )
                        else:
                            logger.warning("Job queue not available; cannot schedule auto Top10 summary")
                    except Exception as e:
                        logger.warning(f"Failed to schedule auto Top10 summary: {e}")
            
            self._initialized = True
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Telegram bot: {e}")
            return False
    
    async def _run_polling(self):
        """Run polling for commands in background."""
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                if self.application:
                    # Ensure webhook is deleted before polling
                    try:
                        webhook_info = await self.bot.get_webhook_info()
                        if webhook_info.url:
                            logger.warning(f"Attempt {attempt + 1}: Webhook still exists, deleting...")
                            await self.bot.delete_webhook(drop_pending_updates=True)
                            await asyncio.sleep(1)  # Wait a bit after deleting webhook
                    except Exception as e:
                        logger.debug(f"Error checking webhook: {e}")
                    
                    await self.application.updater.start_polling(
                        drop_pending_updates=True,
                        allowed_updates=["message", "edited_message"]
                    )
                    logger.info("✅ Telegram bot polling started successfully")
                    return  # Success, exit retry loop
                    
            except Conflict as e:
                # Another bot instance is running or webhook conflict
                logger.warning(f"Telegram bot conflict (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                    # Try to delete webhook again
                    try:
                        await self.bot.delete_webhook(drop_pending_updates=True)
                        logger.info("Webhook deleted, retrying polling...")
                    except Exception as del_error:
                        logger.debug(f"Error deleting webhook on retry: {del_error}")
                else:
                    logger.error("❌ Failed to start polling after all retries. Commands will not work.")
                    logger.error("Please ensure no webhook is set and no other bot instance is running.")
                    
            except Exception as e:
                logger.error(f"Error in polling (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("❌ Failed to start polling after all retries.")
    
    async def _handle_start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        logger.info(f"📥 Received /start command")
        if not update or not update.message:
            logger.warning("Update or message is None")
            return
        
        chat_id = str(update.message.chat.id)
        logger.info(f"Processing /start from chat ID: {chat_id}")
        if chat_id not in self.chat_ids:
            self.chat_ids.append(chat_id)
            logger.info(f"Added new chat ID: {chat_id}")
        
        message = """🤖 <b>Binance Futures Volume Alert Bot</b>

I will send alerts when volume spikes are detected on Binance Futures.

<b>Commands:</b>
/top10 - Top 10 pairs with highest volume spike (5 minutes)
/topgainers - Top 15 tokens with highest 24h price increase
/funding - Scan funding rates (top positive & negative)
/topfunding - Top 10 highest and lowest funding rates"""
        
        await update.message.reply_text(
            message,
            parse_mode="HTML",
            reply_markup=self._build_menu_keyboard(),
        )

    def _build_menu_keyboard(self):
        """Build a persistent reply-keyboard menu."""
        if not ReplyKeyboardMarkup or not KeyboardButton:
            return None
        return ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(self._menu_labels["top10"])],
                [KeyboardButton(self._menu_labels["topgainers"])],
                [KeyboardButton(self._menu_labels["funding"])],
            ],
            resize_keyboard=True,
            one_time_keyboard=False,
            input_field_placeholder="Chọn chức năng…",
        )

    async def _handle_menu_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle menu button clicks (text messages)."""
        if not update or not update.message:
            return

        text = (update.message.text or "").strip()
        if text == self._menu_labels["top10"]:
            await self._handle_top10_command(update, context)
            return
        if text == self._menu_labels["topgainers"]:
            await self._handle_topgainers_command(update, context)
            return
        if text == self._menu_labels["funding"]:
            await self._handle_funding_command(update, context)
            return

        # Always keep menu visible; guide user back to buttons
        await update.message.reply_text(
            "Hãy chọn 1 chức năng trong menu bên dưới.",
            reply_markup=self._build_menu_keyboard(),
        )
    
    async def _handle_top10_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /top10 command - shows top 10 pairs with highest volume spike."""
        logger.info(f"📥 Received /top10 command")
        if not update or not update.message:
            logger.warning("Update or message is None")
            return
        
        if not self._volume_calculator or not self._baseline_calculator:
            await update.message.reply_text(
                "❌ Volume calculator or baseline calculator not initialized. Please try again later.",
                reply_markup=self._build_menu_keyboard(),
            )
            return
        
        try:
            message = await self._build_top10_message()
            await update.message.reply_text(
                message,
                parse_mode="HTML",
                reply_markup=self._build_menu_keyboard(),
            )
            
        except Exception as e:
            logger.error(f"Error handling top10 command: {e}")
            await update.message.reply_text(
                f"❌ Error: {str(e)}",
                reply_markup=self._build_menu_keyboard(),
            )

    async def _build_top10_message(self) -> str:
        """Build the Top10 message (shared by command + auto job)."""
        current_time = datetime.now(timezone.utc)
        current_timestamp = current_time.timestamp()

        # Get all symbols with trade data
        symbols = await self._volume_calculator.get_all_symbols()
        if not symbols:
            return "📊 <b>TOP 10</b>\n\nNo volume data available yet. Please wait a moment..."

        spike_data = []
        fallback_volume_data = []

        for symbol in symbols:
            try:
                current_volume = await self._volume_calculator.get_current_volume(symbol, current_timestamp)
                if current_volume == 0:
                    continue

                history = await self._volume_calculator.get_volume_history(
                    symbol,
                    current_timestamp,
                    minutes_back=Config.BASELINE_WINDOW_MINUTES,
                )

                # Need at least 2 intervals (1 baseline, 1 current)
                if len(history) < 2:
                    fallback_volume_data.append(
                        {
                            "symbol": symbol,
                            "current_volume": current_volume,
                        }
                    )
                    continue

                history_for_baseline = history[:-1] if history else []
                baseline_volume = self._baseline_calculator.calculate_baseline(history_for_baseline, method="median")
                if baseline_volume <= 0:
                    fallback_volume_data.append(
                        {
                            "symbol": symbol,
                            "current_volume": current_volume,
                        }
                    )
                    continue

                spike_ratio = current_volume / baseline_volume
                spike_data.append(
                    {
                        "symbol": symbol,
                        "current_volume": current_volume,
                        "baseline_volume": baseline_volume,
                        "spike_ratio": spike_ratio,
                    }
                )
            except Exception as e:
                logger.debug(f"Error calculating spike for {symbol}: {e}")
                continue

        if not spike_data:
            if not fallback_volume_data:
                return "📊 <b>TOP 10</b>\n\nNo volume data available yet. Please wait a few minutes..."

            fallback_volume_data.sort(key=lambda x: x["current_volume"], reverse=True)
            top_items = fallback_volume_data[:10]
            message = "📊 <b>TOP 10 PAIRS - HIGHEST VOLUME (5 minutes)</b>\n"
            message += "<i>⚠️ Not enough data for spike calculation, showing absolute volume</i>\n\n"
            for i, data in enumerate(top_items, 1):
                symbol = data["symbol"]
                current_vol = data["current_volume"]
                vol_str = self._format_volume(current_vol)
                binance_link = f"https://www.binance.com/en/futures/{symbol}"
                message += f'{i}. <a href="{binance_link}"><b>{symbol}</b></a>\n'
                message += f"   📊 Vol: {vol_str} USDT\n\n"
            message += f"<i>Time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
            return message

        spike_data.sort(key=lambda x: x["spike_ratio"], reverse=True)
        top_spikes = spike_data[:10]

        message = "📊 <b>TOP 10 PAIRS - HIGHEST VOLUME SPIKE (5 minutes)</b>\n\n"
        for i, data in enumerate(top_spikes, 1):
            symbol = data["symbol"]
            current_vol = data["current_volume"]
            baseline_vol = data["baseline_volume"]
            spike_ratio = data["spike_ratio"]
            vol_str = self._format_volume(current_vol)
            baseline_str = self._format_volume(baseline_vol)
            binance_link = f"https://www.binance.com/en/futures/{symbol}"
            message += f'{i}. <a href="{binance_link}"><b>{symbol}</b></a>\n'
            message += f"   📊 Vol: {vol_str} | Baseline: {baseline_str} | 🔥 {spike_ratio:.2f}x\n\n"

        message += f"<i>Time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
        return message

    async def _job_send_top10_summary(self, context):
        """Periodic job: push Top10 summary to configured chats."""
        if not self._initialized or not self.bot:
            return
        if not self.chat_ids:
            return
        if not self._volume_calculator or not self._baseline_calculator:
            return
        try:
            message = await self._build_top10_message()
            for cid in self.chat_ids:
                await self.bot.send_message(
                    chat_id=cid,
                    text=message,
                    parse_mode="HTML",
                    disable_web_page_preview=True,
                    reply_markup=self._build_menu_keyboard(),
                )
                await asyncio.sleep(self.rate_limit_delay)
        except Exception as e:
            logger.warning(f"Auto Top10 summary job failed: {e}")
    
    async def _handle_topgainers_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /topgainers command."""
        logger.info(f"📥 Received /topgainers command")
        if not update or not update.message:
            logger.warning("Update or message is None")
            return
        
        if not self._binance_client:
            await update.message.reply_text(
                "❌ Binance client not initialized. Please try again later.",
                reply_markup=self._build_menu_keyboard(),
            )
            return
        
        try:
            # Get 24h tickers
            await update.message.reply_text(
                "⏳ Fetching 24h data...",
                reply_markup=self._build_menu_keyboard(),
            )
            tickers = await self._binance_client.get_24h_tickers()
            
            if not tickers:
                await update.message.reply_text(
                    "📊 No ticker data available. Please try again later.",
                    reply_markup=self._build_menu_keyboard(),
                )
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
                await update.message.reply_text(
                    "📊 No gainers found in the last 24h.",
                    reply_markup=self._build_menu_keyboard(),
                )
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
                
                # Binance Futures link
                binance_link = f"https://www.binance.com/en/futures/{symbol}"
                
                message += f"{i}. <a href=\"{binance_link}\"><b>{symbol}</b></a>\n"
                message += f"   💰 {price_str} | 📈 +{change_pct:.2f}% | 📊 Vol: {vol_str}\n\n"
            
            message += f"<i>Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
            
            await update.message.reply_text(
                message,
                parse_mode="HTML",
                reply_markup=self._build_menu_keyboard(),
            )
            
        except Exception as e:
            logger.error(f"Error handling topgainers command: {e}")
            await update.message.reply_text(
                f"❌ Error: {str(e)}",
                reply_markup=self._build_menu_keyboard(),
            )
    
    async def _handle_funding_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /funding command - scan funding rates."""
        logger.info(f"📥 Received /funding command")
        if not update or not update.message:
            logger.warning("Update or message is None")
            return
        
        if not self._funding_scanner:
            await update.message.reply_text(
                "❌ Funding scanner not enabled or not initialized. Please check configuration.",
                reply_markup=self._build_menu_keyboard(),
            )
            return
        
        try:
            await update.message.reply_text(
                "⏳ Scanning funding rates...",
                reply_markup=self._build_menu_keyboard(),
            )
            
            # Get symbols from binance client if available
            symbols = None
            if self._binance_client and hasattr(self._binance_client, 'symbols'):
                symbols = self._binance_client.symbols
            
            # Get top positive and negative funding rates
            top_positive = await self._funding_scanner.get_top_funding_rates(
                top_n=10, highest=True, symbols=symbols
            )
            top_negative = await self._funding_scanner.get_top_funding_rates(
                top_n=10, highest=False, symbols=symbols
            )
            
            # Convert to dict format for formatter
            from src.alert.formatter import AlertFormatter
            top_positive_dicts = [item.to_dict() for item in top_positive]
            top_negative_dicts = [item.to_dict() for item in top_negative]
            
            # Format message
            message = AlertFormatter.format_funding_scan_summary(
                top_positive_dicts, top_negative_dicts, "telegram"
            )
            
            await update.message.reply_text(
                message,
                parse_mode="HTML",
                reply_markup=self._build_menu_keyboard(),
            )
            
        except Exception as e:
            logger.error(f"Error handling funding command: {e}")
            await update.message.reply_text(
                f"❌ Error: {str(e)}",
                reply_markup=self._build_menu_keyboard(),
            )
    
    async def _handle_topfunding_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /topfunding command - top funding rates."""
        logger.info(f"📥 Received /topfunding command")
        if not update or not update.message:
            logger.warning("Update or message is None")
            return
        
        if not self._funding_scanner:
            await update.message.reply_text(
                "❌ Funding scanner not enabled or not initialized. Please check configuration.",
                reply_markup=self._build_menu_keyboard(),
            )
            return
        
        try:
            await update.message.reply_text(
                "⏳ Fetching top funding rates...",
                reply_markup=self._build_menu_keyboard(),
            )
            
            # Get symbols from binance client if available
            symbols = None
            if self._binance_client and hasattr(self._binance_client, 'symbols'):
                symbols = self._binance_client.symbols
            
            # Get top 10 highest and lowest
            top_highest = await self._funding_scanner.get_top_funding_rates(
                top_n=10, highest=True, symbols=symbols
            )
            top_lowest = await self._funding_scanner.get_top_funding_rates(
                top_n=10, highest=False, symbols=symbols
            )
            
            current_time = datetime.now(timezone.utc)
            message = "💰 <b>TOP FUNDING RATES</b> 💰\n\n"
            
            if top_highest:
                message += "📈 <b>HIGHEST FUNDING RATES</b> (Longs pay shorts)\n"
                for i, item in enumerate(top_highest, 1):
                    symbol = item.symbol
                    rate_pct = item.funding_rate_percent
                    mark_price = item.mark_price
                    binance_link = f"https://www.binance.com/en/futures/{symbol}"
                    message += f"{i}. <a href=\"{binance_link}\"><b>{symbol}</b></a> "
                    message += f"🔴 <b>+{rate_pct:.4f}%</b> "
                    message += f"(${mark_price:,.4f})\n"
                message += "\n"
            
            if top_lowest:
                message += "📉 <b>LOWEST FUNDING RATES</b> (Shorts pay longs)\n"
                for i, item in enumerate(top_lowest, 1):
                    symbol = item.symbol
                    rate_pct = item.funding_rate_percent
                    mark_price = item.mark_price
                    binance_link = f"https://www.binance.com/en/futures/{symbol}"
                    message += f"{i}. <a href=\"{binance_link}\"><b>{symbol}</b></a> "
                    message += f"🟢 <b>{rate_pct:.4f}%</b> "
                    message += f"(${mark_price:,.4f})\n"
                message += "\n"
            
            message += f"<i>Time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
            
            await update.message.reply_text(
                message,
                parse_mode="HTML",
                reply_markup=self._build_menu_keyboard(),
            )
            
        except Exception as e:
            logger.error(f"Error handling topfunding command: {e}")
            await update.message.reply_text(
                f"❌ Error: {str(e)}",
                reply_markup=self._build_menu_keyboard(),
            )
    
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

