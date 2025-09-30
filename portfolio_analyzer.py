import yaml
import pandas as pd
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime
import os


@dataclass
class PortfolioPosition:
    """Represents a single portfolio position."""
    symbol: str
    description: str
    quantity: float
    current_price: float
    market_value: float
    gain_loss: float
    gain_loss_pct: float
    bucket: str = "Unassigned"


@dataclass
class AccountInfo:
    """Represents account balance and margin information."""
    total_account_value: float
    cash_available_for_investment: float
    margin_buying_power: float
    margin_balance: float
    net_account_value: float


class PortfolioAnalyzer:
    """Analyzes portfolio positions and generates bucket reports."""
    
    def __init__(self, config_path: str = "config.yml"):
        self.config = self._load_config(config_path)
        self.buckets = self.config.get('buckets', {})
        self.settings = self.config.get('settings', {})
        
        # Create reverse mapping for quick bucket lookup
        self.symbol_to_bucket = {}
        for bucket_name, symbols in self.buckets.items():
            for symbol in symbols:
                self.symbol_to_bucket[symbol.upper()] = bucket_name
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from YAML file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_path, 'r') as file:
            return yaml.safe_load(file)
    
    def assign_buckets_to_positions(self, positions: List[Dict]) -> List[PortfolioPosition]:
        """Assign bucket categories to positions."""
        portfolio_positions = []
        min_value = self.settings.get('min_position_value', 100)
        
        for pos in positions:
            if pos['market_value'] < min_value:
                continue
                
            symbol = pos['symbol'].upper()
            description = pos.get('description', pos['symbol']).upper()
            
            # Try multiple matching strategies
            bucket = self._find_bucket_for_symbol(symbol, description)
            
            portfolio_position = PortfolioPosition(
                symbol=pos['symbol'],
                description=pos['description'],
                quantity=pos['quantity'],
                current_price=pos['current_price'],
                market_value=pos['market_value'],
                gain_loss=pos['gain_loss'],
                gain_loss_pct=pos['gain_loss_pct'],
                bucket=bucket
            )
            portfolio_positions.append(portfolio_position)
        
        return portfolio_positions
    
    def _find_bucket_for_symbol(self, symbol: str, description: str) -> str:
        """Find bucket for symbol using multiple matching strategies."""
        # Strategy 1: Exact match (current behavior)
        if symbol in self.symbol_to_bucket:
            return self.symbol_to_bucket[symbol]
        
        # Strategy 2: Pattern matching for each bucket
        for bucket_name, patterns in self.buckets.items():
            for pattern in patterns:
                pattern_upper = pattern.upper()
                
                # Wildcard matching
                if '*' in pattern_upper:
                    if self._matches_wildcard_pattern(symbol, description, pattern_upper):
                        return bucket_name
                
                # Substring matching (contains)
                elif pattern_upper in symbol or pattern_upper in description:
                    return bucket_name
        
        return "Unassigned"
    
    def _matches_wildcard_pattern(self, symbol: str, description: str, pattern: str) -> bool:
        """Check if symbol or description matches a wildcard pattern."""
        import fnmatch
        
        # Try matching against both symbol and description
        return (fnmatch.fnmatch(symbol, pattern) or 
                fnmatch.fnmatch(description, pattern))
    
    def calculate_bucket_allocations(self, positions: List[PortfolioPosition]) -> Dict[str, Dict]:
        """Calculate allocation percentages for each bucket."""
        total_value = sum(pos.market_value for pos in positions)
        
        if total_value == 0:
            return {}
        
        bucket_data = {}
        
        # Initialize all configured buckets
        for bucket_name in self.buckets.keys():
            bucket_data[bucket_name] = {
                'total_value': 0.0,
                'percentage': 0.0,
                'positions': [],
                'position_count': 0
            }
        
        # Add Unassigned bucket
        bucket_data['Unassigned'] = {
            'total_value': 0.0,
            'percentage': 0.0,
            'positions': [],
            'position_count': 0
        }
        
        # Calculate bucket totals
        for pos in positions:
            bucket = pos.bucket
            if bucket not in bucket_data:
                bucket_data[bucket] = {
                    'total_value': 0.0,
                    'percentage': 0.0,
                    'positions': [],
                    'position_count': 0
                }
            
            bucket_data[bucket]['total_value'] += pos.market_value
            bucket_data[bucket]['positions'].append(pos)
            bucket_data[bucket]['position_count'] += 1
        
        # Calculate percentages
        for bucket in bucket_data:
            bucket_data[bucket]['percentage'] = (bucket_data[bucket]['total_value'] / total_value) * 100
        
        return bucket_data
    
    def calculate_margin_utilization(self, account_info: AccountInfo) -> Dict[str, float]:
        """Calculate margin utilization metrics."""
        if account_info.margin_buying_power <= 0:
            return {
                'margin_balance': account_info.margin_balance,
                'margin_utilization_pct': 0.0,
                'available_cash': account_info.cash_available_for_investment,
                'margin_buying_power': account_info.margin_buying_power
            }
        
        # Calculate margin utilization as a percentage
        margin_utilization_pct = 0.0
        if account_info.margin_balance != 0 and account_info.net_account_value > 0:
            # Negative margin balance means borrowed money (margin debt)
            # Margin utilization = absolute margin balance / net account value
            margin_utilization_pct = (abs(account_info.margin_balance) / account_info.net_account_value) * 100
        
        return {
            'margin_balance': account_info.margin_balance,
            'margin_utilization_pct': margin_utilization_pct,
            'available_cash': account_info.cash_available_for_investment,
            'margin_buying_power': account_info.margin_buying_power
        }
    
    def generate_summary_report(self, positions: List[PortfolioPosition], 
                              account_info: AccountInfo) -> Dict:
        """Generate comprehensive portfolio summary report."""
        bucket_allocations = self.calculate_bucket_allocations(positions)
        margin_metrics = self.calculate_margin_utilization(account_info)
        
        total_portfolio_value = sum(pos.market_value for pos in positions)
        total_gain_loss = sum(pos.gain_loss for pos in positions)
        total_gain_loss_pct = (total_gain_loss / (total_portfolio_value - total_gain_loss)) * 100 if total_portfolio_value > 0 else 0
        
        unassigned_positions = [pos for pos in positions if pos.bucket == "Unassigned"]
        
        return {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_portfolio_value': total_portfolio_value,
            'total_gain_loss': total_gain_loss,
            'total_gain_loss_pct': total_gain_loss_pct,
            'bucket_allocations': bucket_allocations,
            'margin_metrics': margin_metrics,
            'account_info': account_info,
            'unassigned_positions': unassigned_positions,
            'position_count': len(positions),
            'settings_used': self.settings
        }