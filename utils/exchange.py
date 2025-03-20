import requests
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Cache for exchange rate data
_exchange_rate_cache = {
    'rate': None,
    'last_updated': None
}

def get_usdt_try_rate():
    """
    Fetch current USDT to TRY exchange rate with caching
    Returns the rate as a float or None if fetch fails
    """
    # Check if we have a cached rate that's less than 1 hour old
    if (_exchange_rate_cache['rate'] is not None and
            _exchange_rate_cache['last_updated'] is not None and
            datetime.now() - _exchange_rate_cache['last_updated'] < timedelta(hours=1)):
        return _exchange_rate_cache['rate']
    
    # Try to fetch new exchange rate
    try:
        # Fetch from CoinGecko API
        url = "https://api.coingecko.com/api/v3/simple/price?ids=tether&vs_currencies=try"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if 'tether' in data and 'try' in data['tether']:
                rate = data['tether']['try']
                
                # Update cache
                _exchange_rate_cache['rate'] = rate
                _exchange_rate_cache['last_updated'] = datetime.now()
                
                logger.info(f"Updated USDT/TRY rate: {rate}")
                return rate
        
        # If we get here, something went wrong with the API
        logger.warning(f"Failed to get exchange rate from CoinGecko: {response.status_code}")
        return _exchange_rate_cache['rate']  # Return cached value if available
        
    except Exception as e:
        logger.error(f"Error fetching exchange rate: {e}")
        return _exchange_rate_cache['rate']  # Return cached value if available