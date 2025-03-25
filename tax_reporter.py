import pandas as pd
from datetime import datetime
import os
from typing import List, Dict, Optional
from models import TaxReport
from calculator import ProfitLossCalculator

class TaxReporter:
    """Class for generating tax reports from cryptocurrency transactions."""
    
    def __init__(self, calculator: ProfitLossCalculator = None):
        """
        Initialize TaxReporter with a calculator.
        
        Args:
            calculator: ProfitLossCalculator instance
        """
        self.calculator = calculator or ProfitLossCalculator()
    
    def generate_report(self, year: int, fiat_currency: str = "USD") -> TaxReport:
        """
        Generate a tax report for a specific year.
        
        Args:
            year: Tax year to generate report for
            fiat_currency: Fiat currency to use (default: USD)
        
        Returns:
            TaxReport object with report data
        """
        # Calculate realized gains for the specified year
        gains_data = self.calculator.calculate_realized_gains(year)
        
        # Create report
        report = TaxReport(
            year=year,
            fiat_currency=fiat_currency,
            short_term_gains=gains_data['short_term_gains'],
            long_term_gains=gains_data['long_term_gains'],
            transactions=gains_data['transactions']
        )
        
        return report
    
    def export_report_to_csv(self, report: TaxReport, directory: str = ".") -> str:
        """
        Export tax report to CSV file.
        
        Args:
            report: TaxReport object
            directory: Directory to save file to (default: current directory)
        
        Returns:
            Path to the saved file
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        filename = f"crypto_tax_report_{report.year}_{report.fiat_currency}.csv"
        filepath = os.path.join(directory, filename)
        
        # Convert transactions to DataFrame
        if report.transactions:
            df = pd.DataFrame(report.transactions)
            
            # Format dates
            if 'buy_date' in df.columns:
                df['buy_date'] = pd.to_datetime(df['buy_date']).dt.strftime('%Y-%m-%d')
            if 'sell_date' in df.columns:
                df['sell_date'] = pd.to_datetime(df['sell_date']).dt.strftime('%Y-%m-%d')
            
            # Save to CSV
            df.to_csv(filepath, index=False)
        else:
            # Create an empty CSV with headers
            pd.DataFrame(columns=[
                'buy_date', 'sell_date', 'buy_price', 'sell_price', 'quantity',
                'cost_basis', 'proceeds', 'gain', 'term', 'holding_period_days',
                'buy_transaction_id', 'sell_transaction_id'
            ]).to_csv(filepath, index=False)
        
        return filepath
    
    def export_report_to_summary_csv(self, report: TaxReport, directory: str = ".") -> str:
        """
        Export tax report summary to CSV file.
        
        Args:
            report: TaxReport object
            directory: Directory to save file to (default: current directory)
        
        Returns:
            Path to the saved file
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
        
        filename = f"crypto_tax_summary_{report.year}_{report.fiat_currency}.csv"
        filepath = os.path.join(directory, filename)
        
        # Create summary DataFrame
        summary_data = {
            'Year': [report.year],
            'Short Term Gains': [report.short_term_gains],
            'Long Term Gains': [report.long_term_gains],
            'Total Gains': [report.total_gains],
            'Currency': [report.fiat_currency],
            'Generated On': [datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        }
        
        summary_df = pd.DataFrame(summary_data)
        summary_df.to_csv(filepath, index=False)
        
        return filepath
    
    def generate_transaction_summary(self, report: TaxReport) -> Dict:
        """
        Generate summary statistics for transactions in the report.
        
        Args:
            report: TaxReport object
        
        Returns:
            Dictionary with summary statistics
        """
        if not report.transactions:
            return {
                'transaction_count': 0,
                'symbols': [],
                'largest_gain': 0,
                'largest_loss': 0,
                'average_gain': 0,
                'average_holding_period': 0
            }
        
        # Convert to DataFrame for easier analysis
        df = pd.DataFrame(report.transactions)
        
        # Calculate summary statistics
        summary = {
            'transaction_count': len(df),
            'symbols': list(df['quantity'].value_counts().index) if 'quantity' in df.columns else [],
            'largest_gain': df['gain'].max() if 'gain' in df.columns else 0,
            'largest_loss': df['gain'].min() if 'gain' in df.columns else 0,
            'average_gain': df['gain'].mean() if 'gain' in df.columns else 0,
            'average_holding_period': df['holding_period_days'].mean() if 'holding_period_days' in df.columns else 0
        }
        
        return summary
