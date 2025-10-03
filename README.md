# E*TRADE Portfolio Dashboard

An interactive Streamlit dashboard for E*TRADE portfolios with real-time data visualization, bucket allocation analysis, and cash flow tracking.

## Features

- **Interactive Dashboard**: Real-time portfolio visualization with Streamlit
- **Bucket Allocation**: Categorize your holdings into custom buckets (Growth, Income, Hedge, etc.)
- **Portfolio Analysis**: View allocation percentages, position details, and performance metrics
- **Cash Flow History**: Visualize daily cash flow with interactive charts
- **Margin Monitoring**: Track margin utilization and available cash
- **Privacy Mode**: Redact sensitive values using upside-down Unicode numbers
- **Dividend Tracking**: Monitor dividend yields, payment dates, and annual income
- **Configuration Management**: Easy-to-edit YAML configuration for bucket assignments

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure E*TRADE API Credentials

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your E*TRADE API credentials:
   ```
   ETRADE_CLIENT_KEY=your_actual_client_key
   ETRADE_CLIENT_SECRET=your_actual_client_secret
   ETRADE_SANDBOX=true  # Set to false for production
   ```

### 3. Configure Portfolio Buckets

Edit `config.yml` to assign your positions to appropriate buckets:

```yaml
buckets:
  Growth:
    - AAPL
    - GOOGL
    - MSFT
    # Add your growth stocks here
  
  Income:
    - VTI
    - SCHD
    - JEPI
    # Add your income-generating assets here
  
  Hedge:
    - GLD
    - TLT
    # Add your hedging positions here
```

## Usage

### Run the Dashboard

```bash
streamlit run dashboard.py
```

The dashboard will open in your default browser at `http://localhost:8501`

### Dashboard Features

- **Auto-refresh**: Click "Refresh Data" to update with latest portfolio information
- **Privacy Mode**: Toggle "Redact Values" to hide sensitive account balances and quantities
- **Time Range Selector**: View cash flow history for 7, 14, 30, 60, or 90 days
- **Interactive Charts**: Hover over charts for detailed information
- **Bucket Views**: Positions organized by configured buckets with color-coded gains/losses

## Authentication Flow

The application uses OAuth 1.0a authentication with E*TRADE:

1. Run the dashboard
2. Browser automatically opens to E*TRADE authorization page
3. Log in to your E*TRADE account
4. Copy the verification code
5. Paste it into the terminal
6. Tokens are cached for up to 12 hours

## Dashboard Sections

### 1. Account Overview (Left Panel)
- Portfolio value with gain/loss
- Net equity with margin utilization
- Margin buying power
- Cash balances
- Annual dividend income

### 2. Portfolio Distribution (Center Panel)
- Interactive pie chart showing bucket allocation
- Percentages for each bucket
- Color-coded by bucket type

### 3. Cash Flow History (Right Panel)
- Daily cash flow bar chart
- Total inflow/outflow statistics
- Selectable time periods (7-90 days)
- Hover for transaction details

### 4. Position Tables (Bottom)
- Positions organized by bucket
- Market value, quantity, current price
- Gain/loss with color coding (green/red)
- Dividend information (yield, annual dividend, pay dates)
- Upcoming dividend alerts (🟠 for ex-div, 💲 for pay date)
- Searchable and sortable

## Configuration Options

The `config.yml` file supports the following settings:

```yaml
settings:
  # Minimum position value to include in report (USD)
  min_position_value: 100
  
  # Display precision
  percentage_precision: 2
  dollar_precision: 2
```

## Troubleshooting

### Authentication Issues
- Ensure your API credentials are correct in `.env`
- Browser should auto-open; if not, copy/paste the URL manually
- Tokens are cached for up to 12 hours
- If tokens expire, dashboard will prompt for re-authentication

### Dashboard Won't Load
- Ensure Streamlit is installed: `pip install streamlit`
- Check if port 8501 is available
- Try running: `streamlit run dashboard.py --server.port 8502`

### Missing Positions
- Check the `min_position_value` setting in config.yml
- Verify positions have positive quantities

### Configuration Errors
- Validate YAML syntax in config.yml
- Ensure all required sections are present
- Check symbol formatting (should match E*TRADE symbols exactly)

## Security Notes

- Never commit your `.env` file to version control
- Keep your API credentials secure
- Use privacy mode when sharing screenshots
- Token cache (`.etrade_tokens.json`) should also be excluded from version control
- Use sandbox mode for testing

## License

This project is for educational and personal use. Please comply with E*TRADE's API terms of service.