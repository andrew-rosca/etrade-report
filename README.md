# E*TRADE Portfolio Dashboard

An interactive Streamlit dashboard for E*TRADE portfolios with real-time data visualization, bucket allocation analysis, and cash flow tracking.

<img width="2274" height="1814" alt="image" src="https://github.com/user-attachments/assets/9dd5f937-2187-4c2c-833b-b0bdbe4abe54" />


## Features

- **Interactive Dashboard**: Real-time portfolio visualization with Streamlit
- **Bucket Allocation**: Categorize your holdings into custom buckets (Growth, Income, Hedge, etc.)
- **Portfolio Analysis**: View allocation percentages, position details, and performance metrics
- **Concentration Analysis**: Track exposure to underlying assets through direct and indirect holdings
- **Cash Flow History**: Visualize daily cash flow with interactive charts
- **Margin Monitoring**: Track margin utilization and available cash
- **Privacy Mode**: Redact sensitive values
- **Dividend Tracking**: Monitor dividend yields, payment dates, and annual income
- **Configuration Management**: Easy-to-edit YAML configuration for bucket assignments

## Prerequisites

Before setting up the dashboard, you'll need:

### 1. Python 3.8 or higher

Check if Python is installed by opening a terminal/command prompt and running:

```bash
python3 --version
```

If Python is not installed, download it from [python.org](https://www.python.org/downloads/)

### 2. E*TRADE API Keys

You need API credentials from E*TRADE to access your portfolio data.

**To get your API keys:**

1. Visit [E*TRADE Developer Portal](https://developer.etrade.com/home)
2. Log in with your E*TRADE credentials
3. Click "Get API Keys" or navigate to "My Keys"
4. Create a new application:
   - **Application Name**: Choose any name (e.g., "Portfolio Dashboard")
   - **Description**: Brief description of your use case
5. You'll receive two sets of keys:
   - **Sandbox Keys**: For testing with fake data (recommended for first-time setup)
   - **Production Keys**: For accessing your real portfolio data

**Important distinctions:**
- **Sandbox Mode**: Uses test data, won't show your real portfolio. Good for learning and testing.
- **Production Mode**: Accesses your actual E*TRADE account data. Use this for real portfolio tracking.

**Note**: Keep your API keys secure and never share them publicly.

## Setup

### Step 1: Clone or Download this Repository

Download the project files to your computer.

### Step 2: (Recommended) Create a Virtual Environment

A virtual environment keeps this project's dependencies separate from other Python projects on your computer.

**On macOS/Linux:**
```bash
cd etrade-report
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**
```bash
cd etrade-report
python -m venv venv
venv\Scripts\activate
```

You'll know the virtual environment is active when you see `(venv)` in your terminal prompt.

### Step 3: Install Dependencies

With your virtual environment activated, install the required Python packages:

```bash
pip install -r requirements.txt
```

This will install Streamlit, Plotly, and other necessary libraries.

### Step 4: Configure E*TRADE API Credentials

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Open `.env` in a text editor and add your E*TRADE API credentials:
   ```
   ETRADE_CLIENT_KEY=your_actual_client_key_here
   ETRADE_CLIENT_SECRET=your_actual_client_secret_here
   ETRADE_SANDBOX=false
   ```

   **Configuration notes:**
   - Replace `your_actual_client_key_here` with your actual API key
   - Replace `your_actual_client_secret_here` with your actual API secret
   - Set `ETRADE_SANDBOX=true` to use sandbox mode (test data)
   - Set `ETRADE_SANDBOX=false` to use production mode (real portfolio data)

### Step 5: Configure Portfolio Buckets

Edit `config.yml` in a text editor to organize your positions into categories (buckets):

```yaml
buckets:
  Core Growth:
    - AAPL
    - GOOGL
    - MSFT
    # Add your core growth stocks here

  Growth:
    - NVDA
    - TSLA
    # Add your growth stocks here

  Income:
    - VTI
    - SCHD
    - JEPI
    # Add your income-generating assets here

  Hedge:
    - SPY*     # Matches SPY and SPY options
    - QQQ*     # Matches QQQ and QQQ options
    # Add your hedging positions here
```

**Tips:**
- Add the ticker symbols from your portfolio to the appropriate buckets
- Use `*` as a wildcard (e.g., `SPY*` matches SPY stock and all SPY options)
- You can create custom bucket names that fit your investment strategy
- Positions not listed will appear in the "Unassigned" bucket

## Usage

### Quick Start (Recommended)

Run the included shell script to start the dashboard:

**On macOS/Linux:**
```bash
./dashboard.sh
```

**On Windows (using Git Bash or WSL):**
```bash
bash dashboard.sh
```

The script will:
- Automatically activate your virtual environment if found
- Check that all dependencies are installed
- Start the dashboard on `http://localhost:8501`
- Open your browser automatically

### Alternative Method

You can also run the dashboard directly with Streamlit:

```bash
streamlit run dashboard.py
```

The dashboard will open in your default browser at `http://localhost:8501`

**To stop the dashboard:** Press `Ctrl+C` in the terminal

### First-Time Authentication

When you first run the dashboard, you'll need to authenticate with E*TRADE:

1. The dashboard will start and your browser will automatically open to the E*TRADE authorization page
2. Log in with your E*TRADE username and password
3. E*TRADE will display a verification code (usually 5 characters)
4. Copy this code
5. Go back to your terminal and paste the verification code when prompted
6. Press Enter

**Good news:** Your authentication tokens are cached for up to 12 hours, so you won't need to do this every time!

### Dashboard Features

Once logged in, you'll see:

- **Auto-refresh**: Click "Refresh Data" in the sidebar to update with latest portfolio information
- **Privacy Mode**: Toggle "Redact Values" to hide sensitive account balances and quantities (useful for screenshots)
- **Time Range Selector**: View cash flow history for 7, 14, 30, 60, or 90 days
- **Interactive Charts**: Hover over any chart for detailed information
- **Bucket Views**: Your positions organized by the buckets you configured, with color-coded gains/losses

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

### 5. Concentration Analysis (Bottom)
- Top N most concentrated exposures in your portfolio
- Aggregates direct and indirect holdings to underlying assets
- Shows exposure chains (e.g., MSTY → MSTR → Bitcoin)
- Supports proportional exposure (e.g., SPYG holds 14% NVDA)
- Color-coded warnings for high concentration risk
- Expandable view showing full exposure mappings

## Configuration Options

The `config.yml` file supports the following settings:

```yaml
settings:
  # Minimum position value to include in report (USD)
  min_position_value: 100
  
  # Display precision
  percentage_precision: 2
  dollar_precision: 2
  
  # Number of top concentrations to display
  top_concentrations: 10
```

### Concentration Analysis Configuration

The concentration analysis feature helps you understand your portfolio's exposure to underlying assets, even through indirect holdings like ETFs. Configure exposure mappings in `config.yml`:

```yaml
exposure_mappings:
  SYMBOL: UNDERLYING              # 1:1 exposure (default)
  SYMBOL: UNDERLYING*factor       # Proportional exposure
  SYMBOL:                         # Multiple exposures (list)
    - UNDERLYING1*factor1
    - UNDERLYING2*factor2
```

**Examples:**

1. **Direct Exposure (1:1)** - Symbol tracks underlying 1:1
   ```yaml
   MSTY: MSTR              # MSTY has full exposure to MSTR
   NVDY: NVDA              # NVDY tracks NVDA 1:1
   MSTR: Bitcoin           # MSTR tracks Bitcoin
   ```

2. **Proportional Exposure** - Use `*factor` notation
   ```yaml
   BRK.B: AAPL*0.22       # Berkshire holds 22% Apple
   CRF: AAPL*0.0695       # CEF holds 6.95% Apple
   ```

3. **Multiple Exposures** - ETFs with multiple top holdings
   ```yaml
   SPYG:                  # S&P 500 Growth ETF
     - NVDA*0.1469        # 14.69% NVIDIA
     - MSFT*0.0636        # 6.36% Microsoft
     - AAPL*0.0560        # 5.60% Apple
     - AVGO*0.0507        # 5.07% Broadcom
     # ... add more holdings
   ```

4. **Chained Exposure** - Automatically resolves through multiple levels
   ```yaml
   MSTY: MSTR             # MSTY tracks MSTR
   MSTR: Bitcoin          # MSTR tracks Bitcoin
   # Result: MSTY → MSTR → Bitcoin (auto-calculated)
   ```

5. **Aggregated Exposure** - Multiple instruments to same underlying
   ```yaml
   MSTR: Bitcoin
   BTCI: Bitcoin
   XBTY: Bitcoin
   # All Bitcoin exposure is aggregated together
   ```

**How It Works:**

- The analyzer recursively resolves exposure chains
- Factors are multiplied along the chain (e.g., 3x leverage × 8% holding = 24% exposure)
- All exposures to the same underlying asset are summed
- Top N concentrations are displayed with color-coded risk warnings

**Concentration Risk Levels:**
- 🔴 **High Risk** (≥15%): Red text - consider diversification
- 🟡 **Moderate** (10-15%): Yellow text - monitor closely
- ⚪ **Normal** (<10%): Standard text

**Testing Your Configuration:**

After adding exposure mappings, test them with:
```bash
python test_concentration.py
```

This will show you:
- Calculated concentrations for sample positions
- Exposure chains for each mapped symbol
- Whether your mappings are working correctly

## Troubleshooting

### "Python not found" Error

If you get a "command not found" error when running `python3`:
- **macOS/Linux**: Try `python` instead of `python3`
- **Windows**: Use `python` instead of `python3`
- Make sure Python is installed and added to your system PATH

### Virtual Environment Issues

**Virtual environment won't activate:**
- **macOS/Linux**: Make sure you're using `source venv/bin/activate`
- **Windows**: Use `venv\Scripts\activate` (not `source`)
- **Windows PowerShell**: You may need to run `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser` first

**"No virtual environment found" when running dashboard.sh:**
- Create a virtual environment first: `python3 -m venv venv`
- Or skip the virtual environment requirement by editing `dashboard.sh`

### Authentication Issues

**"Failed to authenticate" error:**
- Double-check your API credentials in `.env` are correct (no extra spaces)
- Make sure you're using the right keys (sandbox vs production)
- Verify your E*TRADE account has API access enabled

**Browser doesn't open automatically:**
- The URL will still be printed in the terminal
- Copy and paste it into your browser manually

**Tokens expired:**
- Simply re-run the dashboard - it will automatically prompt for re-authentication
- Token expiration is normal after several hours of inactivity

### Dashboard Won't Load

**"Streamlit not found" error:**
- Make sure you've installed dependencies: `pip install -r requirements.txt`
- Verify your virtual environment is activated (look for `(venv)` in terminal)

**Port 8501 already in use:**
- Another instance might be running - close it first
- Or use a different port: `streamlit run dashboard.py --server.port 8502`

### Missing or Incorrect Data

**Some positions are missing:**
- Check the `min_position_value` setting in `config.yml` - positions below this value are hidden
- Verify positions have positive quantities (short positions may not show)

**"Unassigned" bucket shows positions:**
- This is normal! Add those ticker symbols to your `config.yml` under the appropriate bucket
- Use the ticker symbol exactly as it appears in E*TRADE

### Configuration Errors

**"Error loading config.yml":**
- Check YAML syntax - indentation matters! Use spaces, not tabs
- Make sure all bucket names and symbols are properly formatted
- Ensure the file is saved as `config.yml` (not `.txt`)

## Security Notes

- Never commit your `.env` file to version control
- Keep your API credentials secure
- Use privacy mode when sharing screenshots
- Token cache (`.etrade_tokens.json`) should also be excluded from version control
- Use sandbox mode for testing

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

**Note**: This project is for educational and personal use. Please comply with E*TRADE's API terms of service when using their API.
