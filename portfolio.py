from typing import List, Dict, Optional
import pandas as pd
from models import PortfolioItem, Transaction
from crypto_api import CryptoAPI

class Portfolio:
    """Class for managing cryptocurrency portfolio."""
    
    def __init__(self, transactions: List[Dict] = None, crypto_api: CryptoAPI = None):
        """
        Initialize Portfolio with transactions and API.
        
        Args:
            transactions: List of transaction dictionaries
            crypto_api: CryptoAPI instance for price data
        """
        self.transactions = []
        if transactions:
            for tx in transactions:
                if isinstance(tx, dict):
                    self.transactions.append(Transaction.from_dict(tx))
                elif isinstance(tx, Transaction):
                    self.transactions.append(tx)
        
        self.crypto_api = crypto_api or CryptoAPI()
        self.holdings = {}  # Will be calculated when needed
    
    def load_transactions(self, transactions: List[Dict]):
        """
        Load transactions into the portfolio.
        
        Args:
            transactions: List of transaction dictionaries
        """
        self.transactions = []
        for tx in transactions:
            if isinstance(tx, dict):
                self.transactions.append(Transaction.from_dict(tx))
            elif isinstance(tx, Transaction):
                self.transactions.append(tx)
        
        # Reset holdings
        self.holdings = {}
    
    def calculate_holdings(self) -> Dict[str, float]:
        """
        Calculate current holdings based on transactions.
        
        Returns:
            Dictionary with symbols as keys and quantities as values
        """
        holdings = {}
        
        for tx in self.transactions:
            symbol = tx.crypto_symbol
            
            if symbol not in holdings:
                holdings[symbol] = 0
            
            if tx.transaction_type == 'buy' or tx.transaction_type == 'transfer_in':
                holdings[symbol] += tx.quantity
            elif tx.transaction_type == 'sell' or tx.transaction_type == 'transfer_out':
                holdings[symbol] -= tx.quantity
        
        # Remove zero or negative holdings (shouldn't happen with valid data)
        self.holdings = {k: v for k, v in holdings.items() if v > 0}
        return self.holdings
    
    def get_portfolio_items(self, fiat_currency: str = "USD") -> List[PortfolioItem]:
        """
        Get portfolio items with current prices.
        
        Args:
            fiat_currency: Fiat currency to use for prices
        
        Returns:
            List of PortfolioItem objects
        """
        # Make sure holdings are calculated
        if not self.holdings:
            self.calculate_holdings()
        
        # Get current prices
        symbols = list(self.holdings.keys())
        prices = self.crypto_api.get_current_price(symbols, fiat_currency)
        
        # Create portfolio items
        items = []
        for symbol, quantity in self.holdings.items():
            if quantity > 0:  # Only include positive holdings
                price = prices.get(symbol)
                item = PortfolioItem(
                    crypto_symbol=symbol,
                    quantity=quantity,
                    current_price=price,
                    fiat_currency=fiat_currency
                )
                items.append(item)
        
        return items
    
    def get_portfolio_value(self, fiat_currency: str = "USD") -> Dict:
        """
        Get total portfolio value and items.
        
        Args:
            fiat_currency: Fiat currency to use for values
        
        Returns:
            Dictionary with portfolio value and items
        """
        items = self.get_portfolio_items(fiat_currency)
        
        # Calculate total value
        total_value = sum(item.current_value or 0 for item in items)
        
        return {
            'total_value': total_value,
            'fiat_currency': fiat_currency,
            'items': [item.to_dict() for item in items]
        }
    
    def get_portfolio_distribution(self, fiat_currency: str = "USD") -> Dict:
        """
        Get portfolio distribution by percentage.
        
        Args:
            fiat_currency: Fiat currency to use for values
        
        Returns:
            Dictionary with portfolio distribution data
        """
        portfolio = self.get_portfolio_value(fiat_currency)
        total_value = portfolio['total_value']
        
        if total_value <= 0:
            return {
                'total_value': 0,
                'fiat_currency': fiat_currency,
                'distribution': []
            }
        
        distribution = []
        for item in portfolio['items']:
            if item['current_value']:
                percentage = (item['current_value'] / total_value) * 100
                distribution.append({
                    'symbol': item['crypto_symbol'],
                    'value': item['current_value'],
                    'percentage': percentage
                })
        
        # Sort by value descending
        distribution.sort(key=lambda x: x['value'], reverse=True)
        
        return {
            'total_value': total_value,
            'fiat_currency': fiat_currency,
            'distribution': distribution
        }
    
    def get_historical_portfolio_value(self, days: int = 30, fiat_currency: str = "USD") -> pd.DataFrame:
        """
        Get historical portfolio value for charting.
        
        Args:
            days: Number of days of historical data
            fiat_currency: Fiat currency to use for values
        
        Returns:
            DataFrame with dates and values
        """
        # This is a simplified implementation
        # For a more accurate version, we would need historical prices for each day
        # and calculate the portfolio value based on transactions up to that day
        
        # Make sure holdings are calculated
        if not self.holdings:
            self.calculate_holdings()
        
        symbols = list(self.holdings.keys())
        if not symbols:
            # Return empty DataFrame if no holdings
            return pd.DataFrame(columns=['date', 'value'])
        
        dfs = []
        for symbol in symbols:
            chart_data = self.crypto_api.get_market_chart(symbol, days, fiat_currency)
            if chart_data is not None:
                # Multiply price by quantity held
                quantity = self.holdings[symbol]
                chart_data['value'] = chart_data['price'] * quantity
                chart_data = chart_data[['date', 'value']]
                dfs.append(chart_data)
        
        if not dfs:
            return pd.DataFrame(columns=['date', 'value'])
        
        # Combine all DataFrames
        result = pd.concat(dfs)
        
        # Group by date and sum values
        result = result.groupby('date')['value'].sum().reset_index()
        
        return result
