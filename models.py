from dataclasses import dataclass
from datetime import datetime
from typing import Optional, List, Dict
import json

@dataclass
class Transaction:
    """Model for cryptocurrency transactions."""
    id: Optional[int] = None
    wallet_id: int = 0
    transaction_type: str = ""  # buy, sell, exchange, transfer_in, transfer_out
    crypto_symbol: str = ""
    quantity: float = 0.0
    price_per_unit: float = 0.0
    fiat_currency: str = "USD"
    fee: float = 0.0
    transaction_date: datetime = None
    notes: str = ""
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """Initialize default values if not provided."""
        if self.transaction_date is None:
            self.transaction_date = datetime.now()
        
        # Ensure uppercase symbols
        self.crypto_symbol = self.crypto_symbol.upper()
        self.fiat_currency = self.fiat_currency.upper()
    
    @property
    def total_cost(self) -> float:
        """Calculate the total cost of the transaction."""
        return self.quantity * self.price_per_unit
    
    @property
    def total_with_fee(self) -> float:
        """Calculate the total cost including fees."""
        return self.total_cost + self.fee
    
    def to_dict(self) -> Dict:
        """Convert Transaction to dictionary."""
        return {
            "id": self.id,
            "wallet_id": self.wallet_id,
            "transaction_type": self.transaction_type,
            "crypto_symbol": self.crypto_symbol,
            "quantity": self.quantity,
            "price_per_unit": self.price_per_unit,
            "fiat_currency": self.fiat_currency,
            "fee": self.fee,
            "transaction_date": self.transaction_date.isoformat() if self.transaction_date else None,
            "notes": self.notes,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Transaction':
        """Create a Transaction from a dictionary."""
        # Handle date strings if they exist
        if data.get("transaction_date") and isinstance(data["transaction_date"], str):
            data["transaction_date"] = datetime.fromisoformat(data["transaction_date"])
        
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        return cls(**data)


@dataclass
class Wallet:
    """Model for cryptocurrency wallets or accounts."""
    id: Optional[int] = None
    name: str = ""
    description: str = ""
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert Wallet to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Wallet':
        """Create a Wallet from a dictionary."""
        # Handle date strings if they exist
        if data.get("created_at") and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"])
        
        return cls(**data)


@dataclass
class TaxReport:
    """Model for cryptocurrency tax reporting."""
    year: int
    fiat_currency: str = "USD"
    short_term_gains: float = 0.0
    long_term_gains: float = 0.0
    transactions: List[Dict] = None
    
    def __post_init__(self):
        """Initialize default values if not provided."""
        self.fiat_currency = self.fiat_currency.upper()
        if self.transactions is None:
            self.transactions = []
    
    @property
    def total_gains(self) -> float:
        """Calculate total capital gains."""
        return self.short_term_gains + self.long_term_gains
    
    def to_dict(self) -> Dict:
        """Convert TaxReport to dictionary."""
        return {
            "year": self.year,
            "fiat_currency": self.fiat_currency,
            "short_term_gains": self.short_term_gains,
            "long_term_gains": self.long_term_gains,
            "total_gains": self.total_gains,
            "transactions": self.transactions
        }
    
    def to_json(self) -> str:
        """Convert TaxReport to JSON string."""
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class PortfolioItem:
    """Model for a portfolio item (holdings of a specific cryptocurrency)."""
    crypto_symbol: str
    quantity: float
    current_price: Optional[float] = None
    fiat_currency: str = "USD"
    
    def __post_init__(self):
        """Initialize and process values."""
        self.crypto_symbol = self.crypto_symbol.upper()
        self.fiat_currency = self.fiat_currency.upper()
    
    @property
    def current_value(self) -> Optional[float]:
        """Calculate current value if price is available."""
        if self.current_price is not None:
            return self.quantity * self.current_price
        return None
    
    def to_dict(self) -> Dict:
        """Convert PortfolioItem to dictionary."""
        return {
            "crypto_symbol": self.crypto_symbol,
            "quantity": self.quantity,
            "current_price": self.current_price,
            "fiat_currency": self.fiat_currency,
            "current_value": self.current_value
        }
