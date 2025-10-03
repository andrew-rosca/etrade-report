#!/usr/bin/env python3
"""
Test script for Concentration Analyzer

This script validates your concentration analysis configuration with sample data.
Run this after configuring exposure_mappings in config.yml to verify your setup.

Usage:
    python test_concentration.py

The output will show:
- Calculated concentrations for sample positions
- Exposure chains showing how positions map to underlying assets
- Whether your configuration is working correctly
"""

import yaml
from concentration_analyzer import ConcentrationAnalyzer


def test_concentration_analyzer():
    """Test the concentration analyzer with sample positions."""
    
    # Load config
    with open('config.yml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Create analyzer
    analyzer = ConcentrationAnalyzer(config)
    
    # Sample portfolio positions
    sample_positions = [
        {
            'symbol': 'MSTY',
            'market_value': 10000,
            'quantity': 100,
            'current_price': 100
        },
        {
            'symbol': 'MSTR',
            'market_value': 15000,
            'quantity': 50,
            'current_price': 300
        },
        {
            'symbol': 'BTCI',
            'market_value': 5000,
            'quantity': 200,
            'current_price': 25
        },
        {
            'symbol': 'SPYG',
            'market_value': 20000,
            'quantity': 100,
            'current_price': 200
        },
        {
            'symbol': 'NVDA',
            'market_value': 8000,
            'quantity': 50,
            'current_price': 160
        },
        {
            'symbol': 'AAPL',
            'market_value': 12000,
            'quantity': 60,
            'current_price': 200
        }
    ]
    
    # Calculate concentrations
    print("=" * 80)
    print("PORTFOLIO CONCENTRATION ANALYSIS")
    print("=" * 80)
    print()
    
    total_value = sum(p['market_value'] for p in sample_positions)
    print(f"Total Portfolio Value: ${total_value:,.0f}")
    print()
    
    concentrations = analyzer.calculate_concentrations(sample_positions, top_n=10)
    
    print(f"{'Rank':<6} {'Underlying Asset':<20} {'Exposure':<15} {'% Portfolio':<12} {'Via Positions'}")
    print("-" * 80)
    
    for i, item in enumerate(concentrations, 1):
        symbols = sorted(
            set(pos['symbol'] for pos in item.contributing_positions),
            key=lambda s: sum(p['exposure_value'] for p in item.contributing_positions if p['symbol'] == s),
            reverse=True
        )
        
        symbol_str = ', '.join(symbols)
        
        print(f"{i:<6} {item.underlying:<20} ${item.total_exposure:>12,.0f} {item.percentage:>10.2f}%  {symbol_str}")
    
    print()
    print("=" * 80)
    print("EXPOSURE CHAINS")
    print("=" * 80)
    print()
    
    # Show exposure chains
    for pos in sample_positions:
        symbol = pos['symbol']
        chains = analyzer.get_exposure_chain(symbol)
        
        if len(chains) == 1 and len(chains[0]) == 1:
            # No mapping
            print(f"{symbol}: {symbol} (no mapping)")
        elif len(chains) == 1:
            # Single chain
            chain = chains[0]
            chain_str = ' → '.join(
                f"{c[0]} ({c[1]:.2f}x)" if c[1] != 1.0 else c[0] 
                for c in chain
            )
            print(f"{symbol}: {chain_str}")
        else:
            # Multiple chains
            print(f"{symbol}:")
            for i, chain in enumerate(chains, 1):
                chain_str = ' → '.join(
                    f"{c[0]} ({c[1]:.2f}x)" if c[1] != 1.0 else c[0] 
                    for c in chain
                )
                print(f"  [{i}] {chain_str}")
    
    print()
    print("=" * 80)
    print("CONCENTRATION INSIGHTS")
    print("=" * 80)
    print()
    
    # Calculate insights
    if len(concentrations) >= 3:
        top_3_pct = sum(item.percentage for item in concentrations[:3])
        print(f"• Top 3 concentrations: {top_3_pct:.1f}% of portfolio")
    
    if len(concentrations) >= 5:
        top_5_pct = sum(item.percentage for item in concentrations[:5])
        print(f"• Top 5 concentrations: {top_5_pct:.1f}% of portfolio")
    
    # Check for high concentration risk
    high_risk = [c for c in concentrations if c.percentage >= 15]
    if high_risk:
        print(f"\n⚠️  High concentration risk detected:")
        for item in high_risk:
            print(f"   - {item.underlying}: {item.percentage:.1f}%")
    
    moderate_risk = [c for c in concentrations if 10 <= c.percentage < 15]
    if moderate_risk:
        print(f"\n⚡ Moderate concentration:")
        for item in moderate_risk:
            print(f"   - {item.underlying}: {item.percentage:.1f}%")
    
    print()


if __name__ == "__main__":
    test_concentration_analyzer()
