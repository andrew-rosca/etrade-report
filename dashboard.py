#!/usr/bin/env python3
"""
Run with: streamlit run dashboard.py

Features:
- Real-time portfolio overview
- Interactive bucket allocation charts
- Margin analysis and cash flow
- Detailed position tables with filtering
- Performance metrics and trends
- Privacy mode with value redaction
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
    .metric-value {
        font-size: 1.5rem !important;
        font-weight: bold !important;
    }
    div[data-testid="metric-container"] > label {
        font-size: 0.9rem !important;
        color: #888 !important;
    }
    .stDataFrame {
        font-size: 0.85rem !important;
    }
    .block-container {
        padding-top: 3rem !important;
    }
</style>
""", unsafe_allow_html=True)

# Load environment variables
load_dotenv()

redaction_text = "\\*\\*\\*"

# Redaction helper functions
def redact_value(value, format_str="${:,.0f}", redacted_text=redaction_text):
    """Redact a monetary value or quantity if redaction is enabled"""
    if st.session_state.get('redact_toggle', False):
        # Use simple text that won't interfere with HTML
        return redaction_text
    else:
        return format_str.format(value)

def redact_quantity(quantity):
    """Redact quantity values"""
    if st.session_state.get('redact_toggle', False):
        return redaction_text
    else:
        return f"{quantity:.1f}"

@st.cache_data(ttl=30)  # Cache for 30 seconds
def load_portfolio_data():
    """Load portfolio data from E*TRADE API."""
    try:
        # Get credentials from environment
        client_key = os.getenv('ETRADE_CLIENT_KEY')
        client_secret = os.getenv('ETRADE_CLIENT_SECRET')
        
        if not client_key or not client_secret:
            st.error("❌ E*TRADE credentials not found. Please check your environment variables.")
            return None, None, None
        
        # Initialize API
        api = ETradeSimpleAPI(client_key, client_secret, use_sandbox=False)
        
        # Authenticate with E*TRADE API
        if not api.authenticate():
            st.error("❌ Failed to authenticate with E*TRADE API. Please check your credentials and try refreshing.")
            return None, None, None
        
        # Get account list
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
    """Create bucket analysis from portfolio data."""
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
    
    # Sidebar for settings and controls
    with st.sidebar:               
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

        if st.button("Refresh Data", type="primary"):
            st.cache_data.clear()
            st.rerun()
        
        st.markdown("---")

        # Redaction toggle
        redact_values = st.toggle(
            "Redact Values", 
            key="redact_toggle",
            help="Hide account balances, market values, and quantities for privacy. Prices and percentages remain visible."
        )        
        
        if redact_values:
            st.info("**Privacy Mode Active**\n\nHidden: Account balances, market values, quantities\n\nVisible: Prices, percentages, symbols")


    
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
        
        st.markdown(f"<span style='color:#888'>Portfolio Value:</span> <strong>{redact_value(net_market_value)}</strong> (<span style='color:{gain_color}; font-weight:bold'>{redact_value(total_gain_loss, '{:+,.0f}')}, {total_gain_loss_pct:+.1f}%</span>)", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#888'>Equity:</span> <strong>{redact_value(net_account_value)}</strong> (<span style='color:{margin_color}; font-weight:bold'>{margin_utilization:.1f}%</span>)", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#888'>Margin Buying Power:</span> <strong>{redact_value(margin_buying_power)}</strong>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#888'>Cash Available:</span> <strong>{redact_value(cash_available)}</strong>", unsafe_allow_html=True)
        st.markdown(f"<span style='color:#888'>Margin Balance:</span> <strong>{redact_value(margin_balance)}</strong>", unsafe_allow_html=True)
    
    # Right pane - Portfolio Distribution (pie chart only)
    with col2:
        
        # Portfolio allocation pie chart
        bucket_names = []
        bucket_values = []
        bucket_colors = []
        color_map = {"Growth": "#1E90FF", "Core Growth": "#4169E1", "Income": "#2E8B57", "Hedge": "#FF8C00", "Unassigned": "#708090"}
        
        for bucket_name, bucket_info in buckets.items():
            if bucket_info['total_value'] > 0:
                bucket_names.append(bucket_name)
                # For pie chart, we can show relative percentages even in redaction mode
                # since percentages don't reveal absolute values
                bucket_values.append(bucket_info['total_value'])
                bucket_colors.append(color_map.get(bucket_name, "#708090"))
        
        # In redaction mode, show only percentages, not values
        textinfo = 'label+percent' if st.session_state.get('redact_toggle', False) else 'label+percent'
        
        fig_pie = go.Figure(data=[go.Pie(
            labels=bucket_names,
            values=bucket_values,
            hole=0.3,
            marker=dict(colors=bucket_colors),
            textinfo=textinfo,
            textfont=dict(size=11),
            hovertemplate='<b>%{label}</b><br>%{percent}<extra></extra>' if st.session_state.get('redact_toggle', False) else '<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>'
        )])
        
        fig_pie.update_layout(
            height=200,
            margin=dict(l=0, r=0, t=0, b=0),
            showlegend=False
        )
        
        # Use config parameter to avoid deprecation warning
        st.plotly_chart(fig_pie, config={'displayModeBar': False})
    
    # Bottom pane - Positions organized by buckets
    search_term = st.text_input("Search positions", placeholder="Search positions...", label_visibility="collapsed")
    
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
    bucket_order = ['Core Growth', 'Growth', 'Income', 'Unassigned', 'Hedge']
    
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
        st.markdown(f"<span style='color:#888'>{bucket_name}:</span> <strong>{redact_value(bucket_total)}</strong> (<span style='color:{gain_color}; font-weight:bold'>{redact_value(bucket_gain_loss, '{:+,.0f}')}</span>)", unsafe_allow_html=True)
        
        # Create dataframe for this bucket
        bucket_df = pd.DataFrame([
            {
                'Symbol': pos['symbol'],
                'Market Value': pos['market_value'],
                'Quantity': pos['quantity'],
                'Price': pos['current_price'],
                'Gain/Loss': pos['gain_loss'],
                'G/L %': pos['gain_loss_pct']
            }
            for pos in sorted(filtered_positions, key=lambda x: x['market_value'], reverse=True)
        ])
        
        # Apply redaction to sensitive columns
        if st.session_state.get('redact_toggle', False):
            bucket_df['Market Value'] = bucket_df['Market Value'].apply(lambda x: "***")
            bucket_df['Quantity'] = bucket_df['Quantity'].apply(lambda x: "***")
            bucket_df['Gain/Loss'] = bucket_df['Gain/Loss'].apply(lambda x: "***")
        
        # Style and format the dataframe
        styled_df = bucket_df.style.map(style_gain_loss, subset=['Gain/Loss', 'G/L %'])
        
        # Format based on redaction state
        if st.session_state.get('redact_toggle', False):
            styled_df = styled_df.format({
                'Price': '${:.2f}',
                'G/L %': '{:+.1f}%'
                # Market Value, Quantity, and Gain/Loss are already redacted above
            })
        else:
            styled_df = styled_df.format({
                'Price': '${:.2f}',
                'Market Value': '${:,.0f}',
                'Gain/Loss': '${:,.0f}',
                'G/L %': '{:+.1f}%',
                'Quantity': '{:.1f}'
            })
        
        st.dataframe(styled_df, width='stretch', hide_index=True)
        st.markdown("")  # Add some spacing between buckets

if __name__ == "__main__":
    main()