from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
from models import Transaction

class ProfitLossCalculator:
    """Class to calculate profit and loss for cryptocurrency transactions using FIFO method."""
    
    def __init__(self, transactions: List[Dict] = None):
        """
        Initialize the calculator with transactions.
        
        Args:
            transactions: List of transaction dictionaries
        """
        self.transactions = []
        if transactions:
            for tx in transactions:
                if isinstance(tx, dict):
                    self.transactions.append(Transaction.from_dict(tx))
                elif isinstance(tx, Transaction):
                    self.transactions.append(tx)
        
        # Sort transactions by date
        self.transactions.sort(key=lambda x: x.transaction_date)
        
        # Initialize inventory for FIFO calculation
        self.inventory = {}  # {symbol: [(quantity, price_per_unit, date)]}
    
    def load_transactions(self, transactions: List[Dict]):
        """
        Load transactions into the calculator.
        
        Args:
            transactions: List of transaction dictionaries
        """
        self.transactions = []
        for tx in transactions:
            if isinstance(tx, dict):
                self.transactions.append(Transaction.from_dict(tx))
            elif isinstance(tx, Transaction):
                self.transactions.append(tx)
        
        # Sort transactions by date
        self.transactions.sort(key=lambda x: x.transaction_date)
        
        # Reset inventory
        self.inventory = {}
    
    def process_transactions(self) -> Dict:
        """
        Process all transactions to calculate profit/loss.
        
        Returns:
            Dictionary with realized and unrealized gains
        """
        self.inventory = {}
        realized_gains = {}
        
        for tx in self.transactions:
            symbol = tx.crypto_symbol
            
            # Initialize inventory and realized gains for this symbol if not exists
            if symbol not in self.inventory:
                self.inventory[symbol] = []
            if symbol not in realized_gains:
                realized_gains[symbol] = []
            
            if tx.transaction_type == 'buy' or tx.transaction_type == 'transfer_in':
                # Add to inventory
                self.inventory[symbol].append((
                    tx.quantity,
                    tx.price_per_unit,
                    tx.transaction_date,
                    tx.id
                ))
            
            elif tx.transaction_type == 'sell' or tx.transaction_type == 'transfer_out':
                # Calculate realized gains using FIFO
                remaining_qty = tx.quantity
                sell_proceeds = tx.quantity * tx.price_per_unit
                cost_basis = 0
                
                while remaining_qty > 0 and self.inventory[symbol]:
                    buy_qty, buy_price, buy_date, buy_id = self.inventory[symbol][0]
                    
                    if buy_qty <= remaining_qty:
                        # Use entire lot
                        self.inventory[symbol].pop(0)
                        used_qty = buy_qty
                    else:
                        # Use partial lot
                        self.inventory[symbol][0] = (
                            buy_qty - remaining_qty,
                            buy_price,
                            buy_date,
                            buy_id
                        )
                        used_qty = remaining_qty
                    
                    # Calculate gain/loss for this portion
                    portion_cost = used_qty * buy_price
                    portion_proceeds = used_qty * tx.price_per_unit
                    gain = portion_proceeds - portion_cost
                    
                    # Determine if short or long term
                    holding_period = (tx.transaction_date - buy_date).days
                    term = 'long' if holding_period > 365 else 'short'
                    
                    # Record the realized gain
                    realized_gains[symbol].append({
                        'buy_date': buy_date,
                        'sell_date': tx.transaction_date,
                        'buy_price': buy_price,
                        'sell_price': tx.price_per_unit,
                        'quantity': used_qty,
                        'cost_basis': portion_cost,
                        'proceeds': portion_proceeds,
                        'gain': gain,
                        'term': term,
                        'holding_period_days': holding_period,
                        'buy_transaction_id': buy_id,
                        'sell_transaction_id': tx.id
                    })
                    
                    cost_basis += portion_cost
                    remaining_qty -= used_qty
                
                if remaining_qty > 0:
                    # This should not happen with valid data
                    # It means trying to sell more than what's in inventory
                    print(f"Warning: Trying to sell more {symbol} than available in inventory.")
            
            elif tx.transaction_type == 'exchange':
                # Handle as a sell of one currency and buy of another
                # This is simplified and might need enhancement for complex scenarios
                pass
        
        return {
            'realized_gains': realized_gains,
            'inventory': self.inventory
        }
    
    def calculate_realized_gains(self, year: Optional[int] = None) -> Dict:
        """
        Calculate realized gains for a specific year.
        
        Args:
            year: Tax year to calculate for (optional)
        
        Returns:
            Dictionary with short and long term gains
        """
        result = self.process_transactions()
        realized_gains = result['realized_gains']
        
        short_term_total = 0
        long_term_total = 0
        transactions = []
        
        for symbol, gains in realized_gains.items():
            for gain in gains:
                # Filter by year if specified
                if year and gain['sell_date'].year != year:
                    continue
                
                if gain['term'] == 'short':
                    short_term_total += gain['gain']
                else:
                    long_term_total += gain['gain']
                
                transactions.append(gain)
        
        return {
            'short_term_gains': short_term_total,
            'long_term_gains': long_term_total,
            'total_gains': short_term_total + long_term_total,
            'transactions': transactions
        }
    
    def get_current_inventory(self) -> Dict:
        """
        Get the current inventory after processing all transactions.
        
        Returns:
            Dictionary with inventory details by symbol
        """
        result = self.process_transactions()
        inventory = result['inventory']
        
        inventory_summary = {}
        for symbol, lots in inventory.items():
            total_quantity = sum(lot[0] for lot in lots)
            if total_quantity > 0:
                avg_price = sum(lot[0] * lot[1] for lot in lots) / total_quantity
                inventory_summary[symbol] = {
                    'quantity': total_quantity,
                    'average_cost': avg_price,
                    'lots': [
                        {
                            'quantity': lot[0],
                            'price': lot[1],
                            'date': lot[2],
                            'transaction_id': lot[3]
                        } for lot in lots
                    ]
                }
        
        return inventory_summary
    
    def calculate_unrealized_gains(self, current_prices: Dict[str, float]) -> Dict:
        """
        Calculate unrealized gains based on current prices.
        
        Args:
            current_prices: Dictionary with symbol as key and current price as value
        
        Returns:
            Dictionary with unrealized gains by symbol
        """
        inventory = self.get_current_inventory()
        unrealized_gains = {}
        total_unrealized_gain = 0
        
        for symbol, inv in inventory.items():
            if symbol in current_prices:
                current_price = current_prices[symbol]
                quantity = inv['quantity']
                avg_cost = inv['average_cost']
                
                market_value = quantity * current_price
                cost_basis = quantity * avg_cost
                unrealized_gain = market_value - cost_basis
                
                unrealized_gains[symbol] = {
                    'quantity': quantity,
                    'average_cost': avg_cost,
                    'current_price': current_price,
                    'market_value': market_value,
                    'cost_basis': cost_basis,
                    'unrealized_gain': unrealized_gain
                }
                
                total_unrealized_gain += unrealized_gain
        
        return {
            'by_symbol': unrealized_gains,
            'total_unrealized_gain': total_unrealized_gain
        }
