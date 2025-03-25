import os
import datetime
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Union, Optional

def validate_date_str(date_str: str) -> bool:
    """
    Validate if a string is in YYYY-MM-DD format.
    
    Args:
        date_str: Date string to validate
    
    Returns:
        True if valid, False otherwise
    """
    try:
        datetime.datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False

def format_currency(amount: float, currency: str = "USD", decimals: int = 2) -> str:
    """
    Format a number as currency.
    
    Args:
        amount: Amount to format
        currency: Currency code
        decimals: Number of decimal places
    
    Returns:
        Formatted currency string
    """
    symbols = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£",
        "JPY": "¥",
        "CNY": "¥",
        "KRW": "₩",
        "INR": "₹",
        "RUB": "₽"
    }
    
    symbol = symbols.get(currency, currency + " ")
    
    if currency in ["JPY", "KRW"]:
        # No decimal places for these currencies
        return f"{symbol}{int(amount):,}"
    
    return f"{symbol}{amount:,.{decimals}f}"

def create_portfolio_pie_chart(distribution_data: Dict) -> go.Figure:
    """
    Create a pie chart for portfolio distribution.
    
    Args:
        distribution_data: Portfolio distribution data
    
    Returns:
        Plotly figure
    """
    if not distribution_data.get('distribution'):
        # Return empty figure if no data
        return go.Figure()
    
    # Prepare data
    labels = [item['symbol'] for item in distribution_data['distribution']]
    values = [item['value'] for item in distribution_data['distribution']]
    
    # Create figure
    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=values,
        hole=.3,
        textinfo='label+percent',
        insidetextorientation='radial'
    )])
    
    fig.update_layout(
        title_text=f"Portfolio Distribution ({distribution_data['fiat_currency']})",
        showlegend=True
    )
    
    return fig

def create_line_chart(df: pd.DataFrame, x_col: str, y_col: str, 
                     title: str, currency: str = None) -> go.Figure:
    """
    Create a line chart.
    
    Args:
        df: DataFrame with data
        x_col: Column for x-axis
        y_col: Column for y-axis
        title: Chart title
        currency: Optional currency for y-axis
    
    Returns:
        Plotly figure
    """
    if df.empty:
        # Return empty figure if no data
        return go.Figure()
    
    fig = px.line(df, x=x_col, y=y_col, title=title)
    
    if currency:
        fig.update_layout(yaxis_title=f"Value ({currency})")
    
    return fig

def create_bar_chart(df: pd.DataFrame, x_col: str, y_col: str, 
                    title: str, currency: str = None) -> go.Figure:
    """
    Create a bar chart.
    
    Args:
        df: DataFrame with data
        x_col: Column for x-axis
        y_col: Column for y-axis
        title: Chart title
        currency: Optional currency for y-axis
    
    Returns:
        Plotly figure
    """
    if df.empty:
        # Return empty figure if no data
        return go.Figure()
    
    fig = px.bar(df, x=x_col, y=y_col, title=title)
    
    if currency:
        fig.update_layout(yaxis_title=f"Value ({currency})")
    
    return fig

def get_transaction_type_color(transaction_type: str) -> str:
    """
    Get a color for a transaction type.
    
    Args:
        transaction_type: Transaction type
    
    Returns:
        Color string
    """
    colors = {
        "buy": "green",
        "sell": "red",
        "exchange": "blue",
        "transfer_in": "purple",
        "transfer_out": "orange"
    }
    
    return colors.get(transaction_type.lower(), "gray")

def validate_crypto_symbol(symbol: str) -> bool:
    """
    Validate if a string is a valid cryptocurrency symbol.
    
    Args:
        symbol: Cryptocurrency symbol to validate
    
    Returns:
        True if valid, False otherwise
    """
    if not symbol or not isinstance(symbol, str):
        return False
    
    # Basic validation: symbols are typically 2-10 uppercase letters
    symbol = symbol.strip().upper()
    return len(symbol) >= 1 and len(symbol) <= 10 and symbol.isalpha()

def safe_float(value: Union[str, float], default: float = 0.0) -> float:
    """
    Safely convert a value to float.
    
    Args:
        value: Value to convert
        default: Default value if conversion fails
    
    Returns:
        Float value
    """
    try:
        return float(value)
    except (ValueError, TypeError):
        return default
