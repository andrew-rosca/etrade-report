#!/usr/bin/env python3
"""
E*TRADE Portfolio Streamlit Dashboard

A beautiful, interactive web dashboard for E*TRADE portfolio analysis.
Run with: streamlit run streamlit_dashboard.py

Fea    # Top refresh controls
    col_refresh, col_time = st.columns([1, 4])
    with col_refresh:
        if st.button("Refresh", type="primary"):
            st.cache_data.clear()
            st.rerun()
    with col_time:
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")eal-time portfolio overview
- Interactive bucket allocation charts
- Margin analysis and cash flow
- Detailed position tables with filtering
- Performance metrics and trends
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime
import os
from dotenv import load_dotenv

# Import our E*TRADE modules
from etrade_simple_api import ETradeSimpleAPI
from portfolio_analyzer import PortfolioAnalyzer, PortfolioPosition
from main import transform_etrade_position

# Configure Streamlit page
st.set_page_config(
    page_title="E*TRADE Portfolio Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for cleaner styling
st.markdown("""
<style>
    h1, h2, h3 {
        font-size: 1.1rem !important;
        margin-bottom: 0.5rem !important;
    }
    .stMarkdown p {
        font-size: 0.9rem;
    }
    .stText {
        font-size: 0.9rem !important;
        line-height: 1.4 !important;
        margin-bottom: 0.2rem !important;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache for 5 minutes
def load_portfolio_data():
    """Load portfolio data from E*TRADE API with caching."""
    try:
        # Load environment variables
        load_dotenv()
        client_key = os.getenv('ETRADE_CLIENT_KEY')
        client_secret = os.getenv('ETRADE_CLIENT_SECRET')
        
        if not client_key or not client_secret:
            st.error("❌ E*TRADE API credentials not found in .env file")
            return None, None, None
        
        # Initialize API
        api = ETradeSimpleAPI(client_key, client_secret)
        
        # Try to use cached tokens first
        if not api.authenticate():
            st.warning("⚠️ Could not authenticate with E*TRADE API. Using sample data for demonstration.")
            # Return sample data for demonstration
            sample_portfolio = [
                {'symbol': 'AAPL', 'description': 'Apple Inc', 'quantity': 100, 'current_price': 175.25, 'market_value': 17525.00, 'gain_loss': 825.00, 'gain_loss_pct': 4.94},
                {'symbol': 'MSFT', 'description': 'Microsoft Corp', 'quantity': 75, 'current_price': 285.30, 'market_value': 21397.50, 'gain_loss': -234.50, 'gain_loss_pct': -1.08},
                {'symbol': 'SPY', 'description': 'SPDR S&P 500 ETF', 'quantity': 200, 'current_price': 412.85, 'market_value': 82570.00, 'gain_loss': 670.00, 'gain_loss_pct': 0.82},
                {'symbol': 'QQQ', 'description': 'Invesco QQQ Trust', 'quantity': 150, 'current_price': 356.42, 'market_value': 53463.00, 'gain_loss': 1200.00, 'gain_loss_pct': 2.30},
                {'symbol': 'SPY Oct 17 \'25 $600 Put', 'description': 'SPY Put Option', 'quantity': 1, 'current_price': 0.46, 'market_value': 46.50, 'gain_loss': -39.17, 'gain_loss_pct': -45.72}
            ]
            sample_balance = {
                'RealTimeValues': {'totalAccountValue': 175000.00},
                'totalAvailableForWithdrawal': 15000.00,
                'marginBuyingPower': 30000.00,
                'accountBalance': -25000.00
            }
            sample_account = {'accountDesc': 'Sample Brokerage Account', 'accountId': 'DEMO123456'}
            return sample_portfolio, sample_balance, sample_account
        
        # Get account data
        accounts = api.get_account_list()
        if not accounts or 'Accounts' not in accounts:
            st.error("❌ Failed to retrieve account list")
            return None, None, None
        
        # Find active margin account
        account_list = accounts['Accounts']['Account']
        if not isinstance(account_list, list):
            account_list = [account_list]
        
        active_account = None
        for account in account_list:
            if account.get('accountStatus') == 'ACTIVE' and account.get('accountMode') == 'MARGIN':
                active_account = account
                break
        
        if not active_account:
            for account in account_list:
                if account.get('accountStatus') == 'ACTIVE':
                    active_account = account
                    break
        
        if not active_account:
            st.error("❌ No active accounts found")
            return None, None, None
        
        account_key = active_account['accountIdKey']
        
        # Get balance and positions
        account_balance = api.get_account_balance(account_key)
        positions_data = api.get_account_positions(account_key)
        
        # Transform positions
        portfolio_data = []
        if 'AccountPortfolio' in positions_data:
            portfolio = positions_data['AccountPortfolio']
            positions_list = portfolio.get('Position', [])
            if not isinstance(positions_list, list):
                positions_list = [positions_list]
            
            for etrade_position in positions_list:
                transformed_position = transform_etrade_position(etrade_position)
                if transformed_position:
                    portfolio_data.append(transformed_position)
        
        return portfolio_data, account_balance, active_account
        
    except Exception as e:
        st.error(f"❌ Error loading portfolio data: {e}")
        return None, None, None

def create_bucket_analysis(portfolio_data):
    """Analyze portfolio into buckets and return data for visualization."""
    analyzer = PortfolioAnalyzer()
    
    # Convert to PortfolioPosition objects
    positions = []
    for pos_data in portfolio_data:
        bucket = analyzer._find_bucket_for_symbol(pos_data['symbol'], pos_data['description'])
        position = PortfolioPosition(
            symbol=pos_data['symbol'],
            description=pos_data['description'],
            quantity=pos_data['quantity'],
            current_price=pos_data['current_price'],
            market_value=pos_data['market_value'],
            gain_loss=pos_data['gain_loss'],
            gain_loss_pct=pos_data['gain_loss_pct'],
            bucket=bucket
        )
        positions.append(position)
    
    # Get bucket allocations
    buckets = analyzer.calculate_bucket_allocations(positions)
    
    return buckets, positions

def main():
    """Main Streamlit application."""
    

    
    # Simple refresh button in sidebar
    with st.sidebar:
        st.header("� Controls")
        if st.button("Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Load data
    with st.spinner("🔄 Loading portfolio data..."):
        portfolio_data, balance_info, account_info = load_portfolio_data()
    
    if portfolio_data is None:
        st.stop()
    
    if not portfolio_data:
        st.warning("⚠️ No portfolio positions found")
        st.stop()
    
    # Calculate summary metrics
    total_value = sum(pos['market_value'] for pos in portfolio_data)
    total_gain_loss = sum(pos['gain_loss'] for pos in portfolio_data)
    total_gain_loss_pct = (total_gain_loss / (total_value - total_gain_loss) * 100) if (total_value - total_gain_loss) != 0 else 0
    
    # Account info - extract from correct E*TRADE nested structure
    if balance_info:
        # Data is nested under "Computed"
        computed = balance_info.get('Computed', {})
        real_time_values = computed.get('RealTimeValues', {})
        
        # Extract values from correct locations
        net_market_value = float(real_time_values.get('netMv', 0))  # Portfolio value from RealTimeValues
        net_account_value = float(computed.get('regtEquity', 0))  # Net account equity from Computed
        margin_buying_power = float(computed.get('marginBuyingPower', 0))  # From Computed
        cash_buying_power = float(computed.get('cashBuyingPower', 0))  # From Computed
        margin_balance = float(computed.get('marginBalance', 0))  # From Computed
        cash_available = float(computed.get('totalAvailableForWithdrawal', 0))  # From Computed
    else:
        net_market_value = net_account_value = margin_buying_power = cash_buying_power = margin_balance = cash_available = 0
    
    # Calculate margin utilization
    margin_utilization = 0
    if net_account_value > 0 and margin_balance < 0:
        margin_utilization = (abs(margin_balance) / net_account_value) * 100
    

    
    # Analyze buckets
    buckets, positions = create_bucket_analysis(portfolio_data)
    
    # Simple 3-pane layout: Balances | Portfolio Distribution
    #                           Positions (full width)
    
    # Top row - two panes side by side
    col1, col2 = st.columns(2)
    
    # Left pane - All Financial Information
    with col1:
        # Color code the gain/loss and dim the labels
        gain_color = "green" if total_gain_loss >= 0 else "red"
        
        # Color code margin utilization: >55% green, 50-55% yellow, <50% red
        if margin_utilization > 55:
            margin_color = "green"
        elif margin_utilization >= 50:
            margin_color = "orange"  # Using orange for better visibility than yellow
        else:
            margin_color = "red"
        
        st.markdown(f"<span style='color:#888'>Portfolio Value:</span> <strong>${net_market_value:,.0f}</strong> (<span style='color:{gain_color}; font-weight:bold'>{total_gain_loss:+,.0f}, {total_gain_loss_pct:+.1f}%</span>)", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#888'>Net Account Value:</span> <strong>${net_account_value:,.0f}</strong> (<span style='color:{margin_color}; font-weight:bold'>{margin_utilization:.1f}%</span>)", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#888'>Margin Buying Power:</span> <strong>${margin_buying_power:,.0f}</strong>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#888'>Cash Available:</span> <strong>${cash_available:,.0f}</strong>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#888'>Margin Balance:</span> <strong>${margin_balance:,.0f}</strong>", unsafe_allow_html=True)
    
    # Right pane - Portfolio Distribution (pie chart only)
    with col2:
        
        # Portfolio allocation pie chart
        bucket_names = []
        bucket_values = []
        bucket_colors = []
        color_map = {"Growth": "#2E8B57", "Income": "#4169E1", "Hedge": "#FF8C00", "Unassigned": "#708090"}
        
        for bucket_name, bucket_info in buckets.items():
            if bucket_info['total_value'] > 0:
                bucket_names.append(bucket_name)
                bucket_values.append(bucket_info['total_value'])
                bucket_colors.append(color_map.get(bucket_name, "#708090"))
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=bucket_names,
            values=bucket_values,
            hole=0.3,
            marker_colors=bucket_colors,
            textinfo='label+percent',
            textfont_size=11
        )])
        
        fig_pie.update_layout(
            height=200,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False
        )
        
        # Use config parameter to avoid deprecation warning
        config = {'displayModeBar': False}
        st.plotly_chart(fig_pie, use_container_width=True, config=config)
    
    # Bottom pane - Positions organized by buckets
    search_term = st.text_input("Search positions", placeholder="Enter symbol...", label_visibility="collapsed")
    
    # Create analyzer and organize positions by bucket
    analyzer = PortfolioAnalyzer()
    
    # Group positions by bucket
    bucket_positions = {}
    for pos in portfolio_data:
        bucket = analyzer._find_bucket_for_symbol(pos['symbol'], pos['description'])
        if bucket not in bucket_positions:
            bucket_positions[bucket] = []
        bucket_positions[bucket].append(pos)
    
    # Style function for gain/loss
    def style_gain_loss(val):
        if isinstance(val, (int, float)):
            return 'color: green; font-weight: bold' if val >= 0 else 'color: red; font-weight: bold'
        return ''
    
    # Define bucket display order (Hedge last)
    bucket_order = ['Growth', 'Income', 'Unassigned', 'Hedge']
    
    # Sort buckets by the defined order
    sorted_buckets = []
    for bucket_name in bucket_order:
        if bucket_name in bucket_positions:
            sorted_buckets.append((bucket_name, bucket_positions[bucket_name]))
    
    # Add any other buckets not in the predefined order
    for bucket_name, positions in bucket_positions.items():
        if bucket_name not in bucket_order:
            sorted_buckets.append((bucket_name, positions))
    
    # Display each bucket in order
    for bucket_name, positions in sorted_buckets:
        if not positions:
            continue
            
        # Filter positions if search term is provided
        filtered_positions = positions
        if search_term:
            filtered_positions = [pos for pos in positions 
                                if search_term.lower() in pos['symbol'].lower() or 
                                   search_term.lower() in pos['description'].lower()]
        
        if not filtered_positions:
            continue
            
        # Calculate bucket totals
        bucket_total = sum(pos['market_value'] for pos in filtered_positions)
        bucket_gain_loss = sum(pos['gain_loss'] for pos in filtered_positions)
        
        # Bucket header with totals
        gain_color = "green" if bucket_gain_loss >= 0 else "red"
        st.markdown(f"<span style='color:#888'>{bucket_name}:</span> <strong>${bucket_total:,.0f}</strong> (<span style='color:{gain_color}; font-weight:bold'>{bucket_gain_loss:+,.0f}</span>)", unsafe_allow_html=True)
        
        # Create dataframe for this bucket
        bucket_df = pd.DataFrame([
            {
                'Symbol': pos['symbol'],
                'Quantity': pos['quantity'],
                'Price': pos['current_price'],
                'Market Value': pos['market_value'],
                'Gain/Loss': pos['gain_loss'],
                'G/L %': pos['gain_loss_pct']
            }
            for pos in sorted(filtered_positions, key=lambda x: x['market_value'], reverse=True)
        ])
        
        # Style and format the dataframe
        styled_df = bucket_df.style.map(style_gain_loss, subset=['Gain/Loss', 'G/L %'])
        styled_df = styled_df.format({
            'Price': '${:.2f}',
            'Market Value': '${:,.0f}',
            'Gain/Loss': '${:,.0f}',
            'G/L %': '{:+.1f}%',
            'Quantity': '{:.1f}'
        })
        
        st.dataframe(styled_df, use_container_width=True, hide_index=True)
        st.markdown("")  # Add some spacing between buckets

if __name__ == "__main__":
    main()