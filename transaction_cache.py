#!/usr/bin/env python3
"""
E*TRADE Transaction Cache

This module handles fetching and caching of E*TRADE transactions to avoid
repeated API calls and provide efficient access to transaction history.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import hashlib
from etrade_simple_api import ETradeSimpleAPI


class TransactionCache:
    def __init__(self, api: ETradeSimpleAPI, cache_dir: str = ".cache"):
        self.api = api
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
    
    def _get_cache_file(self, account_id_key: str) -> str:
        """Generate cache filename for account."""
        # Hash the account key for privacy
        account_hash = hashlib.md5(account_id_key.encode()).hexdigest()[:8]
        return os.path.join(self.cache_dir, f"transactions_{account_hash}.json")
    
    def _load_cache(self, account_id_key: str) -> Dict[str, Any]:
        """Load cached transactions for account."""
        cache_file = self._get_cache_file(account_id_key)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    cache_data = json.load(f)
                    # Convert date strings back to timestamps for consistency
                    return cache_data
            except (json.JSONDecodeError, FileNotFoundError):
                print("⚠️  Cache file corrupted, will rebuild")
                return {'transactions': [], 'last_updated': None}
        return {'transactions': [], 'last_updated': None}
    
    def _save_cache(self, account_id_key: str, transactions: List[Dict[str, Any]]) -> None:
        """Save transactions to cache."""
        cache_file = self._get_cache_file(account_id_key)
        cache_data = {
            'transactions': transactions,
            'last_updated': datetime.now().isoformat()
        }
        try:
            with open(cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Failed to save cache: {e}")
    
    def _fetch_recent_transactions(self, account_id_key: str, count: int = 50) -> List[Dict[str, Any]]:
        """Fetch recent transactions from API."""
        try:
            response = self.api.get_account_transactions(account_id_key, count=count)
            
            if 'Transaction' not in response:
                if isinstance(response, dict) and 'code' in response:
                    print(f"❌ API Error: {response.get('message', 'Unknown error')}")
                return []
            
            transactions = response['Transaction']
            if not isinstance(transactions, list):
                transactions = [transactions]
            
            return transactions
        except Exception as e:
            print(f"❌ Error fetching transactions: {e}")
            return []
    
    def _fetch_paginated_transactions(self, account_id_key: str, days_back: int = 30) -> List[Dict[str, Any]]:
        """Fetch transactions using pagination to get full history."""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)

        all_transactions = []
        seen_ids = set()  # Track transaction IDs to prevent duplicates
        marker = None
        max_calls = 50  # Increased from 20 to fetch more history
        call_count = 0
        oldest_date_found = None
        expected_total_count = None  # Track total from first response

        print(f"📊 Fetching transaction history for {days_back} days (back to {start_date.strftime('%m/%d/%Y')})...")

        while call_count < max_calls:
            call_count += 1
            print(f"🔄 API call {call_count}/{max_calls}...")

            try:
                # Note: E*TRADE API date parameters seem unreliable, so we fetch without them
                # and filter locally
                response = self.api.get_account_transactions(
                    account_id_key, 
                    count=50, 
                    marker=marker
                )

                if 'Transaction' not in response:
                    print(f"⚠️  No more transactions found (call {call_count})")
                    break

                transactions = response['Transaction']
                if not isinstance(transactions, list):
                    transactions = [transactions]

                # Track oldest date and add transactions (with deduplication)
                new_transactions = []
                new_unique_count = 0
                for trans in transactions:
                    trans_id = trans.get('transactionId')

                    # Skip if we've already seen this transaction
                    if trans_id in seen_ids:
                        continue

                    seen_ids.add(trans_id)
                    new_unique_count += 1

                    try:
                        trans_date_ms = int(trans.get('transactionDate', 0))
                        trans_date_obj = datetime.fromtimestamp(trans_date_ms / 1000)

                        if oldest_date_found is None or trans_date_obj < oldest_date_found:
                            oldest_date_found = trans_date_obj

                        # Only include transactions within date range
                        if start_date <= trans_date_obj <= end_date:
                            new_transactions.append(trans)
                    except (ValueError, TypeError):
                        continue

                all_transactions.extend(new_transactions)
                print(f"  ✅ Found {len(new_transactions)} transactions in range ({new_unique_count} new, {len(transactions) - new_unique_count} duplicates, total: {len(all_transactions)})")

                # Capture expected total count from first response
                if expected_total_count is None:
                    expected_total_count = response.get('totalCount', 0)
                    if expected_total_count:
                        print(f"  📊 Total available: {expected_total_count} transactions")

                # If we didn't get any new unique transactions, we're done
                if new_unique_count == 0:
                    print("📄 No new transactions found - pagination complete")
                    break

                # Check if we've fetched all available transactions based on initial totalCount
                if expected_total_count and len(seen_ids) >= int(expected_total_count):
                    print(f"📄 Fetched all {expected_total_count} available transactions")
                    break
                elif expected_total_count:
                    print(f"  📊 Progress: {len(seen_ids)}/{expected_total_count} transactions")
                
                # Check if we've gone back far enough in time
                if oldest_date_found and oldest_date_found < start_date:
                    print(f"� Reached target date: {oldest_date_found.strftime('%m/%d/%Y')} (requested {start_date.strftime('%m/%d/%Y')})")
                    break

                # Use the API's marker field if available, otherwise fall back to transaction ID
                if 'marker' in response:
                    marker = response['marker']
                    print(f"  📍 Using API marker: {marker}")
                elif transactions:
                    marker = transactions[-1].get('transactionId')
                    if not marker:
                        print("⚠️  No marker or transaction ID for pagination")
                        break
                else:
                    print("⚠️  No transactions or marker to continue pagination")
                    break

            except Exception as e:
                print(f"❌ Error in pagination call {call_count}: {e}")
                break

        # Report what we actually got
        if all_transactions and oldest_date_found:
            actual_days = (datetime.now() - oldest_date_found).days
            print(f"✅ Fetched {len(all_transactions)} transactions from {call_count} API calls")
            print(f"   Date range: {oldest_date_found.strftime('%m/%d/%Y')} to {datetime.now().strftime('%m/%d/%Y')} ({actual_days} days)")
        else:
            print(f"✅ Fetched {len(all_transactions)} transactions from {call_count} API calls")
        
        return all_transactions
    
    def get_transactions(self, account_id_key: str, days_back: int = 7, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """
        Get transactions with intelligent caching.
        
        Args:
            account_id_key: Account identifier
            days_back: Number of days to fetch
            force_refresh: Force refresh from API
        
        Returns:
            List of transaction dictionaries
        """
        if force_refresh:
            print("🔄 Force refresh requested, fetching from API...")
            transactions = self._fetch_paginated_transactions(account_id_key, days_back)
            self._save_cache(account_id_key, transactions)
            return transactions
        
        # Load cache
        cache_data = self._load_cache(account_id_key)
        cached_transactions = cache_data.get('transactions', [])
        
        if not cached_transactions:
            print("📁 No cached transactions, fetching full history...")
            transactions = self._fetch_paginated_transactions(account_id_key, days_back)
            self._save_cache(account_id_key, transactions)
            return transactions
        
        # Check if cached data covers the requested date range
        end_date = datetime.now()
        start_date = (end_date - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Find oldest transaction in cache
        oldest_cached_date = None
        for trans in cached_transactions:
            try:
                trans_date_ms = int(trans.get('transactionDate', 0))
                trans_date_obj = datetime.fromtimestamp(trans_date_ms / 1000)
                if oldest_cached_date is None or trans_date_obj < oldest_cached_date:
                    oldest_cached_date = trans_date_obj
            except (ValueError, TypeError):
                continue
        
        # If cache doesn't go back far enough, re-fetch with larger range
        if oldest_cached_date and oldest_cached_date > start_date:
            print(f"📁 Cache only goes back to {oldest_cached_date.strftime('%m/%d/%Y')}, but need data from {start_date.strftime('%m/%d/%Y')}")
            print(f"🔄 Re-fetching transactions for {days_back} days...")
            transactions = self._fetch_paginated_transactions(account_id_key, days_back)
            self._save_cache(account_id_key, transactions)
            return transactions
        
        # Check if we need fresh data by fetching recent transactions
        print("🔍 Checking for new transactions...")
        recent_transactions = self._fetch_recent_transactions(account_id_key, 50)

        if not recent_transactions:
            print("⚠️  No recent transactions found, using cache")
            return self._filter_by_date_range(cached_transactions, days_back)

        # Build set of current API transaction IDs
        api_ids = {t.get('transactionId') for t in recent_transactions}
        cached_ids = {t.get('transactionId') for t in cached_transactions}

        # Find new transactions (in API but not in cache)
        new_transactions = [t for t in recent_transactions if t.get('transactionId') not in cached_ids]

        # Find the oldest transaction timestamp in the API response
        # Transactions are in reverse chronological order, so we need to find the oldest one
        oldest_api_timestamp = None
        for t in recent_transactions:
            try:
                trans_date_ms = int(t.get('transactionDate', 0))
                if oldest_api_timestamp is None or trans_date_ms < oldest_api_timestamp:
                    oldest_api_timestamp = trans_date_ms
            except (ValueError, TypeError):
                continue

        if oldest_api_timestamp is None:
            print("⚠️  No valid timestamps in API response, using cache")
            return self._filter_by_date_range(cached_transactions, days_back)

        oldest_api_datetime = datetime.fromtimestamp(oldest_api_timestamp / 1000)
        print(f"📅 API response goes back to {oldest_api_datetime.strftime('%m/%d/%Y %H:%M:%S')}")

        # Find stale transactions (in cache but no longer in API)
        # IMPORTANT: Only check for stale transactions in the MOST RECENT time window
        # where we expect the API to have complete data (e.g., last 24-48 hours).
        # We can't assume the 50-transaction API response includes ALL transactions
        # back to oldest_api_timestamp - there could be older valid transactions.
        stale_ids = set()
        
        # Only check for stale transactions from the last 2 days
        # (pending transactions typically settle within 24-48 hours)
        recent_cutoff = datetime.now() - timedelta(days=2)
        recent_cutoff_ms = int(recent_cutoff.timestamp() * 1000)

        for t in cached_transactions:
            try:
                trans_date_ms = int(t.get('transactionDate', 0))

                # Only reconcile very recent transactions (last 2 days)
                # These are the ones that might be pending and could settle/change
                if trans_date_ms >= recent_cutoff_ms:
                    # If this recent cached transaction is not in the API response, it's stale
                    if t.get('transactionId') not in api_ids:
                        stale_ids.add(t.get('transactionId'))
            except (ValueError, TypeError):
                continue

        # Remove stale transactions from cache
        if stale_ids:
            print(f"🧹 Removing {len(stale_ids)} stale transactions (pending→settled)")
            cached_transactions = [t for t in cached_transactions if t.get('transactionId') not in stale_ids]
            cached_ids = {t.get('transactionId') for t in cached_transactions}

        if new_transactions or stale_ids:
            if new_transactions:
                print(f"✨ Found {len(new_transactions)} new transactions")
            # Merge new transactions with cleaned cache and sort by date (newest first)
            all_transactions = new_transactions + cached_transactions
            all_transactions = self._sort_transactions(all_transactions)
            # Remove duplicates (shouldn't happen, but just in case)
            all_transactions = self._deduplicate_transactions(all_transactions)
            self._save_cache(account_id_key, all_transactions)
            return self._filter_by_date_range(all_transactions, days_back)
        else:
            print("✅ Cache is up to date")
            return self._filter_by_date_range(cached_transactions, days_back)
    
    def _filter_by_date_range(self, transactions: List[Dict[str, Any]], days_back: int) -> List[Dict[str, Any]]:
        """Filter transactions to specified date range."""
        end_date = datetime.now()
        # Use start of day for start_date to include all transactions on that day
        start_date = (end_date - timedelta(days=days_back)).replace(hour=0, minute=0, second=0, microsecond=0)

        filtered = []
        for trans in transactions:
            try:
                trans_date_ms = int(trans.get('transactionDate', 0))
                trans_date_obj = datetime.fromtimestamp(trans_date_ms / 1000)
                if start_date <= trans_date_obj <= end_date:
                    filtered.append(trans)
            except (ValueError, TypeError):
                continue

        return filtered
    
    def _sort_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort transactions by date (newest first)."""
        def get_date(trans):
            try:
                return int(trans.get('transactionDate', 0))
            except (ValueError, TypeError):
                return 0
        
        return sorted(transactions, key=get_date, reverse=True)
    
    def _deduplicate_transactions(self, transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate transactions based on transaction ID."""
        seen_ids = set()
        deduplicated = []
        
        for trans in transactions:
            trans_id = trans.get('transactionId')
            if trans_id and trans_id not in seen_ids:
                seen_ids.add(trans_id)
                deduplicated.append(trans)
        
        return deduplicated
    
    def get_transaction_summary(self, account_id_key: str, days_back: int = 7) -> Dict[str, Any]:
        """Get summary statistics for transactions."""
        transactions = self.get_transactions(account_id_key, days_back)
        
        if not transactions:
            return {
                'total_transactions': 0,
                'date_range': 'No transactions',
                'transaction_types': {},
                'oldest_date': None,
                'newest_date': None
            }
        
        # Analyze transactions
        transaction_types = {}
        dates = []
        
        for trans in transactions:
            trans_type = trans.get('transactionType', 'Unknown')
            transaction_types[trans_type] = transaction_types.get(trans_type, 0) + 1
            
            try:
                trans_date_ms = int(trans.get('transactionDate', 0))
                trans_date_obj = datetime.fromtimestamp(trans_date_ms / 1000)
                dates.append(trans_date_obj)
            except (ValueError, TypeError):
                continue
        
        dates.sort()
        
        return {
            'total_transactions': len(transactions),
            'date_range': f"{dates[0].strftime('%m/%d/%Y')} - {dates[-1].strftime('%m/%d/%Y')}" if dates else 'No valid dates',
            'transaction_types': transaction_types,
            'oldest_date': dates[0] if dates else None,
            'newest_date': dates[-1] if dates else None
        }
    
    def clear_cache(self, account_id_key: Optional[str] = None) -> None:
        """Clear cache for specific account or all accounts."""
        if account_id_key:
            cache_file = self._get_cache_file(account_id_key)
            if os.path.exists(cache_file):
                os.remove(cache_file)
                print(f"✅ Cleared cache for account")
        else:
            # Clear all cache files
            for filename in os.listdir(self.cache_dir):
                if filename.startswith('transactions_') and filename.endswith('.json'):
                    os.remove(os.path.join(self.cache_dir, filename))
            print("✅ Cleared all transaction caches")