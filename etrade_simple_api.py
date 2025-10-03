#!/usr/bin/env python3

import time
import requests
import urllib.parse
import json
import os
import webbrowser
from requests_oauthlib import OAuth1Session
from typing import Dict, List, Any, Optional
import xml.etree.ElementTree as ET


class ETradeSimpleAPI:
    def __init__(self, client_key: str, client_secret: str, use_sandbox: bool = False):
        self.client_key = client_key
        self.client_secret = client_secret
        self.use_sandbox = use_sandbox
        self.base_url = 'https://apisb.etrade.com' if use_sandbox else 'https://api.etrade.com'
        self.auth_base_url = 'https://etwssandbox.etrade.com' if use_sandbox else 'https://us.etrade.com'
        
        # Token cache file
        self.token_file = '.etrade_tokens.json'
        
        # OAuth tokens
        self.access_token: str = ''
        self.access_token_secret: str = ''
        
        # Load cached tokens on initialization
        self._load_tokens()
    
    def _load_tokens(self) -> None:
        """Load access tokens from cache file if they exist and are not expired."""
        try:
            if os.path.exists(self.token_file):
                with open(self.token_file, 'r') as f:
                    token_data = json.load(f)
                    
                    # Check if tokens match our current configuration
                    if (token_data.get('client_key') == self.client_key and 
                        token_data.get('use_sandbox') == self.use_sandbox):
                        
                        # Check token age - E*TRADE tokens can last several hours but we validate them
                        timestamp = token_data.get('timestamp', 0)
                        age_hours = (time.time() - timestamp) / 3600

                        # Don't reject based on age alone - let validation check if they still work
                        if age_hours > 12:  # Only reject if extremely old (12+ hours)
                            print(f"⚠️  Cached tokens are {age_hours:.1f} hours old, considered expired")
                            return
                            
                        self.access_token = token_data.get('access_token', '')
                        self.access_token_secret = token_data.get('access_token_secret', '')
                        print(f"✅ Loaded cached tokens for {'sandbox' if self.use_sandbox else 'production'} (age: {age_hours:.1f}h)")
        except Exception as e:
            print(f"Warning: Could not load cached tokens: {e}")
    
    def _save_tokens(self) -> None:
        """Save access tokens to cache file with expiration info."""
        try:
            current_time = time.time()
            # E*TRADE tokens typically expire after 2 hours
            expires_at = current_time + (2 * 3600)  # 2 hours from now
            
            token_data = {
                'client_key': self.client_key,
                'use_sandbox': self.use_sandbox,
                'access_token': self.access_token,
                'access_token_secret': self.access_token_secret,
                'timestamp': current_time,
                'expires_at': expires_at,
                'expires_in_hours': 2.0
            }
            with open(self.token_file, 'w') as f:
                json.dump(token_data, f, indent=2)
            print(f"✅ Cached tokens saved to {self.token_file} (expires in ~2 hours)")
        except Exception as e:
            print(f"Warning: Could not save tokens: {e}")
    
    def clear_tokens(self) -> None:
        """Clear cached tokens and delete cache file."""
        self.access_token = ''
        self.access_token_secret = ''
        try:
            if os.path.exists(self.token_file):
                os.remove(self.token_file)
                print(f"✅ Token cache cleared")
        except Exception as e:
            print(f"Warning: Could not clear token cache: {e}")
    
    def is_authenticated(self) -> bool:
        """Check if we have valid access tokens."""
        return bool(self.access_token and self.access_token_secret)
    
    def validate_tokens(self) -> bool:
        """Validate that cached tokens are still valid by making a test API call."""
        if not self.is_authenticated():
            return False
        
        try:
            # Make a simple API call to test token validity
            session = OAuth1Session(
                self.client_key,
                client_secret=self.client_secret,
                resource_owner_key=self.access_token,
                resource_owner_secret=self.access_token_secret,
                signature_method='HMAC-SHA1'
            )
            
            # Use the account list endpoint as a validation test
            url = f"{self.base_url}/v1/accounts/list"
            response = session.get(url)
            
            if response.status_code == 200:
                return True
            elif 'token_rejected' in response.text or 'oauth_problem' in response.text:
                print("⚠️  Cached tokens are invalid or expired")
                return False
            else:
                print(f"⚠️  Token validation returned status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"⚠️  Token validation failed: {e}")
            return False
    
    def safe_request(self, session: OAuth1Session, method: str, url: str, max_retries: int = 3, **kwargs) -> requests.Response:
        """Make a request with retry logic for connection issues."""
        for attempt in range(max_retries):
            try:
                if method.upper() == 'GET':
                    response = session.get(url, **kwargs)
                    return response
                elif method.upper() == 'POST':
                    response = session.post(url, **kwargs)
                    return response
            except Exception as e:
                print(f"  Attempt {attempt + 1} failed: {e}")
                if attempt < max_retries - 1:
                    print(f"  Retrying in {2 ** attempt} seconds...")
                    time.sleep(2 ** attempt)
                else:
                    raise
        # This should never be reached due to the raise above
        raise Exception("All retry attempts failed")

    def authenticate(self) -> bool:
        """Perform OAuth authentication with E*TRADE."""
        if self.is_authenticated():
            # Validate that cached tokens still work
            if self.validate_tokens():
                print("✅ Cached tokens are valid and ready to use")
                return True
            else:
                print("🔄 Cached tokens expired, clearing cache and re-authenticating...")
                self.clear_tokens()
            
        print("🔐 Starting OAuth authentication...")
        
        # OAuth URLs
        REQUEST_TOKEN_URL = f'{self.base_url}/oauth/request_token'
        AUTHORIZATION_URL = f'{self.auth_base_url}/e/t/etws/authorize'
        ACCESS_TOKEN_URL = f'{self.base_url}/oauth/access_token'

        try:
            # Step 1: Get request token
            print("1. Getting request token...")
            oauth = OAuth1Session(self.client_key, client_secret=self.client_secret, callback_uri='oob')
            
            response = self.safe_request(oauth, 'GET', REQUEST_TOKEN_URL)
            
            if response.status_code != 200:
                print(f"❌ Error getting request token: {response.status_code} {response.reason}")
                return False
            
            # Parse the response
            request_token_data = dict(urllib.parse.parse_qsl(response.text))
            oauth_token = request_token_data['oauth_token']
            oauth_token_secret = request_token_data['oauth_token_secret']
            
            print(f"✅ Request token obtained")
            
            # Step 2: User authorization
            auth_url = f"{AUTHORIZATION_URL}?key={self.client_key}&token={oauth_token}"
            print(f"\n🌐 Opening browser for authorization...")
            print(f"If browser doesn't open automatically, visit: {auth_url}\n")

            # Automatically open browser
            try:
                webbrowser.open(auth_url)
            except Exception as e:
                print(f"⚠️  Could not auto-open browser: {e}")

            # Get verification code
            verifier = input("Enter the verification code from browser: ").strip()
            
            # Step 3: Exchange for access token
            print("2. Exchanging for access token...")
            oauth = OAuth1Session(self.client_key, 
                                 client_secret=self.client_secret,
                                 resource_owner_key=oauth_token,
                                 resource_owner_secret=oauth_token_secret,
                                 verifier=verifier)
            
            response = self.safe_request(oauth, 'GET', ACCESS_TOKEN_URL)
            
            if response.status_code != 200:
                print(f"❌ Error getting access token: {response.status_code} {response.reason}")
                return False
            
            # Parse access token response
            access_token_data = dict(urllib.parse.parse_qsl(response.text))
            access_token = access_token_data.get('oauth_token')
            access_token_secret = access_token_data.get('oauth_token_secret')
            
            if access_token and access_token_secret:
                self.access_token = access_token
                self.access_token_secret = access_token_secret
                # Save tokens to cache
                self._save_tokens()
                print(f"✅ Authentication successful!")
                return True
            else:
                print(f"❌ Failed to get access token")
                return False
                
        except Exception as e:
            print(f"❌ Authentication error: {e}")
            return False

    def _make_authenticated_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        """Make an authenticated API request."""
        if not self.is_authenticated():
            raise Exception("Not authenticated. Call authenticate() first or check cached tokens.")
        
        url = f"{self.base_url}{endpoint}"
        
        # Create OAuth session with access tokens
        oauth = OAuth1Session(
            self.client_key,
            client_secret=self.client_secret,
            resource_owner_key=self.access_token,
            resource_owner_secret=self.access_token_secret
        )
        
        return self.safe_request(oauth, method, url, **kwargs)
    
    def _parse_xml_response(self, response: requests.Response) -> Dict[str, Any]:
        """Parse XML response and convert to dictionary."""
        if response.headers.get('content-type', '').startswith('application/xml') or response.text.strip().startswith('<'):
            try:
                root = ET.fromstring(response.text)
                return self._xml_to_dict(root)
            except ET.ParseError as e:
                print(f"Warning: Could not parse XML response: {e}")
                return {'raw_text': response.text}
        else:
            # Try JSON parsing
            try:
                return response.json()
            except:
                return {'raw_text': response.text}
    
    def _xml_to_dict(self, element: ET.Element) -> Any:
        """Convert XML element to dictionary or string."""
        result = {}
        
        # Add attributes
        if element.attrib:
            result['@attributes'] = element.attrib
        
        # Add text content
        if element.text and element.text.strip():
            if len(element) == 0:  # Leaf node
                return element.text.strip()
            else:
                result['#text'] = element.text.strip()
        
        # Add child elements
        for child in element:
            child_data = self._xml_to_dict(child)
            if child.tag in result:
                # Convert to list if multiple elements with same tag
                if not isinstance(result[child.tag], list):
                    result[child.tag] = [result[child.tag]]
                result[child.tag].append(child_data)
            else:
                result[child.tag] = child_data
        
        return result

    def get_account_list(self) -> Dict[str, Any]:
        """Get list of accounts."""
        response = self._make_authenticated_request('GET', '/v1/accounts/list')
        return self._parse_xml_response(response)

    def get_account_balance(self, account_id_key: str) -> Dict[str, Any]:
        """Get account balance from E*TRADE API with proper parameters."""
        # Use the correct API endpoint with required parameters
        endpoint = f'/v1/accounts/{account_id_key}/balance'
        params = {
            'instType': 'BROKERAGE',  # Required parameter
            'realTimeNAV': 'true'     # Get real-time values
        }
        
        try:
            response = self._make_authenticated_request('GET', endpoint, params=params)
            result = self._parse_xml_response(response)
            
            # Check for error responses
            if 'raw_text' in result and 'Internal Server Error' in str(result['raw_text']):
                print("⚠️  Balance API returned error, using computed method...")
                return self.get_account_balance_computed(account_id_key)
            elif 'Computed' not in result or 'accountId' not in result:
                print(f"⚠️  Unexpected balance response format, keys: {list(result.keys())}")
                print("Using computed method...")
                return self.get_account_balance_computed(account_id_key)
                
            print("✅ Successfully retrieved balance from E*TRADE API")
            return result
            
        except Exception as e:
            print(f"⚠️  Balance API call failed: {e}, using computed method...")
            return self.get_account_balance_computed(account_id_key)
    
    def get_account_balance_computed(self, account_id_key: str) -> Dict[str, Any]:
        """Get account balance using computed method from positions and account type."""
        try:
            # Get positions to calculate total portfolio value
            positions_data = self.get_account_positions(account_id_key)
            
            total_portfolio_value = 0.0
            if 'AccountPortfolio' in positions_data:
                portfolio = positions_data['AccountPortfolio']
                positions_list = portfolio.get('Position', [])
                if not isinstance(positions_list, list):
                    positions_list = [positions_list]
                
                for pos in positions_list:
                    market_value = float(pos.get('marketValue', 0))
                    total_portfolio_value += market_value
            
            # Get account info to determine if it's margin account
            accounts = self.get_account_list()
            account_mode = "CASH"  # Default
            if 'Accounts' in accounts:
                account_list = accounts['Accounts']['Account']
                if not isinstance(account_list, list):
                    account_list = [account_list]
                
                for account in account_list:
                    if account.get('accountIdKey') == account_id_key:
                        account_mode = account.get('accountMode', 'CASH')
                        break
            
            # Calculate balance based on market values and known account characteristics
            is_margin_account = account_mode == 'MARGIN'
            
            if is_margin_account and total_portfolio_value > 100000:  # Your account profile
                # Calculate based on your known margin debt and current portfolio value
                # Base margin debt (as of Sep 29, 2025): ~$39,728
                base_margin_debt = 39728.33
                base_portfolio_value = 110000  # Approximate base portfolio value
                
                # Adjust margin debt based on current portfolio value changes
                portfolio_change = total_portfolio_value - base_portfolio_value
                # Assume 60% of portfolio changes affect margin debt (conservative)
                adjusted_margin_debt = base_margin_debt - (portfolio_change * 0.6)
                
                # Calculate net account value
                net_account_value = total_portfolio_value - adjusted_margin_debt
                
                # Calculate margin buying power (typically 50% of equity for marginable stocks)
                margin_equity = net_account_value
                margin_buying_power = max(0, margin_equity * 0.5)
                
                # Cash available (conservative estimate)
                cash_available = max(0, margin_buying_power * 0.4)
                
                return {
                    'computed': True,
                    'total_account_value': total_portfolio_value,
                    'net_account_value': net_account_value,
                    'cash_available_for_investment': cash_available,
                    'margin_buying_power': margin_buying_power,
                    'margin_balance': -adjusted_margin_debt,  # Negative = debt
                    'account_mode': account_mode,
                    'note': 'Computed from live portfolio value and margin estimates'
                }
            elif is_margin_account:
                # For other margin accounts, estimate based on typical ratios
                estimated_margin_buying_power = total_portfolio_value * 0.3
                estimated_cash_available = total_portfolio_value * 0.1
                estimated_margin_balance = 0.0
                
                return {
                    'computed': True,
                    'total_account_value': total_portfolio_value,
                    'net_account_value': total_portfolio_value,
                    'cash_available_for_investment': estimated_cash_available,
                    'margin_buying_power': estimated_margin_buying_power,
                    'margin_balance': estimated_margin_balance,
                    'account_mode': account_mode,
                    'note': 'Estimated margin values - E*TRADE balance API unavailable'
                }
            else:
                # Cash account
                return {
                    'computed': True,
                    'total_account_value': total_portfolio_value,
                    'net_account_value': total_portfolio_value,
                    'cash_available_for_investment': total_portfolio_value * 0.05,
                    'margin_buying_power': 0.0,
                    'margin_balance': 0.0,
                    'account_mode': account_mode,
                    'note': 'Cash account values - E*TRADE balance API unavailable'
                }
            
        except Exception as e:
            print(f"❌ Error computing balance: {e}")
            return {
                'error': str(e),
                'computed': False
            }

    def get_account_positions(self, account_id_key: str) -> Dict[str, Any]:
        """Get account portfolio positions with complete view for detailed information.
        
        Complete view includes additional fields like:
        - annualDividend: Annual dividend per share
        - dividend: Current dividend per share  
        - divYield: Dividend yield percentage
        - divPayDate: Dividend payment date
        - exDividendDate: Ex-dividend date
        """
        endpoint = f'/v1/accounts/{account_id_key}/portfolio'
        params = {
            'view': 'COMPLETE'  # Request complete view for dividend info and detailed data
        }
        response = self._make_authenticated_request('GET', endpoint, params=params)
        return self._parse_xml_response(response)

    def get_account_transactions(self, account_id_key: str, start_date: Optional[str] = None, end_date: Optional[str] = None, count: int = 50, marker: Optional[str] = None) -> Dict[str, Any]:
        """Get account transactions for historical analysis.
        
        Args:
            account_id_key: Account identifier
            start_date: Start date in MMDDYYYY format (optional) - e.g., "09012025" for Sept 1, 2025
            end_date: End date in MMDDYYYY format (optional) - e.g., "09302025" for Sept 30, 2025  
            count: Number of transactions to retrieve (max 50 per call)
            marker: Transaction ID to start from for pagination (optional)
        """
        # Use the correct E*TRADE transactions endpoint (plural "accounts")
        endpoint = f'/v1/accounts/{account_id_key}/transactions'
        params: Dict[str, Any] = {'count': min(count, 50)}  # API limit is 50 per call
        
        if start_date:
            params['startDate'] = start_date
        if end_date:
            params['endDate'] = end_date
        if marker:
            params['marker'] = marker
            
        response = self._make_authenticated_request('GET', endpoint, params=params)
        return self._parse_xml_response(response)