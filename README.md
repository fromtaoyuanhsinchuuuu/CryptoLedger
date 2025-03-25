# CryptoLedger

A comprehensive cryptocurrency transaction tracking and tax reporting application with both CLI and web interfaces.

## Features

- Track cryptocurrency transactions (buy, sell, exchange, transfers)
- Manage multiple wallets/accounts
- Calculate portfolio performance and holdings
- Generate tax reports with capital gains calculations
- Fetch real-time cryptocurrency price data
- View transaction history and portfolio through a web interface or command-line

## Requirements

- Python 3.11+
- Dependencies:
  - pandas
  - plotly
  - requests
  - streamlit

## Installation

```bash
# Clone the repository
git clone https://github.com/YOUR-USERNAME/CryptoLedger.git
cd CryptoLedger

# Install dependencies
pip install -e .
```

## Usage

### Web Interface

```bash
streamlit run app.py
```

### Command Line Interface

```bash
python cli.py --help
```

## Project Structure

- `models.py`: Data models for transactions, wallets, etc.
- `database.py`: Database operations and persistence
- `crypto_api.py`: Cryptocurrency API integration
- `transaction_manager.py`: Transaction management functions
- `portfolio.py`: Portfolio calculation and analysis
- `calculator.py`: Financial calculations
- `tax_reporter.py`: Tax reporting functionality
- `utils.py`: Utility functions
- `cli.py`: Command-line interface
- `app.py`: Streamlit web application

## License

[MIT License](LICENSE) 