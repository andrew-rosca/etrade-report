#!/usr/bin/env python3
"""
E*TRADE Portfolio Report Generator

This script generates a comprehensive portfolio report showing:
- Holdings categorized into configurable buckets (Growth, Income, Hedge, etc.)
- Allocation percentages for each bucket
- Margin utilization and available cash
- Warnings for unassigned positions

Usage:
    python main.py [--config config.yml] [--account ACCOUNT_ID]

Requirements:
    - E*TRADE API credentials in .env file
    - Portfolio bucket configuration in config.yml
"""

import os
import sys
import argparse
from dotenv import load_dotenv

from etrade_simple_api import ETradeSimpleAPI
from portfolio_analyzer import PortfolioAnalyzer, AccountInfo, PortfolioPosition
from report_formatter import ReportFormatter


def authenticate_etrade_api(client_key: str, client_secret: str, sandbox: bool = False) -> ETradeSimpleAPI:
    """Authenticate with E*TRADE API and return configured client."""
    api = ETradeSimpleAPI(client_key, client_secret, use_sandbox=sandbox)
    
    print("🔐 Starting E*TRADE authentication...")
    if api.authenticate():
        print("✅ Authentication ready!")
        return api
    else:
        print("❌ Authentication failed")
        raise Exception("Failed to authenticate with E*TRADE")


def transform_etrade_position(etrade_position: dict) -> dict:
    """Transform E*TRADE position data to expected dictionary format."""
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
            
        return {
            'symbol': symbol,
            'description': symbol,  # E*TRADE uses symbolDescription for both
            'quantity': quantity,
            'current_price': current_price,
            'market_value': market_value,
            'gain_loss': total_gain,
            'gain_loss_pct': total_gain_pct
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


def get_account_data(api: ETradeSimpleAPI) -> tuple[dict, dict, dict]:
    """Retrieve account data from E*TRADE API."""
    print("📊 Retrieving account data...")
    
    # Get account list with token expiration handling
    accounts = api.get_account_list()
    
    # Check for token expiration in the response
    if isinstance(accounts, dict) and ('oauth_problem' in str(accounts) or 
                                      'token_rejected' in str(accounts) or
                                      accounts.get('message', '').find('oauth_problem') != -1):
        print("🔄 Tokens expired during API call, re-authenticating...")
        api.clear_tokens()
        if not api.authenticate():
            raise Exception("Failed to re-authenticate after token expiration")
        # Retry the account list call
        accounts = api.get_account_list()
    
    if not accounts or 'Accounts' not in accounts:
        print(f"⚠️  Account response: {accounts}")
        raise Exception("Failed to retrieve account list")
    
    # Find the first active account
    account_list = accounts['Accounts']['Account']
    if not isinstance(account_list, list):
        account_list = [account_list]
    
    active_account = None
    for account in account_list:
        if account.get('accountStatus') == 'ACTIVE':
            active_account = account
            break
    
    if not active_account:
        raise Exception("No active accounts found")
    
    account_key = active_account['accountIdKey']
    print(f"📋 Using account: {active_account['accountDesc']} ({active_account['accountId']})")
    
    # Get computed account balance (E*TRADE balance API is broken)
    balance = {}
    try:
        balance = api.get_account_balance(account_key)
        print("✅ Balance information computed")
    except Exception as e:
        print(f"⚠️  Warning: Could not compute account balance: {e}")
        balance = {'error': str(e)}
    
    # Get portfolio positions
    positions_data = api.get_account_positions(account_key)
    print("✅ Portfolio positions retrieved")
    
    return active_account, balance, positions_data


def main():
    """Main application entry point."""
    parser = argparse.ArgumentParser(description='Generate E*TRADE Portfolio Report')
    parser.add_argument('--config', default='config.yml', help='Configuration file path')
    parser.add_argument('--account', help='Specific account ID to analyze')
    parser.add_argument('--no-color', action='store_true', help='Disable colored output')
    
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get API credentials
    client_key = os.getenv('ETRADE_CLIENT_KEY')
    client_secret = os.getenv('ETRADE_CLIENT_SECRET')
    sandbox = os.getenv('ETRADE_SANDBOX', 'true').lower() == 'true'
    
    if not client_key or not client_secret:
        print("ERROR: E*TRADE API credentials not found in .env file")
        print("Please copy .env.example to .env and update with your credentials")
        sys.exit(1)
    
    # Initialize components
    try:
        analyzer = PortfolioAnalyzer(args.config)
        formatter = ReportFormatter()
        
        # Set precision from config
        settings = analyzer.settings
        formatter.set_precision(
            settings.get('percentage_precision', 2),
            settings.get('dollar_precision', 2)
        )
        
    except Exception as e:
        print(f"ERROR: Failed to initialize: {str(e)}")
        sys.exit(1)
    
    # Initialize and authenticate E*TRADE API
    api = authenticate_etrade_api(client_key, client_secret, sandbox)
    
    # Get account data
    account_info, balance_info, positions_data = get_account_data(api)
    
    if account_info is None or positions_data is None:
        print("Failed to retrieve account data. Exiting.")
        sys.exit(1)
    
    print(f"🔍 DEBUG: positions_data keys: {list(positions_data.keys())}")
    
    # Extract and transform positions from the portfolio response
    raw_positions = []
    if 'AccountPortfolio' in positions_data:
        portfolio = positions_data['AccountPortfolio']
        positions_list = portfolio.get('Position', [])
        if not isinstance(positions_list, list):
            positions_list = [positions_list]
        raw_positions = positions_list
        print(f"🔍 DEBUG: Extracted {len(raw_positions)} raw positions")
    else:
        print(f"❌ DEBUG: No 'AccountPortfolio' key found. Keys: {list(positions_data.keys())}")
    
    # Transform E*TRADE positions to expected dictionary format
    positions = []
    for i, raw_pos in enumerate(raw_positions):
        try:
            transformed_pos = transform_etrade_position(raw_pos)
            positions.append(transformed_pos)
            print(f"✅ Transformed position {i+1}: {transformed_pos['symbol']} - ${transformed_pos['market_value']:.2f}")
        except Exception as e:
            print(f"❌ Error transforming position {i+1}: {e}")
            print(f"   Raw position keys: {list(raw_pos.keys())}")
    
    print(f"\nFound {len(positions)} positions")
    
    # Analyze portfolio
    try:
        print("🔍 Analyzing portfolio...")
        portfolio_positions = analyzer.assign_buckets_to_positions(positions)
        
        # Create AccountInfo object - use balance data or computed values
        total_portfolio_value = sum(pos['market_value'] for pos in positions)
        
        # Extract balance information 
        if balance_info and not balance_info.get('error'):
            # Use actual or computed balance data
            account_obj = AccountInfo(
                total_account_value=balance_info.get('total_account_value', total_portfolio_value),
                cash_available_for_investment=balance_info.get('cash_available_for_investment', 0.0),
                margin_buying_power=balance_info.get('margin_buying_power', 0.0),
                margin_balance=balance_info.get('margin_balance', 0.0),
                net_account_value=balance_info.get('net_account_value', total_portfolio_value)
            )
            
            if balance_info.get('computed'):
                print("ℹ️  Balance calculated from portfolio value and margin estimates")
        else:
            # Fallback to basic portfolio value
            account_obj = AccountInfo(
                total_account_value=total_portfolio_value,
                cash_available_for_investment=0.0,
                margin_buying_power=0.0,
                margin_balance=0.0,
                net_account_value=total_portfolio_value
            )
        
        print("🔍 Generating summary report...")
        report = analyzer.generate_summary_report(portfolio_positions, account_obj)
        
        print("🔍 Displaying report...")
        # Display report
        formatter.print_full_report(report)
        
        # Exit with error code if there are unassigned positions
        if report['unassigned_positions']:
            sys.exit(2)  # Exit code 2 indicates unassigned positions
            
    except Exception as e:
        print(f"ERROR: Failed to generate report: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()