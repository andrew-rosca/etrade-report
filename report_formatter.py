from portfolio_analyzer import PortfolioAnalyzer, PortfolioPosition, AccountInfo
from typing import Dict, List
from tabulate import tabulate
from colorama import Fore, Style, init
import sys


class ReportFormatter:
    """Formats and displays portfolio reports."""
    
    def __init__(self):
        init(autoreset=True)  # Initialize colorama
        self.percentage_precision = 2
        self.dollar_precision = 2
    
    def set_precision(self, percentage_precision: int = 2, dollar_precision: int = 2):
        """Set display precision for numbers."""
        self.percentage_precision = percentage_precision
        self.dollar_precision = dollar_precision
    
    def format_currency(self, amount: float) -> str:
        """Format currency with proper precision."""
        return f"${amount:,.{self.dollar_precision}f}"
    
    def format_percentage(self, percentage: float) -> str:
        """Format percentage with proper precision."""
        return f"{percentage:.{self.percentage_precision}f}%"
    
    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{title.center(80)}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'=' * 80}{Style.RESET_ALL}")
    
    def print_portfolio_summary(self, report: Dict):
        """Print portfolio overview summary."""
        self.print_header("PORTFOLIO SUMMARY")
        
        print(f"{Fore.GREEN}Report Generated:{Style.RESET_ALL} {report['timestamp']}")
        print(f"{Fore.GREEN}Total Portfolio Value:{Style.RESET_ALL} {self.format_currency(report['total_portfolio_value'])}")
        print(f"{Fore.GREEN}Total Positions:{Style.RESET_ALL} {report['position_count']}")
        
        gain_loss = report['total_gain_loss']
        gain_loss_pct = report['total_gain_loss_pct']
        
        if gain_loss >= 0:
            print(f"{Fore.GREEN}Total Gain/Loss:{Style.RESET_ALL} {Fore.GREEN}+{self.format_currency(gain_loss)} ({self.format_percentage(gain_loss_pct)}){Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Total Gain/Loss:{Style.RESET_ALL} {Fore.RED}{self.format_currency(gain_loss)} ({self.format_percentage(gain_loss_pct)}){Style.RESET_ALL}")
    
    def print_bucket_allocation(self, report: Dict):
        """Print bucket allocation table."""
        self.print_header("BUCKET ALLOCATION")
        
        bucket_allocations = report['bucket_allocations']
        
        # Prepare table data
        table_data = []
        for bucket_name, data in bucket_allocations.items():
            if data['total_value'] > 0:  # Only show buckets with positions
                color = Fore.GREEN
                if bucket_name == "Unassigned":
                    color = Fore.RED
                
                table_data.append([
                    f"{color}{bucket_name}{Style.RESET_ALL}",
                    data['position_count'],
                    self.format_currency(data['total_value']),
                    f"{color}{self.format_percentage(data['percentage'])}{Style.RESET_ALL}"
                ])
        
        # Sort by percentage (descending)
        table_data.sort(key=lambda x: float(x[3].replace('%', '').replace(Fore.RED, '').replace(Fore.GREEN, '').replace(Style.RESET_ALL, '')), reverse=True)
        
        headers = ["Bucket", "Positions", "Value", "Allocation %"]
        print(tabulate(table_data, headers=headers, tablefmt="grid"))
    
    def print_bucket_details(self, report: Dict):
        """Print detailed positions for each bucket."""
        self.print_header("BUCKET DETAILS")
        
        bucket_allocations = report['bucket_allocations']
        
        for bucket_name, data in bucket_allocations.items():
            if data['position_count'] > 0:
                color = Fore.GREEN if bucket_name != "Unassigned" else Fore.RED
                
                print(f"\n{color}{bucket_name.upper()} BUCKET{Style.RESET_ALL}")
                print(f"Total Value: {self.format_currency(data['total_value'])} ({self.format_percentage(data['percentage'])})")
                print("-" * 80)
                
                # Prepare position table
                position_data = []
                for pos in data['positions']:
                    gain_loss_color = Fore.GREEN if pos.gain_loss >= 0 else Fore.RED
                    
                    position_data.append([
                        pos.symbol,
                        pos.description[:30] + "..." if len(pos.description) > 30 else pos.description,
                        f"{pos.quantity:,.2f}",
                        self.format_currency(pos.current_price),
                        self.format_currency(pos.market_value),
                        f"{gain_loss_color}{self.format_currency(pos.gain_loss)}{Style.RESET_ALL}",
                        f"{gain_loss_color}{self.format_percentage(pos.gain_loss_pct)}{Style.RESET_ALL}"
                    ])
                
                # Sort by market value (descending)
                position_data.sort(key=lambda x: float(x[4].replace('$', '').replace(',', '')), reverse=True)
                
                headers = ["Symbol", "Description", "Quantity", "Price", "Market Value", "Gain/Loss", "G/L %"]
                print(tabulate(position_data, headers=headers, tablefmt="grid"))
    
    def print_margin_info(self, report: Dict):
        """Print margin utilization information."""
        self.print_header("MARGIN & CASH INFORMATION")
        
        margin_metrics = report['margin_metrics']
        account_info = report['account_info']
        
        print(f"{Fore.GREEN}Net Account Value:{Style.RESET_ALL} {self.format_currency(account_info.net_account_value)}")
        print(f"{Fore.GREEN}Cash Available for Investment:{Style.RESET_ALL} {self.format_currency(margin_metrics['available_cash'])}")
        print(f"{Fore.GREEN}Margin Buying Power:{Style.RESET_ALL} {self.format_currency(margin_metrics['margin_buying_power'])}")
        
        margin_balance = margin_metrics['margin_balance']
        margin_utilization = margin_metrics['margin_utilization_pct']
        
        if margin_balance > 0:
            print(f"{Fore.YELLOW}Margin Balance:{Style.RESET_ALL} {Fore.YELLOW}{self.format_currency(margin_balance)}{Style.RESET_ALL}")
            
            utilization_color = Fore.GREEN
            if margin_utilization > 50:
                utilization_color = Fore.YELLOW
            elif margin_utilization > 75:
                utilization_color = Fore.RED
            
            print(f"{Fore.GREEN}Margin Utilization:{Style.RESET_ALL} {utilization_color}{self.format_percentage(margin_utilization)}{Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}Margin Balance:{Style.RESET_ALL} {self.format_currency(margin_balance)}")
            print(f"{Fore.GREEN}Margin Utilization:{Style.RESET_ALL} {Fore.GREEN}{self.format_percentage(margin_utilization)}{Style.RESET_ALL}")
    
    def print_unassigned_warning(self, report: Dict):
        """Print warning about unassigned positions."""
        unassigned_positions = report['unassigned_positions']
        
        if unassigned_positions:
            self.print_header("⚠️  UNASSIGNED POSITIONS WARNING")
            
            print(f"{Fore.RED}WARNING: {len(unassigned_positions)} position(s) are not assigned to any bucket!{Style.RESET_ALL}")
            print(f"{Fore.YELLOW}Please update config.yml to assign these positions to appropriate buckets:{Style.RESET_ALL}\n")
            
            for pos in unassigned_positions:
                print(f"{Fore.RED}  • {pos.symbol}{Style.RESET_ALL} - {pos.description[:50]}... ({self.format_currency(pos.market_value)})")
            
            print(f"\n{Fore.YELLOW}Add these symbols to the appropriate bucket in config.yml{Style.RESET_ALL}")
    
    def print_full_report(self, report: Dict):
        """Print the complete portfolio report."""
        self.print_portfolio_summary(report)
        self.print_bucket_allocation(report)
        self.print_margin_info(report)
        
        if report['unassigned_positions']:
            self.print_unassigned_warning(report)
        
        self.print_bucket_details(report)
        
        print(f"\n{Fore.CYAN}End of Report{Style.RESET_ALL}")
        print("=" * 80)