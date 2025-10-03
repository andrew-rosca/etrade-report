#!/usr/bin/env python3
"""
E*TRADE Portfolio Data Module

This module provides utility functions for transforming E*TRADE API data.
Used by dashboard.py for the Streamlit visualization.

The transform_etrade_position function converts E*TRADE API position format
to a standardized dictionary format with dividend information.
"""


def transform_etrade_position(etrade_position: dict) -> dict:
    """Transform E*TRADE position data to expected dictionary format with dividend info."""
    try:
        # Extract basic position info
        symbol = etrade_position.get('symbolDescription', '')
        quantity = float(etrade_position.get('quantity', 0))
        market_value = float(etrade_position.get('marketValue', 0))
        total_gain = float(etrade_position.get('totalGain', 0))
        total_gain_pct = float(etrade_position.get('totalGainPct', 0))
        
        # Get current price from Quick quote data
        quick_data = etrade_position.get('Quick', {})
        current_price = float(quick_data.get('lastTrade', 0))
        
        # If no current price in Quick, calculate from market value and quantity
        if current_price == 0 and quantity > 0:
            current_price = market_value / quantity
        

        
        # Extract dividend information from Complete section (available with complete view)
        complete_data = etrade_position.get('Complete', {})
        annual_dividend = float(complete_data.get('annualDividend', 0))
        dividend = float(complete_data.get('dividend', 0))
        div_yield = float(complete_data.get('divYield', 0))
        div_pay_date = complete_data.get('divPayDate', '')
        ex_dividend_date = complete_data.get('exDividendDate', '')
        
        # Calculate annual dividend income from this position
        annual_dividend_income = annual_dividend * quantity if annual_dividend > 0 else 0
            
        return {
            'symbol': symbol,
            'description': symbol,  # Keep using symbol as description
            'quantity': quantity,
            'current_price': current_price,
            'market_value': market_value,
            'gain_loss': total_gain,
            'gain_loss_pct': total_gain_pct,
            'annual_dividend': annual_dividend,
            'dividend': dividend,
            'div_yield': div_yield,
            'div_pay_date': div_pay_date,
            'ex_dividend_date': ex_dividend_date,
            'annual_dividend_income': annual_dividend_income
        }
    except (KeyError, ValueError, TypeError) as e:
        print(f"⚠️  Warning: Could not transform position {etrade_position.get('symbolDescription', 'Unknown')}: {e}")
        # Return a minimal position to avoid breaking the entire report
        return {
            'symbol': etrade_position.get('symbolDescription', 'Unknown'),
            'description': etrade_position.get('symbolDescription', 'Unknown'),
            'quantity': 0.0,
            'current_price': 0.0,
            'market_value': 0.0,
            'gain_loss': 0.0,
            'gain_loss_pct': 0.0
        }


