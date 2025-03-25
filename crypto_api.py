import requests
import time
import pandas as pd
from datetime import datetime, timedelta
import os

class CryptoAPI:
    """Class to interact with CoinGecko API for cryptocurrency data."""
    
    def __init__(self):
        """Initialize CryptoAPI class with base URL and headers."""
        self.base_url = "https://api.coingecko.com/api/v3"
        self.headers = {
            'Accept': 'application/json',
            'User-Agent': 'Crypto Accounting App'
        }
        
        # Optional API key from environment
        self.api_key = os.getenv("COINGECKO_API_KEY", None)
        if self.api_key:
            self.headers['x-cg-api-key'] = self.api_key
        
        # Cache for coin ID mapping and prices
        self.coin_id_cache = {}
        self.price_cache = {}
        self.price_cache_time = {}
        self.cache_validity = 300  # 5 minutes
    
    def _make_request(self, endpoint, params=None):
        """Make a request to the CoinGecko API with built-in rate limiting and error handling."""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            
            if response.status_code == 429:  # Rate limit exceeded
                time.sleep(60)  # Wait for 60 seconds before retrying
                return self._make_request(endpoint, params)
            
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            return None
    
    def get_supported_coins(self):
        """Get list of all supported coins with their IDs."""
        data = self._make_request("coins/list")
        if data:
            # Update coin ID cache
            for coin in data:
                self.coin_id_cache[coin['symbol'].upper()] = coin['id']
            return data
        return []
    
    def get_coin_id(self, symbol):
        """Get coin ID from symbol (cached if possible)."""
        symbol = symbol.upper()
        
        # Check cache first
        if symbol in self.coin_id_cache:
            return self.coin_id_cache[symbol]
        
        # If not in cache, fetch all coins and update cache
        self.get_supported_coins()
        
        # Check cache again
        if symbol in self.coin_id_cache:
            return self.coin_id_cache[symbol]
        
        # If still not found, try to search for it
        try:
            endpoint = "search"
            params = {"query": symbol}
            data = self._make_request(endpoint, params)
            
            if data and data.get("coins"):
                for coin in data["coins"]:
                    if coin.get("symbol", "").upper() == symbol:
                        # Update cache and return
                        self.coin_id_cache[symbol] = coin["id"]
                        return coin["id"]
        except Exception as e:
            print(f"Error searching for coin: {e}")
        
        # If all fails, return None
        return None
    
    def get_current_price(self, symbols, fiat="USD"):
        """
        Get current price for one or multiple cryptocurrencies.
        
        Args:
            symbols: String or list of strings with cryptocurrency symbols
            fiat: Fiat currency for price (default: USD)
        
        Returns:
            Dictionary with symbol as key and price as value
        """
        if isinstance(symbols, str):
            symbols = [symbols]
        
        fiat = fiat.lower()
        result = {}
        missing_symbols = []
        
        # Check cache first
        for symbol in symbols:
            symbol = symbol.upper()
            cache_key = f"{symbol}_{fiat}"
            
            if (cache_key in self.price_cache and 
                cache_key in self.price_cache_time and 
                (datetime.now() - self.price_cache_time[cache_key]).total_seconds() < self.cache_validity):
                result[symbol] = self.price_cache[cache_key]
            else:
                missing_symbols.append(symbol)
        
        if missing_symbols:
            # Get coin IDs for symbols
            coin_ids = []
            for symbol in missing_symbols:
                coin_id = self.get_coin_id(symbol)
                if coin_id:
                    coin_ids.append(coin_id)
            
            if coin_ids:
                endpoint = "simple/price"
                params = {
                    "ids": ",".join(coin_ids),
                    "vs_currencies": fiat,
                    "include_24hr_change": "true"
                }
                
                data = self._make_request(endpoint, params)
                
                if data:
                    # Map coin IDs back to symbols and update result
                    for symbol in missing_symbols:
                        coin_id = self.get_coin_id(symbol)
                        if coin_id and coin_id in data:
                            price = data[coin_id].get(fiat, 0)
                            result[symbol] = price
                            
                            # Update cache
                            cache_key = f"{symbol}_{fiat}"
                            self.price_cache[cache_key] = price
                            self.price_cache_time[cache_key] = datetime.now()
        
        return result
    
    def get_historical_price(self, symbol, date, fiat="USD"):
        """
        Get historical price for a cryptocurrency on a specific date.
        
        Args:
            symbol: Cryptocurrency symbol
            date: Date string in format YYYY-MM-DD or datetime object
            fiat: Fiat currency for price (default: USD)
        
        Returns:
            Price as float or None if not found
        """
        symbol = symbol.upper()
        fiat = fiat.lower()
        
        # Convert date to string format if it's a datetime object
        if isinstance(date, datetime):
            date_str = date.strftime("%d-%m-%Y")
        else:
            # Convert from YYYY-MM-DD to DD-MM-YYYY
            try:
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                date_str = date_obj.strftime("%d-%m-%Y")
            except ValueError:
                return None
        
        # Get coin ID
        coin_id = self.get_coin_id(symbol)
        if not coin_id:
            return None
        
        endpoint = f"coins/{coin_id}/history"
        params = {
            "date": date_str,
            "localization": "false"
        }
        
        data = self._make_request(endpoint, params)
        
        if data and "market_data" in data:
            price = data["market_data"]["current_price"].get(fiat)
            return float(price) if price is not None else None
        
        return None
    
    def get_market_chart(self, symbol, days=30, fiat="USD"):
        """
        Get price data for chart rendering.
        
        Args:
            symbol: Cryptocurrency symbol
            days: Number of days of data to retrieve
            fiat: Fiat currency for price (default: USD)
        
        Returns:
            DataFrame with dates and prices or None if error
        """
        symbol = symbol.upper()
        fiat = fiat.lower()
        
        # Get coin ID
        coin_id = self.get_coin_id(symbol)
        if not coin_id:
            return None
        
        endpoint = f"coins/{coin_id}/market_chart"
        params = {
            "vs_currency": fiat,
            "days": days,
            "interval": "daily"
        }
        
        data = self._make_request(endpoint, params)
        
        if data and "prices" in data:
            # Convert to DataFrame
            df = pd.DataFrame(data["prices"], columns=["timestamp", "price"])
            df["date"] = pd.to_datetime(df["timestamp"], unit="ms")
            return df[["date", "price"]]
        
        return None
