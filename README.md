# E*TRADE Portfolio Report Generator

A Python application that generates comprehensive portfolio reports from E*TRADE accounts, categorizing holdings into configurable buckets and showing margin utilization.

## Features

- **Bucket Allocation**: Categorize your holdings into custom buckets (Growth, Income, Hedge, etc.)
- **Portfolio Analysis**: View allocation percentages, position details, and performance metrics
- **Margin Monitoring**: Track margin utilization and available cash
- **Configuration Management**: Easy-to-edit YAML configuration for bucket assignments
- **Unassigned Position Warnings**: Highlights positions that need bucket assignment
- **Colorized Output**: Easy-to-read terminal reports with color coding

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

### Basic Usage

```bash
python main.py
```

### Advanced Options

```bash
# Use custom config file
python main.py --config my_config.yml

# Analyze specific account
python main.py --account ACCOUNT_ID

# Disable colored output
python main.py --no-color
```

## Authentication Flow

The application uses OAuth 1.0a authentication with E*TRADE:

1. Run the script
2. Visit the authorization URL displayed
3. Log in to your E*TRADE account
4. Copy the verification code
5. Paste it into the terminal

## Report Sections

### 1. Portfolio Summary
- Total portfolio value
- Overall gain/loss
- Position count

### 2. Bucket Allocation
- Value and percentage for each bucket
- Position count per bucket
- Highlights unassigned positions in red

### 3. Margin & Cash Information
- Net account value
- Available cash for investment
- Margin buying power
- Margin utilization percentage

### 4. Unassigned Positions Warning
- Lists positions not assigned to any bucket
- Shows market value for each unassigned position
- Provides guidance for updating configuration

### 5. Bucket Details
- Detailed position information for each bucket
- Individual position performance
- Sorted by market value

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

## Exit Codes

- `0`: Success
- `1`: General error (authentication, API, configuration)
- `2`: Success but with unassigned positions (warning)

## Troubleshooting

### Authentication Issues
- Ensure your API credentials are correct
- Check if you're using sandbox vs production endpoints
- Verify your E*TRADE account has API access enabled

### Missing Positions
- Check the `min_position_value` setting in config.yml
- Ensure positions have positive quantities (short positions are excluded)

### Configuration Errors
- Validate YAML syntax in config.yml
- Ensure all required sections are present
- Check symbol formatting (should match E*TRADE symbols exactly)

## Security Notes

- Never commit your `.env` file to version control
- Keep your API credentials secure
- Use sandbox mode for testing
- Regularly rotate your API keys

## Sample Output

```
================================================================================
                               PORTFOLIO SUMMARY
================================================================================
Report Generated: 2025-09-29 14:30:15
Total Portfolio Value: $125,450.67
Total Positions: 15
Total Gain/Loss: +$8,245.32 (7.03%)

================================================================================
                              BUCKET ALLOCATION
================================================================================
┌─────────┬───────────┬──────────────┬──────────────┐
│ Bucket  │ Positions │ Value        │ Allocation % │
├─────────┼───────────┼──────────────┼──────────────┤
│ Growth  │ 8         │ $75,270.40   │ 60.00%       │
│ Income  │ 5         │ $37,635.20   │ 30.00%       │
│ Hedge   │ 2         │ $12,545.07   │ 10.00%       │
└─────────┴───────────┴──────────────┴──────────────┘
```

## License

This project is for educational and personal use. Please comply with E*TRADE's API terms of service.