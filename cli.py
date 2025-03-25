import argparse
import sys
from datetime import datetime
import os
import csv
from typing import Dict, List, Optional

from database import Database
from transaction_manager import TransactionManager
from portfolio import Portfolio
from calculator import ProfitLossCalculator
from tax_reporter import TaxReporter
from crypto_api import CryptoAPI
from utils import format_currency, validate_date_str, validate_crypto_symbol, safe_float

class CryptoAccountingCLI:
    """Command-line interface for cryptocurrency accounting application."""
    
    def __init__(self):
        """Initialize the CLI with necessary components."""
        self.db = Database()
        self.transaction_manager = TransactionManager(self.db)
        self.crypto_api = CryptoAPI()
        self.portfolio = Portfolio(crypto_api=self.crypto_api)
        self.calculator = ProfitLossCalculator()
        self.tax_reporter = TaxReporter(self.calculator)
        
        # Setup argument parser
        self.parser = argparse.ArgumentParser(
            description="Cryptocurrency Accounting CLI",
            prog="crypto-accounting"
        )
        self.setup_commands()
    
    def setup_commands(self):
        """Setup CLI commands and arguments."""
        subparsers = self.parser.add_subparsers(dest="command", help="Command to execute")
        
        # Wallet commands
        wallet_parser = subparsers.add_parser("wallet", help="Wallet management")
        wallet_subparsers = wallet_parser.add_subparsers(dest="wallet_command")
        
        # Add wallet
        add_wallet_parser = wallet_subparsers.add_parser("add", help="Add a new wallet")
        add_wallet_parser.add_argument("name", help="Wallet name")
        add_wallet_parser.add_argument("--description", "-d", help="Wallet description")
        
        # List wallets
        list_wallet_parser = wallet_subparsers.add_parser("list", help="List all wallets")
        
        # Transaction commands
        tx_parser = subparsers.add_parser("tx", help="Transaction management")
        tx_subparsers = tx_parser.add_subparsers(dest="tx_command")
        
        # Add transaction
        add_tx_parser = tx_subparsers.add_parser("add", help="Add a new transaction")
        add_tx_parser.add_argument("--wallet", "-w", type=int, required=True, help="Wallet ID")
        add_tx_parser.add_argument("--type", "-t", required=True, 
                                 choices=["buy", "sell", "exchange", "transfer_in", "transfer_out"],
                                 help="Transaction type")
        add_tx_parser.add_argument("--symbol", "-s", required=True, help="Cryptocurrency symbol (e.g., BTC)")
        add_tx_parser.add_argument("--quantity", "-q", type=float, required=True, help="Quantity")
        add_tx_parser.add_argument("--price", "-p", type=float, required=True, help="Price per unit")
        add_tx_parser.add_argument("--currency", "-c", default="USD", help="Fiat currency (default: USD)")
        add_tx_parser.add_argument("--fee", "-f", type=float, default=0, help="Transaction fee")
        add_tx_parser.add_argument("--date", "-d", help="Transaction date (YYYY-MM-DD)")
        add_tx_parser.add_argument("--notes", "-n", help="Transaction notes")
        
        # List transactions
        list_tx_parser = tx_subparsers.add_parser("list", help="List transactions")
        list_tx_parser.add_argument("--wallet", "-w", type=int, help="Filter by wallet ID")
        list_tx_parser.add_argument("--symbol", "-s", help="Filter by cryptocurrency symbol")
        list_tx_parser.add_argument("--type", "-t", help="Filter by transaction type")
        list_tx_parser.add_argument("--start", help="Start date (YYYY-MM-DD)")
        list_tx_parser.add_argument("--end", help="End date (YYYY-MM-DD)")
        
        # Delete transaction
        delete_tx_parser = tx_subparsers.add_parser("delete", help="Delete a transaction")
        delete_tx_parser.add_argument("id", type=int, help="Transaction ID")
        
        # Import transactions
        import_tx_parser = tx_subparsers.add_parser("import", help="Import transactions from CSV")
        import_tx_parser.add_argument("file", help="CSV file path")
        import_tx_parser.add_argument("--wallet", "-w", type=int, required=True, help="Wallet ID")
        
        # Export transactions
        export_tx_parser = tx_subparsers.add_parser("export", help="Export transactions to CSV")
        export_tx_parser.add_argument("file", help="Output CSV file path")
        export_tx_parser.add_argument("--wallet", "-w", type=int, help="Filter by wallet ID")
        
        # Portfolio commands
        portfolio_parser = subparsers.add_parser("portfolio", help="Portfolio management")
        portfolio_subparsers = portfolio_parser.add_subparsers(dest="portfolio_command")
        
        # View portfolio
        view_portfolio_parser = portfolio_subparsers.add_parser("view", help="View portfolio")
        view_portfolio_parser.add_argument("--currency", "-c", default="USD", help="Fiat currency (default: USD)")
        view_portfolio_parser.add_argument("--wallet", "-w", type=int, help="Filter by wallet ID")
        
        # Tax commands
        tax_parser = subparsers.add_parser("tax", help="Tax reporting")
        tax_subparsers = tax_parser.add_subparsers(dest="tax_command")
        
        # Generate tax report
        generate_tax_parser = tax_subparsers.add_parser("generate", help="Generate tax report")
        generate_tax_parser.add_argument("year", type=int, help="Tax year")
        generate_tax_parser.add_argument("--currency", "-c", default="USD", help="Fiat currency (default: USD)")
        generate_tax_parser.add_argument("--output", "-o", help="Output CSV file path")
        
        # Price commands
        price_parser = subparsers.add_parser("price", help="Cryptocurrency price")
        price_subparsers = price_parser.add_subparsers(dest="price_command")
        
        # Get current price
        get_price_parser = price_subparsers.add_parser("get", help="Get current price")
        get_price_parser.add_argument("symbol", help="Cryptocurrency symbol")
        get_price_parser.add_argument("--currency", "-c", default="USD", help="Fiat currency (default: USD)")
        
        # Get historical price
        get_historical_parser = price_subparsers.add_parser("historical", help="Get historical price")
        get_historical_parser.add_argument("symbol", help="Cryptocurrency symbol")
        get_historical_parser.add_argument("date", help="Date (YYYY-MM-DD)")
        get_historical_parser.add_argument("--currency", "-c", default="USD", help="Fiat currency (default: USD)")
    
    def run(self):
        """Run the CLI application."""
        args = self.parser.parse_args()
        
        if not args.command:
            self.parser.print_help()
            return
        
        try:
            # Handle wallet commands
            if args.command == "wallet":
                self.handle_wallet_command(args)
            
            # Handle transaction commands
            elif args.command == "tx":
                self.handle_transaction_command(args)
            
            # Handle portfolio commands
            elif args.command == "portfolio":
                self.handle_portfolio_command(args)
            
            # Handle tax commands
            elif args.command == "tax":
                self.handle_tax_command(args)
            
            # Handle price commands
            elif args.command == "price":
                self.handle_price_command(args)
            
            else:
                self.parser.print_help()
        
        except Exception as e:
            print(f"Error: {e}")
            sys.exit(1)
        
        finally:
            # Close database connection
            self.db.close()
    
    def handle_wallet_command(self, args):
        """Handle wallet-related commands."""
        if not args.wallet_command:
            self.parser.parse_args(["wallet", "--help"])
            return
        
        if args.wallet_command == "add":
            # Add wallet
            success = self.db.add_wallet(args.name, args.description or "")
            if success:
                print(f"Wallet '{args.name}' added successfully.")
            else:
                print(f"Failed to add wallet. Name '{args.name}' might already exist.")
        
        elif args.wallet_command == "list":
            # List wallets
            wallets = self.db.get_wallets()
            if wallets:
                print("Wallets:")
                for wallet in wallets:
                    print(f"  ID: {wallet['id']}, Name: {wallet['name']}, Description: {wallet['description']}")
            else:
                print("No wallets found.")
    
    def handle_transaction_command(self, args):
        """Handle transaction-related commands."""
        if not args.tx_command:
            self.parser.parse_args(["tx", "--help"])
            return
        
        if args.tx_command == "add":
            # Validate inputs
            if not validate_crypto_symbol(args.symbol):
                print(f"Invalid cryptocurrency symbol: {args.symbol}")
                return
            
            if args.quantity <= 0:
                print("Quantity must be greater than zero.")
                return
            
            if args.price < 0:
                print("Price cannot be negative.")
                return
            
            if args.fee < 0:
                print("Fee cannot be negative.")
                return
            
            # Parse date if provided
            transaction_date = None
            if args.date:
                if not validate_date_str(args.date):
                    print(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
                    return
                transaction_date = datetime.strptime(args.date, "%Y-%m-%d")
            
            # Add transaction
            try:
                tx_id = self.transaction_manager.add_transaction(
                    wallet_id=args.wallet,
                    transaction_type=args.type,
                    crypto_symbol=args.symbol,
                    quantity=args.quantity,
                    price_per_unit=args.price,
                    fiat_currency=args.currency,
                    fee=args.fee,
                    transaction_date=transaction_date,
                    notes=args.notes or ""
                )
                print(f"Transaction added successfully with ID: {tx_id}")
            except Exception as e:
                print(f"Failed to add transaction: {e}")
        
        elif args.tx_command == "list":
            # Parse date filters if provided
            start_date = None
            if args.start:
                if not validate_date_str(args.start):
                    print(f"Invalid start date format: {args.start}. Use YYYY-MM-DD.")
                    return
                start_date = args.start
            
            end_date = None
            if args.end:
                if not validate_date_str(args.end):
                    print(f"Invalid end date format: {args.end}. Use YYYY-MM-DD.")
                    return
                end_date = args.end
            
            # Get transactions
            transactions = self.transaction_manager.get_transactions(
                wallet_id=args.wallet,
                crypto_symbol=args.symbol,
                transaction_type=args.type,
                start_date=start_date,
                end_date=end_date
            )
            
            if transactions:
                print(f"Found {len(transactions)} transactions:")
                for tx in transactions:
                    # Format date
                    date_str = tx['transaction_date']
                    if isinstance(date_str, datetime):
                        date_str = date_str.strftime("%Y-%m-%d")
                    
                    print(f"  ID: {tx['id']}, Date: {date_str}, Type: {tx['transaction_type']}, " +
                          f"Symbol: {tx['crypto_symbol']}, Quantity: {tx['quantity']}, " +
                          f"Price: {format_currency(tx['price_per_unit'], tx['fiat_currency'])}")
            else:
                print("No transactions found.")
        
        elif args.tx_command == "delete":
            # Delete transaction
            success = self.transaction_manager.delete_transaction(args.id)
            if success:
                print(f"Transaction ID {args.id} deleted successfully.")
            else:
                print(f"Failed to delete transaction ID {args.id}. It might not exist.")
        
        elif args.tx_command == "import":
            # Check if file exists
            if not os.path.isfile(args.file):
                print(f"File not found: {args.file}")
                return
            
            # Import transactions
            try:
                count = self.transaction_manager.import_transactions_from_csv(args.file, args.wallet)
                print(f"Successfully imported {count} transactions.")
            except Exception as e:
                print(f"Failed to import transactions: {e}")
        
        elif args.tx_command == "export":
            # Export transactions
            try:
                success = self.transaction_manager.export_transactions_to_csv(args.file, args.wallet)
                if success:
                    print(f"Transactions exported to {args.file} successfully.")
                else:
                    print("No transactions to export.")
            except Exception as e:
                print(f"Failed to export transactions: {e}")
    
    def handle_portfolio_command(self, args):
        """Handle portfolio-related commands."""
        if not args.portfolio_command:
            self.parser.parse_args(["portfolio", "--help"])
            return
        
        if args.portfolio_command == "view":
            # Get transactions
            transactions = self.transaction_manager.get_transactions(wallet_id=args.wallet)
            
            # Load transactions into portfolio
            self.portfolio.load_transactions(transactions)
            
            # Get portfolio value
            portfolio = self.portfolio.get_portfolio_value(args.currency)
            
            if portfolio['items']:
                print(f"Portfolio Value: {format_currency(portfolio['total_value'], portfolio['fiat_currency'])}")
                print("Holdings:")
                for item in portfolio['items']:
                    value_str = "N/A"
                    if item['current_value'] is not None:
                        value_str = format_currency(item['current_value'], portfolio['fiat_currency'])
                    
                    price_str = "N/A"
                    if item['current_price'] is not None:
                        price_str = format_currency(item['current_price'], portfolio['fiat_currency'])
                    
                    print(f"  {item['crypto_symbol']}: {item['quantity']} @ {price_str} = {value_str}")
            else:
                print("No holdings found in portfolio.")
    
    def handle_tax_command(self, args):
        """Handle tax-related commands."""
        if not args.tax_command:
            self.parser.parse_args(["tax", "--help"])
            return
        
        if args.tax_command == "generate":
            # Get all transactions
            transactions = self.transaction_manager.get_transactions()
            
            # Load transactions into calculator
            self.calculator.load_transactions(transactions)
            
            # Generate tax report
            report = self.tax_reporter.generate_report(args.year, args.currency)
            
            # Print report summary
            print(f"Tax Report for {report.year}:")
            print(f"  Short-term gains: {format_currency(report.short_term_gains, report.fiat_currency)}")
            print(f"  Long-term gains: {format_currency(report.long_term_gains, report.fiat_currency)}")
            print(f"  Total gains: {format_currency(report.total_gains, report.fiat_currency)}")
            
            # Export to CSV if output path provided
            if args.output:
                filepath = self.tax_reporter.export_report_to_csv(report, os.path.dirname(args.output))
                print(f"Tax report exported to {filepath}")
    
    def handle_price_command(self, args):
        """Handle price-related commands."""
        if not args.price_command:
            self.parser.parse_args(["price", "--help"])
            return
        
        if args.price_command == "get":
            # Validate symbol
            if not validate_crypto_symbol(args.symbol):
                print(f"Invalid cryptocurrency symbol: {args.symbol}")
                return
            
            # Get current price
            prices = self.crypto_api.get_current_price(args.symbol, args.currency)
            
            if prices and args.symbol.upper() in prices:
                price = prices[args.symbol.upper()]
                print(f"Current price of {args.symbol.upper()}: {format_currency(price, args.currency)}")
            else:
                print(f"Failed to get price for {args.symbol.upper()}")
        
        elif args.price_command == "historical":
            # Validate symbol
            if not validate_crypto_symbol(args.symbol):
                print(f"Invalid cryptocurrency symbol: {args.symbol}")
                return
            
            # Validate date
            if not validate_date_str(args.date):
                print(f"Invalid date format: {args.date}. Use YYYY-MM-DD.")
                return
            
            # Get historical price
            price = self.crypto_api.get_historical_price(args.symbol, args.date, args.currency)
            
            if price is not None:
                print(f"Historical price of {args.symbol.upper()} on {args.date}: {format_currency(price, args.currency)}")
            else:
                print(f"Failed to get historical price for {args.symbol.upper()} on {args.date}")


if __name__ == "__main__":
    cli = CryptoAccountingCLI()
    cli.run()
