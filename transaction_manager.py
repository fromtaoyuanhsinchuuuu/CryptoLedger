from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd
from models import Transaction
from database import Database

class TransactionManager:
    """Class for managing cryptocurrency transactions."""
    
    def __init__(self, database: Database):
        """
        Initialize TransactionManager with a database.
        
        Args:
            database: Database instance for storage
        """
        self.db = database
    
    def add_transaction(self, wallet_id: int, transaction_type: str, 
                       crypto_symbol: str, quantity: float, price_per_unit: float,
                       fiat_currency: str = "USD", fee: float = 0,
                       transaction_date: Optional[datetime] = None, notes: str = "") -> int:
        """
        Add a new transaction to the database.
        
        Args:
            wallet_id: ID of the wallet
            transaction_type: Type of transaction (buy, sell, exchange, transfer_in, transfer_out)
            crypto_symbol: Symbol of the cryptocurrency
            quantity: Quantity of cryptocurrency
            price_per_unit: Price per unit in fiat currency
            fiat_currency: Fiat currency code (default: USD)
            fee: Transaction fee in fiat currency
            transaction_date: Date and time of transaction (default: now)
            notes: Additional notes
        
        Returns:
            ID of the new transaction
        
        Raises:
            ValueError: If invalid transaction data
        """
        # Validate transaction data
        if quantity <= 0:
            raise ValueError("Quantity must be greater than zero")
        
        if price_per_unit < 0:
            raise ValueError("Price per unit cannot be negative")
        
        if fee < 0:
            raise ValueError("Fee cannot be negative")
        
        # Add transaction to database
        return self.db.add_transaction(
            wallet_id=wallet_id,
            transaction_type=transaction_type,
            crypto_symbol=crypto_symbol,
            quantity=quantity,
            price_per_unit=price_per_unit,
            fiat_currency=fiat_currency,
            fee=fee,
            transaction_date=transaction_date,
            notes=notes
        )
    
    def get_transactions(self, wallet_id: Optional[int] = None, 
                        crypto_symbol: Optional[str] = None,
                        transaction_type: Optional[str] = None, 
                        start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> List[Dict]:
        """
        Get transactions with optional filters.
        
        Args:
            wallet_id: Filter by wallet ID
            crypto_symbol: Filter by cryptocurrency symbol
            transaction_type: Filter by transaction type
            start_date: Filter by start date
            end_date: Filter by end date
        
        Returns:
            List of transaction dictionaries
        """
        return self.db.get_transactions(
            wallet_id=wallet_id,
            crypto_symbol=crypto_symbol,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date
        )
    
    def get_transactions_dataframe(self, wallet_id: Optional[int] = None, 
                                 crypto_symbol: Optional[str] = None,
                                 transaction_type: Optional[str] = None, 
                                 start_date: Optional[datetime] = None, 
                                 end_date: Optional[datetime] = None) -> pd.DataFrame:
        """
        Get transactions as a pandas DataFrame with optional filters.
        
        Args:
            wallet_id: Filter by wallet ID
            crypto_symbol: Filter by cryptocurrency symbol
            transaction_type: Filter by transaction type
            start_date: Filter by start date
            end_date: Filter by end date
        
        Returns:
            DataFrame with transactions
        """
        return self.db.get_transactions_df(
            wallet_id=wallet_id,
            crypto_symbol=crypto_symbol,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date
        )
    
    def update_transaction(self, transaction_id: int, **kwargs) -> bool:
        """
        Update a transaction by ID.
        
        Args:
            transaction_id: ID of the transaction to update
            **kwargs: Fields to update
        
        Returns:
            True if successful, False otherwise
        """
        # Validate quantity and price if provided
        if 'quantity' in kwargs and kwargs['quantity'] <= 0:
            raise ValueError("Quantity must be greater than zero")
        
        if 'price_per_unit' in kwargs and kwargs['price_per_unit'] < 0:
            raise ValueError("Price per unit cannot be negative")
        
        if 'fee' in kwargs and kwargs['fee'] < 0:
            raise ValueError("Fee cannot be negative")
        
        return self.db.update_transaction(transaction_id, **kwargs)
    
    def delete_transaction(self, transaction_id: int) -> bool:
        """
        Delete a transaction by ID.
        
        Args:
            transaction_id: ID of the transaction to delete
        
        Returns:
            True if successful, False otherwise
        """
        return self.db.delete_transaction(transaction_id)
    
    def import_transactions_from_csv(self, filepath: str, wallet_id: int) -> int:
        """
        Import transactions from a CSV file.
        
        Args:
            filepath: Path to CSV file
            wallet_id: ID of the wallet to associate transactions with
        
        Returns:
            Number of transactions imported
        
        Raises:
            ValueError: If invalid CSV file
        """
        try:
            df = pd.read_csv(filepath)
            required_columns = [
                'transaction_type', 'crypto_symbol', 'quantity', 
                'price_per_unit', 'transaction_date'
            ]
            
            # Check if required columns exist
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
            # Process each row
            count = 0
            for _, row in df.iterrows():
                try:
                    # Get optional fields with defaults
                    fiat_currency = row.get('fiat_currency', 'USD')
                    fee = float(row.get('fee', 0))
                    notes = str(row.get('notes', ''))
                    
                    # Add transaction
                    self.add_transaction(
                        wallet_id=wallet_id,
                        transaction_type=row['transaction_type'],
                        crypto_symbol=row['crypto_symbol'],
                        quantity=float(row['quantity']),
                        price_per_unit=float(row['price_per_unit']),
                        fiat_currency=fiat_currency,
                        fee=fee,
                        transaction_date=row['transaction_date'],
                        notes=notes
                    )
                    count += 1
                except Exception as e:
                    # Continue with next row
                    print(f"Error importing row: {e}")
            
            return count
            
        except Exception as e:
            raise ValueError(f"Error importing CSV: {e}")
    
    def export_transactions_to_csv(self, filepath: str, wallet_id: Optional[int] = None) -> bool:
        """
        Export transactions to a CSV file.
        
        Args:
            filepath: Path to save CSV file
            wallet_id: Filter by wallet ID (optional)
        
        Returns:
            True if successful, False otherwise
        """
        return self.db.export_to_csv(filepath, wallet_id)
    
    def get_crypto_symbols(self) -> List[str]:
        """
        Get all unique cryptocurrency symbols from transactions.
        
        Returns:
            List of cryptocurrency symbols
        """
        return self.db.get_crypto_symbols()
