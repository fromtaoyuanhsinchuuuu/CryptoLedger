import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
import time
import base64
import io

from database import Database
from transaction_manager import TransactionManager
from portfolio import Portfolio
from calculator import ProfitLossCalculator
from tax_reporter import TaxReporter
from crypto_api import CryptoAPI
from utils import (
    format_currency, create_portfolio_pie_chart, create_line_chart,
    validate_date_str, validate_crypto_symbol, safe_float
)

# Set page config
st.set_page_config(
    page_title="Crypto Accounting",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state if not already done
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.selected_wallet = None
    st.session_state.fiat_currency = "USD"
    st.session_state.show_transaction_form = False
    st.session_state.transaction_success = False
    st.session_state.transaction_error = None
    st.session_state.refresh_portfolio = True

# Initialize components
@st.cache_resource
def get_database():
    return Database()

db = get_database()

# Add default wallets if none exist
wallets = db.get_wallets()
if not wallets:
    # Add some default wallets for demonstration
    db.add_wallet("Exchange Wallet", "For assets held on cryptocurrency exchanges")
    db.add_wallet("Hardware Wallet", "For cold storage of cryptocurrencies")
    db.add_wallet("DeFi Wallet", "For DeFi protocol interactions")

transaction_manager = TransactionManager(db)
crypto_api = CryptoAPI()
portfolio = Portfolio(crypto_api=crypto_api)
calculator = ProfitLossCalculator()
tax_reporter = TaxReporter(calculator)

# Sidebar navigation
st.sidebar.title("Crypto Accounting")

# Wallet selection
wallets = db.get_wallets()
wallet_options = ["All Wallets"] + [f"{w['name']} (ID: {w['id']})" for w in wallets]

selected_wallet_name = st.sidebar.selectbox(
    "Select Wallet",
    wallet_options,
    index=0
)

if selected_wallet_name == "All Wallets":
    st.session_state.selected_wallet = None
else:
    wallet_id = int(selected_wallet_name.split("ID: ")[1].strip(")"))
    st.session_state.selected_wallet = wallet_id

# Fiat currency selection
currencies = ["USD", "EUR", "GBP", "JPY", "CNY", "KRW", "INR", "RUB"]
st.session_state.fiat_currency = st.sidebar.selectbox(
    "Fiat Currency",
    currencies,
    index=currencies.index(st.session_state.fiat_currency)
)

# Navigation menu
nav_options = [
    "Dashboard", 
    "Portfolio", 
    "Transactions",
    "Tax Reports", 
    "Price Lookup",
    "Settings"
]
selected_nav = st.sidebar.radio("Navigation", nav_options)

# Add wallet section
st.sidebar.markdown("---")
with st.sidebar.expander("Add New Wallet"):
    with st.form("new_wallet_form"):
        wallet_name = st.text_input("Wallet Name")
        wallet_description = st.text_area("Description")
        submit_wallet = st.form_submit_button("Add Wallet")
        
        if submit_wallet and wallet_name:
            success = db.add_wallet(wallet_name, wallet_description)
            if success:
                st.success(f"Wallet '{wallet_name}' added successfully!")
                time.sleep(1)
                st.rerun()
            else:
                st.error(f"Failed to add wallet. Name '{wallet_name}' might already exist.")

# Dashboard Page
if selected_nav == "Dashboard":
    st.title("Crypto Accounting Dashboard")
    
    # Get all transactions
    transactions = transaction_manager.get_transactions(wallet_id=st.session_state.selected_wallet)
    
    # Load transactions into portfolio and calculator
    portfolio.load_transactions(transactions)
    calculator.load_transactions(transactions)
    
    # Portfolio summary
    portfolio_value = portfolio.get_portfolio_value(st.session_state.fiat_currency)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            "Total Portfolio Value", 
            format_currency(portfolio_value['total_value'], st.session_state.fiat_currency),
            delta=None
        )
    
    # Calculate realized and unrealized gains
    current_prices = {}
    if portfolio_value['items']:
        symbols = [item['crypto_symbol'] for item in portfolio_value['items']]
        current_prices = crypto_api.get_current_price(symbols, st.session_state.fiat_currency)
    
    unrealized_gains = calculator.calculate_unrealized_gains(current_prices)
    realized_gains = calculator.calculate_realized_gains()
    
    with col2:
        st.metric(
            "Realized Gains/Losses", 
            format_currency(realized_gains['total_gains'], st.session_state.fiat_currency),
            delta=None
        )
    
    with col3:
        st.metric(
            "Unrealized Gains/Losses", 
            format_currency(unrealized_gains['total_unrealized_gain'], st.session_state.fiat_currency),
            delta=None
        )
    
    # Portfolio distribution chart
    st.subheader("Portfolio Distribution")
    distribution = portfolio.get_portfolio_distribution(st.session_state.fiat_currency)
    
    if distribution['distribution']:
        distribution_fig = create_portfolio_pie_chart(distribution)
        st.plotly_chart(distribution_fig, use_container_width=True)
    else:
        st.info("No holdings found to display portfolio distribution.")
    
    # Recent transactions
    st.subheader("Recent Transactions")
    recent_tx_df = transaction_manager.get_transactions_dataframe(
        wallet_id=st.session_state.selected_wallet,
    )
    
    if not recent_tx_df.empty:
        # Sort by date descending and get the latest 10
        recent_tx_df = recent_tx_df.sort_values('transaction_date', ascending=False).head(10)
        
        # Format for display
        if 'transaction_date' in recent_tx_df.columns:
            recent_tx_df['transaction_date'] = pd.to_datetime(recent_tx_df['transaction_date']).dt.strftime('%Y-%m-%d')
        
        # Display as table
        st.dataframe(
            recent_tx_df[['transaction_date', 'transaction_type', 'crypto_symbol', 'quantity', 'price_per_unit', 'fiat_currency']],
            use_container_width=True
        )
    else:
        st.info("No recent transactions found.")

# Portfolio Page
elif selected_nav == "Portfolio":
    st.title("Cryptocurrency Portfolio")
    
    # Get all transactions
    transactions = transaction_manager.get_transactions(wallet_id=st.session_state.selected_wallet)
    
    # Load transactions into portfolio
    portfolio.load_transactions(transactions)
    
    # Get portfolio value
    portfolio_value = portfolio.get_portfolio_value(st.session_state.fiat_currency)
    
    # Display portfolio summary
    st.header("Portfolio Summary")
    
    if portfolio_value['items']:
        # Create DataFrame for better display
        items_df = pd.DataFrame(portfolio_value['items'])
        
        # Calculate and add percentage of portfolio
        total_value = portfolio_value['total_value']
        if total_value > 0:
            items_df['percentage'] = items_df['current_value'].apply(
                lambda x: (x / total_value) * 100 if x is not None else 0
            )
        
        # Format columns
        items_df['current_price'] = items_df['current_price'].apply(
            lambda x: format_currency(x, st.session_state.fiat_currency) if x is not None else "N/A"
        )
        items_df['current_value'] = items_df['current_value'].apply(
            lambda x: format_currency(x, st.session_state.fiat_currency) if x is not None else "N/A"
        )
        items_df['percentage'] = items_df['percentage'].apply(
            lambda x: f"{x:.2f}%" if x > 0 else "N/A"
        )
        
        # Rename columns for display
        items_df = items_df.rename(columns={
            'crypto_symbol': 'Symbol',
            'quantity': 'Quantity',
            'current_price': 'Current Price',
            'current_value': 'Current Value',
            'percentage': 'Portfolio %'
        })
        
        # Display portfolio table
        st.dataframe(items_df, use_container_width=True)
        
        # Display total value
        st.metric(
            "Total Portfolio Value", 
            format_currency(portfolio_value['total_value'], st.session_state.fiat_currency)
        )
        
        # Portfolio distribution chart
        st.subheader("Portfolio Distribution")
        distribution = portfolio.get_portfolio_distribution(st.session_state.fiat_currency)
        
        if distribution['distribution']:
            distribution_fig = create_portfolio_pie_chart(distribution)
            st.plotly_chart(distribution_fig, use_container_width=True)
        
        # Historical portfolio value chart
        st.subheader("Historical Portfolio Value (30 Days)")
        historical_df = portfolio.get_historical_portfolio_value(30, st.session_state.fiat_currency)
        
        if not historical_df.empty:
            historical_fig = create_line_chart(
                historical_df, 
                'date', 
                'value', 
                f"Portfolio Value History ({st.session_state.fiat_currency})",
                st.session_state.fiat_currency
            )
            st.plotly_chart(historical_fig, use_container_width=True)
        else:
            st.info("No historical data available for chart.")
    else:
        st.info("No holdings found in portfolio. Add transactions to see your portfolio.")

# Transactions Page
elif selected_nav == "Transactions":
    st.title("Transactions Management")
    
    # Tabs for different transaction functions
    transaction_tabs = st.tabs(["View Transactions", "Add Transaction", "Import/Export"])
    
    # View Transactions Tab
    with transaction_tabs[0]:
        st.header("View Transactions")
        
        # Filters
        col1, col2, col3 = st.columns(3)
        
        with col1:
            # Cryptocurrency filter
            crypto_symbols = ["All"] + db.get_crypto_symbols()
            selected_symbol = st.selectbox("Cryptocurrency", crypto_symbols)
            if selected_symbol == "All":
                selected_symbol = None
        
        with col2:
            # Transaction type filter
            tx_types = ["All", "buy", "sell", "exchange", "transfer_in", "transfer_out"]
            selected_type = st.selectbox("Transaction Type", tx_types)
            if selected_type == "All":
                selected_type = None
        
        with col3:
            # Date range filter
            date_range = st.date_input(
                "Date Range",
                value=(datetime.now() - timedelta(days=30), datetime.now()),
                max_value=datetime.now()
            )
            
            if len(date_range) == 2:
                start_date, end_date = date_range
            else:
                start_date, end_date = None, None
        
        # Get transactions with filters
        transactions_df = transaction_manager.get_transactions_dataframe(
            wallet_id=st.session_state.selected_wallet,
            crypto_symbol=selected_symbol,
            transaction_type=selected_type,
            start_date=start_date,
            end_date=end_date
        )
        
        if not transactions_df.empty:
            # Format for display
            if 'transaction_date' in transactions_df.columns:
                transactions_df['transaction_date'] = pd.to_datetime(transactions_df['transaction_date']).dt.strftime('%Y-%m-%d')
            
            # Add total cost column
            transactions_df['total_cost'] = transactions_df['quantity'] * transactions_df['price_per_unit']
            
            # Add total with fee column
            transactions_df['total_with_fee'] = transactions_df['total_cost'] + transactions_df['fee']
            
            # Display as dataframe
            st.dataframe(transactions_df, use_container_width=True)
            
            # Allow selecting a transaction to delete
            if not transactions_df.empty and 'id' in transactions_df.columns:
                transaction_ids = transactions_df['id'].tolist()
                
                with st.expander("Delete Transaction"):
                    tx_to_delete = st.selectbox("Select Transaction ID to Delete", transaction_ids)
                    if st.button("Delete Selected Transaction"):
                        success = transaction_manager.delete_transaction(tx_to_delete)
                        if success:
                            st.success(f"Transaction ID {tx_to_delete} deleted successfully!")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"Failed to delete transaction ID {tx_to_delete}.")
                
        else:
            st.info("No transactions found with the current filters.")
    
    # Add Transaction Tab
    with transaction_tabs[1]:
        st.header("Add New Transaction")
        
        with st.form("add_transaction_form"):
            # Get wallet ID for this transaction
            wallet_options = db.get_wallets()
            if not wallet_options:
                st.warning("You need to create a wallet first before adding transactions.")
                wallet_id = None
            else:
                wallet_names = [f"{w['name']} (ID: {w['id']})" for w in wallet_options]
                selected_wallet_name = st.selectbox("Wallet", wallet_names)
                wallet_id = int(selected_wallet_name.split("ID: ")[1].strip(")"))
            
            # Transaction fields
            col1, col2 = st.columns(2)
            
            with col1:
                tx_type = st.selectbox(
                    "Transaction Type",
                    ["buy", "sell", "exchange", "transfer_in", "transfer_out"]
                )
                
                crypto_symbol = st.text_input("Cryptocurrency Symbol (e.g., BTC)")
                
                quantity = st.number_input(
                    "Quantity",
                    min_value=0.0,
                    format="%.8f"
                )
            
            with col2:
                price_per_unit = st.number_input(
                    "Price per Unit",
                    min_value=0.0,
                    format="%.2f"
                )
                
                fiat_currency = st.selectbox(
                    "Fiat Currency",
                    currencies,
                    index=currencies.index(st.session_state.fiat_currency)
                )
                
                fee = st.number_input(
                    "Transaction Fee",
                    min_value=0.0,
                    format="%.2f"
                )
            
            # Date and notes
            tx_date = st.date_input(
                "Transaction Date",
                value=datetime.now(),
                max_value=datetime.now()
            )
            
            notes = st.text_area("Notes")
            
            # Submit button
            submit_tx = st.form_submit_button("Add Transaction")
            
            if submit_tx:
                if not wallet_id:
                    st.error("Please create a wallet first before adding transactions.")
                elif not validate_crypto_symbol(crypto_symbol):
                    st.error(f"Invalid cryptocurrency symbol: {crypto_symbol}")
                elif quantity <= 0:
                    st.error("Quantity must be greater than zero.")
                else:
                    try:
                        tx_id = transaction_manager.add_transaction(
                            wallet_id=wallet_id,
                            transaction_type=tx_type,
                            crypto_symbol=crypto_symbol,
                            quantity=quantity,
                            price_per_unit=price_per_unit,
                            fiat_currency=fiat_currency,
                            fee=fee,
                            transaction_date=tx_date,
                            notes=notes
                        )
                        st.success(f"Transaction added successfully with ID: {tx_id}")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to add transaction: {e}")
    
    # Import/Export Tab
    with transaction_tabs[2]:
        st.header("Import/Export Transactions")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Import from CSV")
            
            # Get wallet ID for import
            wallet_options = db.get_wallets()
            if not wallet_options:
                st.warning("You need to create a wallet first before importing transactions.")
                import_wallet_id = None
            else:
                wallet_names = [f"{w['name']} (ID: {w['id']})" for w in wallet_options]
                import_wallet_name = st.selectbox("Import to Wallet", wallet_names)
                import_wallet_id = int(import_wallet_name.split("ID: ")[1].strip(")"))
            
            # File upload
            uploaded_file = st.file_uploader("Upload CSV File", type="csv")
            
            if uploaded_file is not None and import_wallet_id:
                # Save the file temporarily
                with open("temp_import.csv", "wb") as f:
                    f.write(uploaded_file.getvalue())
                
                if st.button("Import Transactions"):
                    try:
                        count = transaction_manager.import_transactions_from_csv("temp_import.csv", import_wallet_id)
                        st.success(f"Successfully imported {count} transactions.")
                        # Remove temp file
                        if os.path.exists("temp_import.csv"):
                            os.remove("temp_import.csv")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to import transactions: {e}")
                        # Remove temp file
                        if os.path.exists("temp_import.csv"):
                            os.remove("temp_import.csv")
            
            st.markdown("### CSV Format")
            st.markdown("""
                Your CSV file should have the following columns:
                - transaction_type (buy, sell, exchange, transfer_in, transfer_out)
                - crypto_symbol
                - quantity
                - price_per_unit
                - transaction_date (YYYY-MM-DD)
                
                Optional columns:
                - fiat_currency (default: USD)
                - fee (default: 0)
                - notes
            """)
        
        with col2:
            st.subheader("Export to CSV")
            
            export_all = st.checkbox("Export all wallets", value=st.session_state.selected_wallet is None)
            
            if st.button("Export Transactions"):
                # Create a temporary file
                temp_file = "temp_export.csv"
                
                if export_all:
                    export_wallet_id = None
                else:
                    export_wallet_id = st.session_state.selected_wallet
                
                try:
                    success = transaction_manager.export_transactions_to_csv(temp_file, export_wallet_id)
                    
                    if success and os.path.exists(temp_file):
                        # Read the file and offer for download
                        with open(temp_file, "rb") as f:
                            csv_data = f.read()
                        
                        b64 = base64.b64encode(csv_data).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="crypto_transactions.csv">Download CSV File</a>'
                        st.markdown(href, unsafe_allow_html=True)
                        
                        # Remove temp file
                        os.remove(temp_file)
                    else:
                        st.warning("No transactions to export.")
                except Exception as e:
                    st.error(f"Failed to export transactions: {e}")
                    if os.path.exists(temp_file):
                        os.remove(temp_file)

# Tax Reports Page
elif selected_nav == "Tax Reports":
    st.title("Tax Reports")
    
    # Get all transactions
    transactions = transaction_manager.get_transactions(wallet_id=st.session_state.selected_wallet)
    
    # Load transactions into calculator
    calculator.load_transactions(transactions)
    
    # Tax year selection
    current_year = datetime.now().year
    year_options = list(range(current_year - 5, current_year + 1))
    selected_year = st.selectbox("Tax Year", year_options, index=len(year_options) - 1)
    
    # Generate tax report
    if st.button("Generate Tax Report"):
        report = tax_reporter.generate_report(selected_year, st.session_state.fiat_currency)
        
        st.header(f"Tax Report for {report.year}")
        
        # Summary metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "Short-term Gains/Losses", 
                format_currency(report.short_term_gains, report.fiat_currency)
            )
        
        with col2:
            st.metric(
                "Long-term Gains/Losses", 
                format_currency(report.long_term_gains, report.fiat_currency)
            )
        
        with col3:
            st.metric(
                "Total Gains/Losses", 
                format_currency(report.total_gains, report.fiat_currency)
            )
        
        # Transactions table
        st.subheader("Realized Gains/Losses Transactions")
        
        if report.transactions:
            # Convert to DataFrame for display
            tx_df = pd.DataFrame(report.transactions)
            
            # Format dates
            date_columns = ['buy_date', 'sell_date']
            for col in date_columns:
                if col in tx_df.columns:
                    tx_df[col] = pd.to_datetime(tx_df[col]).dt.strftime('%Y-%m-%d')
            
            # Display table
            st.dataframe(tx_df, use_container_width=True)
            
            # Export options
            if st.button("Export to CSV"):
                # Create a temporary file
                temp_dir = "temp_reports"
                os.makedirs(temp_dir, exist_ok=True)
                
                try:
                    filepath = tax_reporter.export_report_to_csv(report, temp_dir)
                    summary_filepath = tax_reporter.export_report_to_summary_csv(report, temp_dir)
                    
                    # Read the files and offer for download
                    with open(filepath, "rb") as f:
                        csv_data = f.read()
                    
                    with open(summary_filepath, "rb") as f:
                        summary_data = f.read()
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        b64 = base64.b64encode(csv_data).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="crypto_tax_report_{report.year}.csv">Download Detailed Report</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    
                    with col2:
                        b64 = base64.b64encode(summary_data).decode()
                        href = f'<a href="data:file/csv;base64,{b64}" download="crypto_tax_summary_{report.year}.csv">Download Summary Report</a>'
                        st.markdown(href, unsafe_allow_html=True)
                    
                    # Remove temp files
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    if os.path.exists(summary_filepath):
                        os.remove(summary_filepath)
                    
                except Exception as e:
                    st.error(f"Failed to export tax report: {e}")
        else:
            st.info(f"No realized gains/losses found for {selected_year}.")

# Price Lookup Page
elif selected_nav == "Price Lookup":
    st.title("Cryptocurrency Price Lookup")
    
    price_tabs = st.tabs(["Current Price", "Historical Price", "Price Chart"])
    
    # Current Price Tab
    with price_tabs[0]:
        st.header("Current Price")
        
        col1, col2 = st.columns(2)
        
        with col1:
            current_symbol = st.text_input("Cryptocurrency Symbol", "BTC", key="current_symbol")
        
        with col2:
            current_fiat = st.selectbox(
                "Fiat Currency",
                currencies,
                index=currencies.index(st.session_state.fiat_currency),
                key="current_fiat"
            )
        
        if st.button("Get Current Price", key="get_current_price_btn") and current_symbol:
            if not validate_crypto_symbol(current_symbol):
                st.error(f"Invalid cryptocurrency symbol: {current_symbol}")
            else:
                with st.spinner("Fetching current price..."):
                    prices = crypto_api.get_current_price(current_symbol, current_fiat)
                    
                    if prices and current_symbol.upper() in prices:
                        price = prices[current_symbol.upper()]
                        st.success(f"Current price of {current_symbol.upper()}: {format_currency(price, current_fiat)}")
                    else:
                        st.error(f"Failed to get price for {current_symbol.upper()}")
    
    # Historical Price Tab
    with price_tabs[1]:
        st.header("Historical Price")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            hist_symbol = st.text_input("Cryptocurrency Symbol", "BTC", key="hist_symbol")
        
        with col2:
            hist_date = st.date_input(
                "Date",
                value=datetime.now() - timedelta(days=1),
                max_value=datetime.now(),
                key="hist_date"
            )
        
        with col3:
            hist_fiat = st.selectbox(
                "Fiat Currency",
                currencies,
                index=currencies.index(st.session_state.fiat_currency),
                key="hist_fiat"
            )
        
        if st.button("Get Historical Price", key="get_historical_price_btn") and hist_symbol:
            if not validate_crypto_symbol(hist_symbol):
                st.error(f"Invalid cryptocurrency symbol: {hist_symbol}")
            else:
                with st.spinner("Fetching historical price..."):
                    price = crypto_api.get_historical_price(
                        hist_symbol, 
                        hist_date.strftime("%Y-%m-%d"), 
                        hist_fiat
                    )
                    
                    if price is not None:
                        st.success(f"Price of {hist_symbol.upper()} on {hist_date.strftime('%Y-%m-%d')}: {format_currency(price, hist_fiat)}")
                    else:
                        st.error(f"Failed to get historical price for {hist_symbol.upper()} on {hist_date.strftime('%Y-%m-%d')}")
    
    # Price Chart Tab
    with price_tabs[2]:
        st.header("Price Chart")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            chart_symbol = st.text_input("Cryptocurrency Symbol", "BTC", key="chart_symbol")
        
        with col2:
            chart_days = st.slider("Number of Days", 1, 365, 30, key="chart_days")
        
        with col3:
            chart_fiat = st.selectbox(
                "Fiat Currency",
                currencies,
                index=currencies.index(st.session_state.fiat_currency),
                key="chart_fiat"
            )
        
        if st.button("Generate Chart", key="generate_chart_btn") and chart_symbol:
            if not validate_crypto_symbol(chart_symbol):
                st.error(f"Invalid cryptocurrency symbol: {chart_symbol}")
            else:
                with st.spinner("Generating price chart..."):
                    chart_data = crypto_api.get_market_chart(chart_symbol, chart_days, chart_fiat)
                    
                    if chart_data is not None and not chart_data.empty:
                        fig = create_line_chart(
                            chart_data,
                            'date',
                            'price',
                            f"{chart_symbol.upper()} Price ({chart_days} Days)",
                            chart_fiat
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.error(f"Failed to get chart data for {chart_symbol.upper()}")

# Settings Page
elif selected_nav == "Settings":
    st.title("Settings")
    
    # Application settings
    st.header("Application Settings")
    
    # Default fiat currency
    default_fiat = st.selectbox(
        "Default Fiat Currency",
        currencies,
        index=currencies.index(st.session_state.fiat_currency),
        key="default_fiat"
    )
    
    if default_fiat != st.session_state.fiat_currency:
        st.session_state.fiat_currency = default_fiat
        st.success(f"Default currency changed to {default_fiat}")
    
    # Database operations
    st.header("Database Operations")
    
    with st.expander("Database Information"):
        # Get database stats
        wallets = db.get_wallets()
        wallet_count = len(wallets)
        
        all_transactions = transaction_manager.get_transactions()
        tx_count = len(all_transactions)
        
        crypto_symbols = db.get_crypto_symbols()
        symbol_count = len(crypto_symbols)
        
        st.write(f"Wallets: {wallet_count}")
        st.write(f"Transactions: {tx_count}")
        st.write(f"Cryptocurrencies: {symbol_count}")
        
        if crypto_symbols:
            st.write("Tracked cryptocurrencies:")
            st.write(", ".join(crypto_symbols))
    
    # Export/Import database
    with st.expander("Export All Data"):
        if st.button("Export All Transactions", key="export_transactions_btn"):
            # Create a temporary file
            temp_file = "all_transactions_export.csv"
            
            try:
                success = transaction_manager.export_transactions_to_csv(temp_file)
                
                if success and os.path.exists(temp_file):
                    # Read the file and offer for download
                    with open(temp_file, "rb") as f:
                        csv_data = f.read()
                    
                    b64 = base64.b64encode(csv_data).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="all_crypto_transactions.csv">Download All Transactions</a>'
                    st.markdown(href, unsafe_allow_html=True)
                    
                    # Remove temp file
                    os.remove(temp_file)
                else:
                    st.warning("No transactions to export.")
            except Exception as e:
                st.error(f"Failed to export transactions: {e}")
                if os.path.exists(temp_file):
                    os.remove(temp_file)

# Footer
st.markdown("---")
st.markdown("Cryptocurrency Accounting App © 2023")
