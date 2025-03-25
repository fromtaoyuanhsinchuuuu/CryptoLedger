import sqlite3
import os
import pandas as pd
from datetime import datetime
import threading

class Database:
    def __init__(self, db_name="crypto_accounting.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_name = db_name
        self.lock = threading.Lock()
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False)
        self.create_tables()
    
    def get_connection(self):
        """Get the database connection and cursor."""
        return self.conn, self.conn.cursor()
    
    def create_tables(self):
        """Create necessary tables if they don't exist."""
        with self.lock:
            conn, cursor = self.get_connection()
            
            # Wallets table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Transactions table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                wallet_id INTEGER,
                transaction_type TEXT NOT NULL,
                crypto_symbol TEXT NOT NULL,
                quantity REAL NOT NULL,
                price_per_unit REAL NOT NULL,
                fiat_currency TEXT DEFAULT 'USD',
                fee REAL DEFAULT 0,
                transaction_date TIMESTAMP NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (wallet_id) REFERENCES wallets(id)
            )
            ''')
            
            conn.commit()
    
    def add_wallet(self, name, description=""):
        """Add a new wallet to the database."""
        with self.lock:
            conn, cursor = self.get_connection()
            try:
                cursor.execute(
                    "INSERT INTO wallets (name, description) VALUES (?, ?)",
                    (name, description)
                )
                conn.commit()
                return True
            except sqlite3.IntegrityError:
                # Wallet with this name already exists
                return False
    
    def get_wallets(self):
        """Get all wallets from the database."""
        with self.lock:
            conn, cursor = self.get_connection()
            cursor.execute("SELECT id, name, description FROM wallets")
            return [{"id": row[0], "name": row[1], "description": row[2]} for row in cursor.fetchall()]
    
    def add_transaction(self, wallet_id, transaction_type, crypto_symbol, quantity, 
                        price_per_unit, fiat_currency="USD", fee=0, 
                        transaction_date=None, notes=""):
        """
        Add a new transaction to the database.
        transaction_type can be 'buy', 'sell', 'exchange', 'transfer_in', 'transfer_out'
        """
        if transaction_date is None:
            transaction_date = datetime.now()
        elif isinstance(transaction_date, str):
            transaction_date = datetime.strptime(transaction_date, "%Y-%m-%d")
        
        with self.lock:
            conn, cursor = self.get_connection()
            cursor.execute(
                """INSERT INTO transactions 
                (wallet_id, transaction_type, crypto_symbol, quantity, price_per_unit, 
                fiat_currency, fee, transaction_date, notes) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (wallet_id, transaction_type, crypto_symbol.upper(), quantity, price_per_unit, 
                 fiat_currency.upper(), fee, transaction_date, notes)
            )
            conn.commit()
            return cursor.lastrowid
    
    def get_transactions(self, wallet_id=None, crypto_symbol=None, 
                        transaction_type=None, start_date=None, end_date=None):
        """
        Get transactions with optional filters.
        Returns a list of transaction dictionaries.
        """
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        
        if wallet_id:
            query += " AND wallet_id = ?"
            params.append(wallet_id)
        
        if crypto_symbol:
            query += " AND crypto_symbol = ?"
            params.append(crypto_symbol.upper())
        
        if transaction_type:
            query += " AND transaction_type = ?"
            params.append(transaction_type)
        
        if start_date:
            if isinstance(start_date, str):
                start_date = datetime.strptime(start_date, "%Y-%m-%d")
            query += " AND transaction_date >= ?"
            params.append(start_date)
        
        if end_date:
            if isinstance(end_date, str):
                end_date = datetime.strptime(end_date, "%Y-%m-%d")
            query += " AND transaction_date <= ?"
            params.append(end_date)
        
        query += " ORDER BY transaction_date"
        
        with self.lock:
            conn, cursor = self.get_connection()
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    def get_transactions_df(self, wallet_id=None, crypto_symbol=None, 
                           transaction_type=None, start_date=None, end_date=None):
        """Get transactions as a pandas DataFrame."""
        transactions = self.get_transactions(wallet_id, crypto_symbol, 
                                           transaction_type, start_date, end_date)
        if transactions:
            return pd.DataFrame(transactions)
        return pd.DataFrame()
    
    def get_crypto_symbols(self):
        """Get all unique cryptocurrency symbols from transactions."""
        with self.lock:
            conn, cursor = self.get_connection()
            cursor.execute("SELECT DISTINCT crypto_symbol FROM transactions")
            return [row[0] for row in cursor.fetchall()]
    
    def delete_transaction(self, transaction_id):
        """Delete a transaction by ID."""
        with self.lock:
            conn, cursor = self.get_connection()
            cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def update_transaction(self, transaction_id, **kwargs):
        """Update a transaction by ID with the provided field values."""
        if not kwargs:
            return False
            
        # Build the SET part of the SQL query dynamically
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values())
        values.append(transaction_id)
        
        with self.lock:
            conn, cursor = self.get_connection()
            query = f"UPDATE transactions SET {set_clause} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            return cursor.rowcount > 0
    
    def export_to_csv(self, filepath, wallet_id=None):
        """Export transactions to a CSV file."""
        df = self.get_transactions_df(wallet_id=wallet_id)
        if not df.empty:
            df.to_csv(filepath, index=False)
            return True
        return False
    
    def close(self):
        """Close the database connection."""
        with self.lock:
            if self.conn:
                self.conn.close()
