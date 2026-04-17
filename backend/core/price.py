import requests
import time
from datetime import datetime, timedelta

URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd,eur"
HISTORICAL_URL = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"

_last_price = None
_last_fetch_time = 0
_rate_limited_until = 0
_last_historical_price = None
_last_historical_fetch_time = 0
CACHE_DURATION = 900
HISTORICAL_CACHE_DURATION = 3600  # Cache historical data for 1 hour

# Fallback prices when API is unavailable (approximate values)
FALLBACK_PRICES = {
    "usd": 62000,
    "eur": 57000
}


def get_bitcoin_price():
    global _last_price, _last_fetch_time, _rate_limited_until

    now = time.time()

    # Return cached price if still valid
    if _last_price and (now - _last_fetch_time) < CACHE_DURATION:
        return _last_price

    # Respect upstream rate-limit cooldown window
    if now < _rate_limited_until:
        if _last_price:
            return _last_price
        return FALLBACK_PRICES

    try:
        res = requests.get(URL, timeout=10)
        if res.status_code == 429:
            retry_after = res.headers.get("Retry-After")
            retry_seconds = int(retry_after) if retry_after and retry_after.isdigit() else CACHE_DURATION
            _rate_limited_until = now + max(retry_seconds, CACHE_DURATION)
            print(f"[Price Service] Rate limited by CoinGecko - backing off for {retry_seconds}s")
            if _last_price:
                return _last_price
            return FALLBACK_PRICES
        res.raise_for_status()
        data = res.json()

        if "bitcoin" in data:
            _last_price = data["bitcoin"]
            _last_fetch_time = now
            _rate_limited_until = 0
            return _last_price

        raise ValueError("Invalid API response from CoinGecko")

    except requests.exceptions.Timeout:
        print("[Price Service] API timeout - using cached or fallback price")
        if _last_price:
            return _last_price
        return FALLBACK_PRICES
    
    except requests.exceptions.ConnectionError:
        print("[Price Service] Connection error - using cached or fallback price")
        if _last_price:
            return _last_price
        return FALLBACK_PRICES
    
    except Exception as e:
        print(f"[Price Service] Error fetching Bitcoin price: {str(e)}")
        if _last_price:
            return _last_price
        return FALLBACK_PRICES


def get_historical_bitcoin_price(days=7):
    """Fetch historical Bitcoin price data for the past N days (USD only)"""
    global _last_historical_price, _last_historical_fetch_time
    
    now = time.time()
    
    # Return cached if available
    if _last_historical_price and (now - _last_historical_fetch_time) < HISTORICAL_CACHE_DURATION:
        return _last_historical_price
    
    try:
        params = {
            "ids": "bitcoin",
            "vs_currency": "usd",
            "days": days,
            "interval": "hourly"
        }
        res = requests.get(HISTORICAL_URL, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        
        if "prices" in data:
            # Convert timestamp array to time-price pairs
            prices_data = []
            for timestamp, price in data["prices"]:
                date_time = datetime.fromtimestamp(timestamp / 1000)
                time_str = date_time.strftime("%H:%M")
                prices_data.append({
                    "price": round(price, 2),
                    "time": time_str,
                    "timestamp": timestamp
                })
            
            _last_historical_price = prices_data
            _last_historical_fetch_time = now
            return prices_data
        
        raise ValueError("Invalid historical API response")
    
    except Exception as e:
        print(f"Error fetching historical price: {e}")
        if _last_historical_price:
            return _last_historical_price
        return []
