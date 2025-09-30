#!/usr/bin/env python3
"""
Historical Account Balance Reconstruction

This module reconstructs account balance history by fetching transactions
from E*TRADE API and working backwards from the current balance.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import pandas as pd
from etrade_simple_api import ETradeSimpleAPI
from transaction_cache import TransactionCache


class BalanceHistoryReconstructor:
    def __init__(self, api: ETradeSimpleAPI):
        self.api = api
        self.transaction_cache = TransactionCache(api)

    def fetch_historical_transactions(self, account_id_key: str, days_back: int = 7) -> List[Dict[str, Any]]:
        """Fetch transactions with intelligent caching to avoid repeated API calls."""
        return self.transaction_cache.get_transactions(account_id_key, days_back=days_back)

    def parse_transaction(self, transaction: Dict[str, Any]) -> Dict[str, Any]:
        """Parse a single transaction and extract relevant balance impact."""
        try:
            # Extract key transaction details
            trans_id = transaction.get('transactionId', '')
            trans_date = transaction.get('transactionDate', '')
            trans_type = transaction.get('transactionType', '')
            amount = float(transaction.get('amount', 0))
            description = transaction.get('description', '')

            # Convert transaction date to datetime
            if trans_date:
                try:
                    # E*TRADE uses Unix timestamp in milliseconds
                    timestamp_ms = int(trans_date)
                    date_obj = datetime.fromtimestamp(timestamp_ms / 1000)
                except (ValueError, TypeError):
                    date_obj = datetime.now()
                    print(f"⚠️ Could not parse date {trans_date}, using current date")
            else:
                date_obj = datetime.now()

            # Calculate balance impact for this transaction
            balance_impact = self._calculate_balance_impact(trans_type, amount, description)

            return {
                'transaction_id': trans_id,
                'date': date_obj,
                'type': trans_type,
                'amount': amount,
                'description': description,
                'balance_impact': balance_impact
            }

        except Exception as e:
            print(f"❌ Error parsing transaction: {e}")
            return {
                'transaction_id': '',
                'date': datetime.now(),
                'type': 'unknown',
                'amount': 0,
                'description': str(transaction),
                'balance_impact': 0
            }

    def _calculate_balance_impact(self, trans_type: str, amount: float, description: str) -> float:
        """
        Calculate how this transaction affects the account balance.
        Focus only on actual cash movements that affect the account value:
        - Deposits/withdrawals (real money in/out)
        - Dividends and interest (real money in)
        - Fees and charges (real money out)
        - Exclude buys/sells (net zero - just moving between cash and positions)
        """

        trans_type_lower = trans_type.lower()
        desc_lower = description.lower()

        # These are real cash flows that affect account value
        cash_flow_types = [
            'dividend',           # Dividend payments
            'interest',           # Interest income
            'funds received',     # Deposits/transfers in
            'automated payment',  # Bill payments/withdrawals
            'withdrawal',         # Cash withdrawals
            'deposit',           # Cash deposits
            'fee',               # Fees
            'misc',              # Misc charges/credits
        ]

        # These are NOT cash flows (just moving money within the account)
        # Note: Check these AFTER checking for ACH deposits/withdrawals
        neutral_transfer_descriptions = [
            'trnsfr cash to margin',  # Internal margin transfers
            'trnsfr margin to cash',  # Internal margin transfers
        ]

        neutral_types = [
            'bought',            # Buying stocks (cash -> positions)
            'sold',              # Selling stocks (positions -> cash)
        ]

        # Check if this is an ACH deposit/withdrawal (real money in/out)
        if 'ach' in desc_lower or 'online transfer' in trans_type_lower:
            # ACH deposits and withdrawals are real cash flows
            if 'deposit' in desc_lower or 'credit' in desc_lower:
                return amount
            elif 'debit' in desc_lower or 'withdrawal' in desc_lower:
                return amount

        # Check if this is an internal transfer (not a cash flow)
        for neutral_desc in neutral_transfer_descriptions:
            if neutral_desc in desc_lower:
                return 0.0

        # Generic "Transfer" type without ACH is internal (margin/cash movements)
        if 'transfer' in trans_type_lower:
            return 0.0

        # Check if this is a neutral (non-cash-flow) transaction
        for neutral_type in neutral_types:
            if neutral_type in trans_type_lower:
                return 0.0

        # Check if this is a cash flow transaction
        for cash_type in cash_flow_types:
            if cash_type in trans_type_lower:
                # Return the amount as-is (positive for inflows, negative for outflows)
                return amount

        # If we don't recognize the type, default to treating it as a cash flow
        # but log it so we can improve the logic
        print(f"⚠️ Unknown transaction type '{trans_type}': ${amount}")
        return amount

    def create_cash_flow_history(self, account_id_key: str, days_back: int = 7) -> pd.DataFrame:
        """Create a DataFrame of daily cash flows over the specified period."""

        # Fetch transactions using the cache
        transactions = self.fetch_historical_transactions(account_id_key, days_back)

        if not transactions:
            print("⚠️ No transactions available for cash flow analysis")
            # Return empty DataFrame with expected structure
            return pd.DataFrame([{
                'date': datetime.now(),
                'daily_flow': 0,
                'cumulative_flow': 0,
                'transaction_count': 0,
                'hover_text': 'No data',
                'bar_color': '#808080'
            }])

        # Parse transactions
        parsed_transactions = [self.parse_transaction(t) for t in transactions]

        # Filter to only cash-affecting transactions
        cash_affecting = [t for t in parsed_transactions if t['balance_impact'] != 0]
        ignored = [t for t in parsed_transactions if t['balance_impact'] == 0]

        print(f"📊 Processing {len(parsed_transactions)} transactions:")
        print(f"  💰 {len(cash_affecting)} affect cash flow")
        print(f"  🚫 {len(ignored)} ignored (trades/internal transfers)")

        # Create a complete date range for all days
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        # Generate all dates in the range
        all_dates = []
        current_date = start_date.date()
        while current_date <= end_date.date():
            all_dates.append(current_date)
            current_date += timedelta(days=1)

        # Group transactions by date
        daily_flows = {}
        for transaction in cash_affecting:
            date_key = transaction['date'].date()
            if date_key not in daily_flows:
                daily_flows[date_key] = {
                    'date': transaction['date'],
                    'total_flow': 0,
                    'transactions': []
                }
            daily_flows[date_key]['total_flow'] += transaction['balance_impact']
            daily_flows[date_key]['transactions'].append({
                'type': transaction['type'],
                'amount': transaction['amount'],
                'description': transaction['description'],
                'impact': transaction['balance_impact']
            })

        print(f"📅 Found cash flows on {len(daily_flows)} days out of {len(all_dates)} days")

        # Create cash flow history with cumulative tracking for ALL days
        cash_flow_history = []
        cumulative_flow = 0

        for date_key in all_dates:
            if date_key in daily_flows:
                # Day with transactions
                day_data = daily_flows[date_key]
                cumulative_flow += day_data['total_flow']

                # Create hover text with transaction details
                transaction_lines = []
                for trans in day_data['transactions']:
                    transaction_lines.append(
                        f"• {trans['type']}: ${trans['impact']:+,.2f}"
                    )

                hover_text = f"Date: {day_data['date'].strftime('%m/%d/%Y')}<br>"
                hover_text += f"Net Flow: ${day_data['total_flow']:+,.2f}<br>"
                hover_text += f"Transactions ({len(day_data['transactions'])}):<br>"
                hover_text += '<br>'.join(transaction_lines)

                cash_flow_history.append({
                    'date': day_data['date'],
                    'daily_flow': day_data['total_flow'],
                    'cumulative_flow': cumulative_flow,
                    'transaction_count': len(day_data['transactions']),
                    'hover_text': hover_text,
                    'bar_color': '#28a745' if day_data['total_flow'] > 0 else '#dc3545'
                })
            else:
                # Day with no transactions - show zero
                hover_text = f"Date: {datetime.combine(date_key, datetime.min.time()).strftime('%m/%d/%Y')}<br>No cash flow transactions"

                cash_flow_history.append({
                    'date': datetime.combine(date_key, datetime.min.time()),
                    'daily_flow': 0,
                    'cumulative_flow': cumulative_flow,
                    'transaction_count': 0,
                    'hover_text': hover_text,
                    'bar_color': '#555555'  # Gray for zero
                })

        # Convert to DataFrame and sort
        df = pd.DataFrame(cash_flow_history)
        df = df.sort_values('date').reset_index(drop=True)

        print(f"✅ Created cash flow history with {len(df)} days of data")
        print(f"   Total net flow: ${cumulative_flow:+,.2f}")

        return df
