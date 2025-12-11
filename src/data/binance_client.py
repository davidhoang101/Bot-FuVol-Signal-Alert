"""Binance Futures API client with WebSocket support and rate limiting."""
import asyncio
import time
from typing import Dict, List, Optional, Callable
from collections import deque
from datetime import datetime, timedelta
import logging

try:
    from binance import AsyncClient, BinanceSocketManager
    from binance.exceptions import BinanceAPIException
except ImportError:
    # Fallback if python-binance is not available
    AsyncClient = None
    BinanceSocketManager = None
    BinanceAPIException = Exception

from src.utils.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)


class RateLimiter:
    """Simple rate limiter to avoid API limits."""
    
    def __init__(self, max_requests: int, time_window: float = 1.0):
        self.max_requests = max_requests
        self.time_window = time_window
        self.requests = deque()
    
    async def acquire(self):
        """Wait if necessary to respect rate limit."""
        now = time.time()
        
        # Remove old requests outside the time window
        while self.requests and self.requests[0] < now - self.time_window:
            self.requests.popleft()
        
        # If we're at the limit, wait
        if len(self.requests) >= self.max_requests:
            sleep_time = self.time_window - (now - self.requests[0])
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
                # Clean up again after sleep
                while self.requests and self.requests[0] < now:
                    self.requests.popleft()
        
        self.requests.append(time.time())


class BinanceFuturesClient:
    """Binance Futures client with WebSocket for real-time data."""
    
    def __init__(self):
        self.client: Optional[AsyncClient] = None
        self.socket_manager: Optional[BinanceSocketManager] = None
        self.rate_limiter = RateLimiter(Config.MAX_REQUESTS_PER_SECOND)
        self.symbols: List[str] = []
        self.trade_callbacks: Dict[str, Callable] = {}
        self.reconnect_attempts = 0
        self._running = False
    
    async def initialize(self):
        """Initialize Binance client."""
        try:
            # Initialize client (API keys optional for public data)
            # Note: SSL verification may fail in some network environments (proxy/firewall)
            # For development, we disable SSL verification
            # WARNING: Only use this in development, not production!
            import ssl
            import aiohttp
            
            # Try normal initialization first
            try:
                self.client = await AsyncClient.create(
                    api_key=Config.BINANCE_API_KEY,
                    api_secret=Config.BINANCE_API_SECRET,
                    testnet=Config.BINANCE_TESTNET
                )
            except Exception as ssl_error:
                # If SSL error, create client with custom SSL context
                logger.warning(f"SSL verification failed, using custom SSL context: {ssl_error}")
                
                # Create SSL context that allows unverified certificates (for development)
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # Create connector with custom SSL context
                connector = aiohttp.TCPConnector(ssl=ssl_context)
                
                # Create session with custom connector
                custom_session = aiohttp.ClientSession(connector=connector)
                
                # Create client without ping (we'll do it manually)
                self.client = AsyncClient(
                    api_key=Config.BINANCE_API_KEY,
                    api_secret=Config.BINANCE_API_SECRET,
                    testnet=Config.BINANCE_TESTNET
                )
                
                # Replace session with custom one
                if hasattr(self.client, 'session') and self.client.session:
                    await self.client.session.close()
                self.client.session = custom_session
                
                # Test connection with custom session
                await self.client.ping()
            
            # Get active futures symbols
            await self._load_symbols()
            
            logger.info(f"Initialized Binance client. Monitoring {len(self.symbols)} symbols")
            
        except Exception as e:
            logger.error(f"Failed to initialize Binance client: {e}")
            raise
    
    async def _load_symbols(self):
        """Load active futures symbols with sufficient volume."""
        try:
            await self.rate_limiter.acquire()
            exchange_info = await self.client.futures_exchange_info()
            
            # Filter symbols: USDT pairs, active, perpetual contracts
            symbols = []
            for symbol_info in exchange_info['symbols']:
                # Check if symbol is trading and is USDT perpetual
                status = symbol_info.get('status', '')
                quote_asset = symbol_info.get('quoteAsset', '')
                contract_type = symbol_info.get('contractType', '')
                
                if (status == 'TRADING' and 
                    quote_asset == 'USDT' and
                    contract_type == 'PERPETUAL'):
                    symbols.append(symbol_info['symbol'])
            
            logger.info(f"Found {len(symbols)} active USDT perpetual contracts")
            
            # Get 24h ticker to filter by volume
            # Try to get all tickers at once, fallback to individual calls if needed
            tickers = []
            try:
                await self.rate_limiter.acquire()
                # Try common method names
                if hasattr(self.client, 'futures_ticker'):
                    tickers = await self.client.futures_ticker()
                elif hasattr(self.client, 'futures_24hr_ticker'):
                    tickers = await self.client.futures_24hr_ticker()
                elif hasattr(self.client, 'get_futures_ticker'):
                    tickers = await self.client.get_futures_ticker()
                else:
                    raise AttributeError("No ticker method found")
            except (AttributeError, Exception) as e:
                logger.warning(f"Could not get all tickers at once ({e}), using symbol list directly")
                # If we can't get tickers, just use all symbols (filtering will happen later)
                self.symbols = symbols[:Config.MAX_SYMBOLS]
                logger.info(f"Loaded {len(self.symbols)} symbols (no volume filtering)")
                return
            
            # Filter by minimum 24h volume and limit count
            if tickers:
                # Handle both list and dict formats
                if isinstance(tickers, dict):
                    tickers = [tickers]
                
                volume_map = {}
                for t in tickers:
                    symbol = t.get('symbol', '')
                    quote_vol = float(t.get('quoteVolume', t.get('quoteQty', 0)))
                    if symbol and quote_vol > 0:
                        volume_map[symbol] = quote_vol
                
                # Filter by minimum 24h volume
                filtered = [
                    s for s in symbols 
                    if volume_map.get(s, 0) >= Config.MIN_24H_VOLUME
                ]
                
                logger.info(f"Filtered to {len(filtered)} symbols with volume >= {Config.MIN_24H_VOLUME:,.0f} USDT")
                
                # Sort by volume and take top N
                filtered.sort(key=lambda s: volume_map.get(s, 0), reverse=True)
                self.symbols = filtered[:Config.MAX_SYMBOLS]
                
                # Log some sample symbols for debugging
                if self.symbols:
                    logger.info(f"Sample symbols: {', '.join(self.symbols[:10])}")
            else:
                # No ticker data, just use all symbols
                self.symbols = symbols[:Config.MAX_SYMBOLS]
            
            logger.info(f"✅ Loaded {len(self.symbols)} symbols (min 24h volume: {Config.MIN_24H_VOLUME:,.0f} USDT, max: {Config.MAX_SYMBOLS})")
            
            # Verify symbols exist by checking a few
            if self.symbols:
                sample_symbol = self.symbols[0]
                try:
                    await self.rate_limiter.acquire()
                    # Try to get ticker for verification
                    if hasattr(self.client, 'futures_symbol_ticker'):
                        ticker = await self.client.futures_symbol_ticker(symbol=sample_symbol)
                    elif hasattr(self.client, 'futures_ticker') and callable(getattr(self.client, 'futures_ticker', None)):
                        # futures_ticker() might need symbol parameter
                        tickers = await self.client.futures_ticker()
                        # Check if sample_symbol is in the list
                        if isinstance(tickers, list):
                            found = any(t.get('symbol') == sample_symbol for t in tickers)
                            if found:
                                logger.info(f"✅ Verified symbol {sample_symbol} exists on Binance Futures")
                            else:
                                logger.warning(f"⚠️ Symbol {sample_symbol} not found in ticker list")
                    else:
                        logger.debug(f"Could not verify symbol (no verification method available)")
                except Exception as e:
                    logger.debug(f"Could not verify symbol {sample_symbol}: {e}")
            
        except BinanceAPIException as e:
            logger.error(f"Binance API error loading symbols: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading symbols: {e}")
            raise
    
    async def start_websocket(self, trade_callback: Callable):
        """Start WebSocket streams for all symbols."""
        if not self.client:
            await self.initialize()
        
        try:
            self.socket_manager = BinanceSocketManager(self.client)
            self._running = True
            
            # Create aggregate stream for all symbols
            streams = [f"{symbol.lower()}@trade" for symbol in self.symbols]
            
            # Start aggregate stream (more efficient than individual streams)
            # Note: Binance has a limit on number of streams and URL length
            # Use smaller batches to avoid HTTP 400 errors
            # Binance typically allows up to 200 streams, but URL length may be limited
            batch_size = 20  # Further reduced to ensure URL stays within limits
            tasks = []
            
            for i in range(0, len(streams), batch_size):
                batch = streams[i:i + batch_size]
                task = self._start_batch_stream(batch, trade_callback)
                tasks.append(task)
            
            logger.info(f"Started {len(tasks)} WebSocket streams for {len(self.symbols)} symbols")
            
            # Wait for all streams
            await asyncio.gather(*tasks, return_exceptions=True)
            
        except Exception as e:
            logger.error(f"Error starting WebSocket: {e}")
            self._running = False
            raise
    
    async def _start_batch_stream(self, streams: List[str], callback: Callable):
        """Start a batch of WebSocket streams using individual connections."""
        import websockets
        import websockets.exceptions
        import json
        
        async def handle_message(msg_str: str, symbol: str = None):
            """Handle incoming WebSocket message."""
            if not self._running:
                return
            
            try:
                msg = json.loads(msg_str)
                # Handle both multiplex format (with 'data' key) and direct format
                if 'data' in msg:
                    trade_data = msg['data']
                else:
                    trade_data = msg
                
                symbol = trade_data.get('s', symbol)
                price = float(trade_data['p'])
                quantity = float(trade_data['q'])
                timestamp = trade_data['T'] / 1000  # Convert to seconds
                
                # Call the callback
                await callback(symbol, price, quantity, timestamp)
            except Exception as e:
                logger.warning(f"Error processing trade data: {e}")
        
        # SSL context for WebSocket (disable verification for development)
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        # Try multiplex first, fallback to individual streams if it fails
        if len(streams) > 1:
            # Try multiplex stream
            stream_names = ','.join(streams)
            ws_url = f"wss://fstream.binance.com/stream?streams={stream_names}"
            
            logger.info(f"Trying multiplex WebSocket: {len(streams)} streams, URL length: {len(ws_url)}")
            
            try:
                async with websockets.connect(
                    ws_url, 
                    ssl=ssl_context,
                    ping_interval=30,     # Auto ping every 30 seconds
                    ping_timeout=20,      # Wait 20 seconds for pong
                    close_timeout=10,
                    max_size=2**23
                ) as websocket:
                    logger.info(f"✅ Multiplex WebSocket connected for {len(streams)} streams")
                    
                    # Backup ping task for multiplex
                    async def backup_ping_task():
                        """Backup ping task in case auto ping fails."""
                        try:
                            while self._running:
                                await asyncio.sleep(25)  # Backup ping every 25 seconds
                                try:
                                    if not websocket.closed:
                                        await websocket.ping()
                                except (websockets.exceptions.ConnectionClosed, AttributeError) as e:
                                    logger.debug(f"Backup ping detected connection closed: {e}")
                                    break
                                except Exception as e:
                                    logger.debug(f"Backup ping error: {e}")
                        except asyncio.CancelledError:
                            pass
                        except Exception as e:
                            logger.debug(f"Backup ping task error: {e}")
                    
                    backup_ping_handle = asyncio.create_task(backup_ping_task())
                    
                    try:
                        async for message in websocket:
                            if not self._running:
                                break
                            await handle_message(message)
                    finally:
                        backup_ping_handle.cancel()
                        try:
                            await backup_ping_handle
                        except asyncio.CancelledError:
                            pass
                    
                    return  # Success, exit function
            except Exception as e:
                logger.warning(f"Multiplex failed ({e}), falling back to individual streams")
        
        # Fallback: Use individual streams
        logger.info(f"Using individual WebSocket streams for {len(streams)} symbols")
        tasks = []
        for stream in streams:
            # Extract symbol from stream name (e.g., "btcusdt@trade" -> "btcusdt")
            symbol = stream.split('@')[0].upper()
            ws_url = f"wss://fstream.binance.com/ws/{stream}"
            
            async def connect_stream(stream_name: str, url: str, sym: str):
                """Connect to a single stream with manual keepalive ping."""
                reconnect_count = 0
                while self._running:
                    try:
                        # Use auto ping with settings optimized for Binance
                        # Binance requires response within 10 minutes, we ping every 30s
                        async with websockets.connect(
                            url, 
                            ssl=ssl_context,
                            ping_interval=30,     # Auto ping every 30 seconds
                            ping_timeout=20,      # Wait 20 seconds for pong
                            close_timeout=10,
                            max_size=2**23
                        ) as websocket:
                            logger.info(f"✅ Connected to {stream_name}")
                            reconnect_count = 0  # Reset on successful connection
                            
                            # Additional manual ping as backup (every 25 seconds)
                            async def backup_ping_task():
                                """Backup ping task in case auto ping fails."""
                                try:
                                    while self._running:
                                        await asyncio.sleep(25)  # Backup ping every 25 seconds
                                        try:
                                            if not websocket.closed:
                                                # Send raw ping frame
                                                await websocket.ping()
                                        except (websockets.exceptions.ConnectionClosed, AttributeError) as e:
                                            logger.debug(f"Backup ping detected connection closed for {stream_name}: {e}")
                                            break
                                        except Exception as e:
                                            # Log but don't break - auto ping should handle it
                                            logger.debug(f"Backup ping error for {stream_name}: {e}")
                                except asyncio.CancelledError:
                                    pass
                                except Exception as e:
                                    logger.debug(f"Backup ping task error for {stream_name}: {e}")
                            
                            # Start backup ping task
                            backup_ping_handle = asyncio.create_task(backup_ping_task())
                            
                            try:
                                async for message in websocket:
                                    if not self._running:
                                        break
                                    await handle_message(message, sym)
                            finally:
                                # Cancel backup ping task
                                backup_ping_handle.cancel()
                                try:
                                    await backup_ping_handle
                                except asyncio.CancelledError:
                                    pass
                    except websockets.exceptions.ConnectionClosed as e:
                        if not self._running:
                            break
                        reconnect_count += 1
                        # Log ping timeout as info (not warning) since it's expected behavior
                        if "ping timeout" in str(e).lower():
                            if reconnect_count <= 1:
                                logger.info(f"Stream {stream_name} ping timeout, reconnecting... (attempt {reconnect_count})")
                        else:
                            if reconnect_count <= 3:
                                logger.warning(f"Stream {stream_name} connection closed: {e}, reconnecting... (attempt {reconnect_count})")
                        await asyncio.sleep(Config.WEBSOCKET_RECONNECT_DELAY)
                    except Exception as e:
                        if not self._running:
                            break
                        reconnect_count += 1
                        if reconnect_count <= 3:  # Only log first few reconnects
                            logger.warning(f"Stream {stream_name} error: {e}, reconnecting... (attempt {reconnect_count})")
                        await asyncio.sleep(Config.WEBSOCKET_RECONNECT_DELAY)
            
            task = asyncio.create_task(connect_stream(stream, ws_url, symbol))
            tasks.append(task)
        
        # Wait for all individual streams and handle exceptions
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions that occurred
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                stream_name = streams[i] if i < len(streams) else f"stream_{i}"
                if not isinstance(result, (asyncio.CancelledError, websockets.exceptions.ConnectionClosed)):
                    logger.error(f"Stream {stream_name} task failed: {result}", exc_info=result)
    
    async def get_klines(self, symbol: str, interval: str = "5m", limit: int = 12) -> List[Dict]:
        """Get historical klines (candlestick data) with rate limiting."""
        try:
            await self.rate_limiter.acquire()
            klines = await self.client.futures_klines(
                symbol=symbol,
                interval=interval,
                limit=limit
            )
            
            # Convert to more usable format
            result = []
            for k in klines:
                result.append({
                    'timestamp': k[0] / 1000,
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5]),
                    'quote_volume': float(k[7]),  # USDT volume
                })
            
            return result
            
        except BinanceAPIException as e:
            logger.warning(f"API error getting klines for {symbol}: {e}")
            return []
        except Exception as e:
            logger.warning(f"Error getting klines for {symbol}: {e}")
            return []
    
    async def get_24h_tickers(self) -> List[Dict]:
        """
        Get 24h ticker statistics for all symbols.
        
        Returns:
            List of ticker dicts with symbol, priceChangePercent, lastPrice, etc.
        """
        try:
            await self.rate_limiter.acquire()
            
            # Try different method names
            if hasattr(self.client, 'futures_ticker'):
                tickers = await self.client.futures_ticker()
            elif hasattr(self.client, 'futures_24hr_ticker'):
                tickers = await self.client.futures_24hr_ticker()
            elif hasattr(self.client, 'get_futures_ticker'):
                tickers = await self.client.get_futures_ticker()
            else:
                logger.warning("No ticker method available")
                return []
            
            # Normalize response format
            if isinstance(tickers, dict):
                tickers = [tickers]
            
            # Convert to list of dicts with normalized keys
            result = []
            for ticker in tickers:
                # Handle different response formats
                symbol = ticker.get('symbol', '')
                price_change_percent = float(ticker.get('priceChangePercent', ticker.get('P', 0)))
                last_price = float(ticker.get('lastPrice', ticker.get('c', 0)))
                volume_24h = float(ticker.get('quoteVolume', ticker.get('qv', 0)))
                
                if symbol and price_change_percent != 0:
                    result.append({
                        'symbol': symbol,
                        'priceChangePercent': price_change_percent,
                        'lastPrice': last_price,
                        'volume24h': volume_24h
                    })
            
            return result
            
        except BinanceAPIException as e:
            logger.error(f"Binance API error getting 24h tickers: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting 24h tickers: {e}")
            return []
    
    async def close(self):
        """Close connections."""
        self._running = False
        # Note: BinanceSocketManager doesn't have close() method
        # WebSocket connections will close when _running is False
        if self.client:
            await self.client.close_connection()
        logger.info("Binance client closed")
