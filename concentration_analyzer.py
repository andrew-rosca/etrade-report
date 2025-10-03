"""
Concentration Analyzer Module

Analyzes portfolio concentration by mapping positions to their underlying exposures.
Supports both direct holdings and indirect exposures through ETFs and other instruments.
"""

import yaml
from typing import Dict, List, Tuple, Optional, Set, Any
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class ExposureMapping:
    """Represents an exposure mapping for a symbol."""
    symbol: str
    underlying: str
    factor: float = 1.0


@dataclass
class ConcentrationItem:
    """Represents a concentration in an underlying asset."""
    underlying: str
    total_exposure: float
    percentage: float
    contributing_positions: List[Dict]


class ConcentrationAnalyzer:
    """Analyzes portfolio concentration based on underlying asset exposures."""
    
    def __init__(self, config: Dict):
        """Initialize with configuration dictionary."""
        self.config = config
        self.exposure_mappings = self._load_exposure_mappings()
        
    def _load_exposure_mappings(self) -> Dict[str, List[ExposureMapping]]:
        """
        Load and parse exposure mappings from config.
        
        Supports multiple formats:
        1. Simple string: "UNDERLYING" or "UNDERLYING*factor"
           Example: "Bitcoin" or "NVDA*0.14"
        2. List of strings: For symbols with multiple exposures
           Example: ["NVDA*0.14", "MSFT*0.06", "AAPL*0.056"]
        3. Dict format: {"underlying": "ASSET", "factor": 1.0}
        
        Returns Dict mapping symbol to LIST of ExposureMappings
        """
        mappings: Dict[str, List[ExposureMapping]] = {}
        raw_mappings = self.config.get('exposure_mappings', {})
        
        for symbol, mapping_data in raw_mappings.items():
            symbol_upper = symbol.upper()
            exposure_list = []
            
            # Format 1: Simple string "UNDERLYING" or "UNDERLYING*factor"
            if isinstance(mapping_data, str):
                if not mapping_data.strip():  # Skip empty strings
                    continue
                    
                if '*' in mapping_data:
                    # Parse "UNDERLYING*factor"
                    parts = mapping_data.split('*')
                    underlying = parts[0].strip()
                    factor = float(parts[1].strip())
                else:
                    # Just "UNDERLYING" - default factor to 1.0
                    underlying = mapping_data.strip()
                    factor = 1.0
                
                exposure_list.append(ExposureMapping(
                    symbol=symbol_upper,
                    underlying=underlying,
                    factor=factor
                ))
            
            # Format 2: List of strings (for multiple exposures)
            elif isinstance(mapping_data, list):
                for item in mapping_data:
                    if isinstance(item, str) and item.strip():
                        if '*' in item:
                            parts = item.split('*')
                            underlying = parts[0].strip()
                            factor = float(parts[1].strip())
                        else:
                            underlying = item.strip()
                            factor = 1.0
                        
                        exposure_list.append(ExposureMapping(
                            symbol=symbol_upper,
                            underlying=underlying,
                            factor=factor
                        ))
            
            # Format 3: Dict format (backward compatibility)
            elif isinstance(mapping_data, dict):
                underlying = mapping_data.get('underlying')
                factor = mapping_data.get('factor', 1.0)
                
                if underlying:
                    exposure_list.append(ExposureMapping(
                        symbol=symbol_upper,
                        underlying=underlying,
                        factor=float(factor)
                    ))
            
            if exposure_list:
                mappings[symbol_upper] = exposure_list
        
        return mappings
    
    def _resolve_ultimate_underlying(self, symbol: str, visited: Optional[Set[str]] = None) -> List[Tuple[str, float]]:
        """
        Recursively resolve a symbol to its ultimate underlying asset(s).
        
        Returns list of (ultimate_underlying, cumulative_factor) tuples.
        Can return multiple results if a symbol has multiple exposures.
        
        Example: MSTY -> MSTR -> Bitcoin with factors multiplied
        Example: SPYG -> [(NVDA, 0.14), (MSFT, 0.06), (AAPL, 0.056)]
        """
        if visited is None:
            visited = set()
        
        # Prevent infinite loops
        if symbol in visited:
            return [(symbol, 1.0)]
        
        visited.add(symbol)
        
        # Check if this symbol has an exposure mapping
        if symbol not in self.exposure_mappings:
            # No mapping, this is the ultimate underlying
            return [(symbol, 1.0)]
        
        mapping_list = self.exposure_mappings[symbol]
        
        results = []
        for mapping in mapping_list:
            # Recursively resolve each underlying
            underlying_results = self._resolve_ultimate_underlying(
                mapping.underlying.upper(), 
                visited.copy()  # Use copy to allow different branches
            )
            
            # Multiply factors for each result
            for ultimate, underlying_factor in underlying_results:
                cumulative_factor = mapping.factor * underlying_factor
                results.append((ultimate, cumulative_factor))
        
        return results
    
    def calculate_concentrations(self, positions: List[Dict], 
                                top_n: Optional[int] = None) -> List[ConcentrationItem]:
        """
        Calculate concentration exposures across all positions.
        
        Args:
            positions: List of position dictionaries with 'symbol' and 'market_value'
            top_n: Number of top concentrations to return (None = all)
            
        Returns:
            List of ConcentrationItem objects sorted by exposure (descending)
        """
        # Calculate total portfolio value
        total_portfolio_value = sum(pos.get('market_value', 0) for pos in positions)
        
        if total_portfolio_value == 0:
            return []
        
        # Accumulate exposures by ultimate underlying
        exposure_map: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_exposure': 0.0,
            'positions': []
        })
        
        for pos in positions:
            symbol = pos.get('symbol', '').upper()
            market_value = pos.get('market_value', 0)
            
            if market_value == 0:
                continue
            
            # Resolve to ultimate underlying(s) - can return multiple exposures
            underlying_results = self._resolve_ultimate_underlying(symbol)
            
            # Add exposure for each underlying
            for ultimate_underlying, factor in underlying_results:
                # Calculate exposure value
                exposure_value = market_value * factor
                
                # Add to the ultimate underlying's exposure
                exposure_map[ultimate_underlying]['total_exposure'] += exposure_value
                exposure_map[ultimate_underlying]['positions'].append({
                    'symbol': symbol,
                    'market_value': market_value,
                    'exposure_value': exposure_value,
                    'factor': factor,
                    'quantity': pos.get('quantity', 0),
                    'current_price': pos.get('current_price', 0)
                })
        
        # Convert to ConcentrationItem objects
        concentrations = []
        for underlying, data in exposure_map.items():
            concentration = ConcentrationItem(
                underlying=underlying,
                total_exposure=data['total_exposure'],
                percentage=(data['total_exposure'] / total_portfolio_value) * 100,
                contributing_positions=data['positions']
            )
            concentrations.append(concentration)
        
        # Sort by exposure (descending)
        concentrations.sort(key=lambda x: x.total_exposure, reverse=True)
        
        # Return top N if specified
        if top_n is not None:
            concentrations = concentrations[:top_n]
        
        return concentrations
    
    def get_exposure_chain(self, symbol: str) -> List[List[Tuple[str, float]]]:
        """
        Get the full exposure chain(s) for a symbol.
        
        Returns list of chains (one per exposure if multiple).
        Each chain is a list of (symbol, cumulative_factor) tuples.
        
        Example single exposure: MSTY -> [[(MSTY, 1.0), (MSTR, 1.0), (Bitcoin, 1.0)]]
        Example multiple: SPYG -> [[(SPYG, 1.0), (NVDA, 0.14)], [(SPYG, 1.0), (MSFT, 0.06)]]
        """
        if symbol not in self.exposure_mappings:
            # No mapping, return simple chain
            return [[(symbol, 1.0)]]
        
        all_chains = []
        mapping_list = self.exposure_mappings[symbol]
        
        for initial_mapping in mapping_list:
            chain = [(symbol, 1.0)]
            visited = {symbol}
            current_symbol = initial_mapping.underlying.upper()
            cumulative_factor = initial_mapping.factor
            
            chain.append((current_symbol, cumulative_factor))
            visited.add(current_symbol)
            
            # Follow the chain further if the underlying has its own mappings
            while current_symbol in self.exposure_mappings:
                current_mappings = self.exposure_mappings[current_symbol]
                
                # If there are multiple mappings, just take the first one for the chain
                # (in reality, this would split into more chains, but for display simplicity)
                if not current_mappings:
                    break
                
                next_mapping = current_mappings[0]
                next_symbol = next_mapping.underlying.upper()
                
                # Prevent infinite loops
                if next_symbol in visited:
                    break
                
                visited.add(next_symbol)
                cumulative_factor *= next_mapping.factor
                chain.append((next_symbol, cumulative_factor))
                current_symbol = next_symbol
            
            all_chains.append(chain)
        
        return all_chains
