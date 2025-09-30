#!/bin/bash

# E*TRADE Portfolio Dashboard Launcher
# This script starts the Streamlit dashboard for E*TRADE portfolio analysis

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting E*TRADE Portfolio Dashboard...${NC}"

# Check if we're in the right directory
if [[ ! -f "dashboard.py" ]]; then
    echo -e "${RED}❌ Error: dashboard.py not found. Please run this script from the project root directory.${NC}"
    exit 1
fi

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: Python 3 is not installed or not in PATH${NC}"
    exit 1
fi

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    echo -e "${RED}❌ Error: pip3 is not installed or not in PATH${NC}"
    exit 1
fi

# Check if we're in a virtual environment
if [[ -z "$VIRTUAL_ENV" ]]; then
    # Try to activate virtual environment if it exists
    if [[ -d "venv" ]]; then
        echo -e "${YELLOW}📦 Activating virtual environment (venv)...${NC}"
        source venv/bin/activate
    elif [[ -d ".venv" ]]; then
        echo -e "${YELLOW}📦 Activating virtual environment (.venv)...${NC}"
        source .venv/bin/activate
    elif [[ -d "env" ]]; then
        echo -e "${YELLOW}📦 Activating virtual environment (env)...${NC}"
        source env/bin/activate
    else
        echo -e "${RED}❌ Error: No virtual environment found and none is currently active.${NC}"
        echo -e "${YELLOW}💡 Please either:${NC}"
        echo -e "   1. Activate your virtual environment: ${GREEN}source venv/bin/activate${NC}"
        echo -e "   2. Create a new one: ${GREEN}python3 -m venv venv${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ Virtual environment already active: $VIRTUAL_ENV${NC}"
fi

# Check if streamlit is available in the current environment
echo -e "${YELLOW}📦 Checking dependencies...${NC}"
if ! python3 -c "import streamlit" 2>/dev/null; then
    echo -e "${RED}❌ Error: Streamlit not found in the current environment.${NC}"
    echo -e "${YELLOW}💡 Make sure you've installed the dependencies with:${NC}"
    echo -e "   ${GREEN}pip install -r requirements.txt${NC}"
    exit 1
fi

# Check if config.yml exists
if [[ ! -f "config.yml" ]]; then
    echo -e "${YELLOW}⚠️  Warning: config.yml not found. Make sure to configure your E*TRADE API credentials.${NC}"
fi

# Start the dashboard
echo -e "${GREEN}✅ Dependencies installed successfully!${NC}"
echo -e "${BLUE}🌐 Starting dashboard on http://localhost:8501${NC}"
echo -e "${YELLOW}💡 Press Ctrl+C to stop the dashboard${NC}"
echo ""

# Run streamlit with dashboard.py
streamlit run dashboard.py --server.port 8501 --server.address localhost

echo -e "${GREEN}👋 Dashboard stopped. Goodbye!${NC}"