#!/usr/bin/env python3
"""
Quick setup script for E*TRADE Portfolio Report Generator
"""

import os
import shutil
import subprocess
import sys


def check_python_version():
    """Check if Python version is adequate."""
    if sys.version_info < (3, 7):
        print("ERROR: Python 3.7 or higher is required")
        sys.exit(1)
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor} detected")


def setup_environment():
    """Set up the development environment."""
    print("Setting up E*TRADE Portfolio Report Generator...")
    
    # Check Python version
    check_python_version()
    
    # Create .env file from example if it doesn't exist
    if not os.path.exists('.env'):
        if os.path.exists('.env.example'):
            shutil.copy('.env.example', '.env')
            print("✓ Created .env file from template")
            print("  Please edit .env with your E*TRADE API credentials")
        else:
            print("⚠ No .env.example file found")
    else:
        print("✓ .env file already exists")
    
    # Install dependencies
    print("\nInstalling Python dependencies...")
    try:
        subprocess.run([sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'], 
                      check=True, capture_output=True, text=True)
        print("✓ Dependencies installed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to install dependencies: {e}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)
    
    # Check config file
    if not os.path.exists('config.yml'):
        print("⚠ No config.yml file found")
        print("  The default config.yml should be present")
    else:
        print("✓ Configuration file found")
    
    print("\n" + "="*50)
    print("Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env with your E*TRADE API credentials")
    print("2. Update config.yml with your portfolio positions")
    print("3. Run: python main.py")
    print("\nFor help: python main.py --help")


if __name__ == "__main__":
    setup_environment()