#!/usr/bin/env python3
"""
BTC Accumulation Bot - BTCMarkets API v3 Compliant (FIXED)
Fixed all API response format issues based on official documentation
"""

import base64
import hashlib
import hmac
import time
import json
import logging
import os
import requests
import numpy as np
from datetime import datetime
from typing import Dict, Tuple, Optional
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError


# Secure configuration using environment variables
class Config:
    # BTCMarkets API - Note: Using PRIVATE_KEY instead of SECRET for consistency with official client
    BTCMARKETS_API_KEY = os.getenv('BTCMARKETS_API_KEY')
    BTCMARKETS_PRIVATE_KEY = os.getenv('BTCMARKETS_PRIVATE_KEY')  # This is the API Secret

    # Bot settings
    BASE_WEEKLY_AMOUNT = float(os.getenv('BASE_WEEKLY_AMOUNT', '500.0'))
    MAX_WEEKLY_AMOUNT = float(os.getenv('MAX_WEEKLY_AMOUNT', '2000.0'))
    MIN_WEEKLY_AMOUNT = float(os.getenv('MIN_WEEKLY_AMOUNT', '100.0'))

    @classmethod
    def validate(cls):
        """Validate that all required environment variables are set"""
        required_vars = [
            'BTCMARKETS_API_KEY',
            'BTCMARKETS_PRIVATE_KEY'
        ]

        missing = []
        for var in required_vars:
            if not getattr(cls, var):
                missing.append(var)

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

        return True


# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/btc_bot_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)


class BTCMarketsClient:
    """Official BTCMarkets Python client implementation"""

    def __init__(self, api_key, private_key):
        self.base_url = 'https://api.btcmarkets.net'
        self.api_key = api_key
        self.private_key = base64.b64decode(private_key)

    def get_ticker(self, market_id='BTC-AUD'):
        """Get ticker for specific market"""
        return self.__make_http_call('GET', self.api_key, self.private_key, f'/v3/markets/{market_id}/ticker', None)

    def get_candles(self, market_id='BTC-AUD', timeWindow='1d', limit=200):
        """Get historical candle data"""
        query_string = f'timeWindow={timeWindow}&limit={limit}'
        return self.__make_http_call('GET', self.api_key, self.private_key, f'/v3/markets/{market_id}/candles',
                                     query_string)

    def get_account_balances(self):
        """Get account balances"""
        return self.__make_http_call('GET', self.api_key, self.private_key, '/v3/accounts/me/balances', '')

    def get_orders(self, status='all'):
        """Get orders with optional status filter"""
        query_string = f'status={status}' if status else ''
        return self.__make_http_call('GET', self.api_key, self.private_key, '/v3/orders', query_string)

    def place_market_buy_order(self, market_id, amount):
        """Place a market buy order

        Args:
            market_id: Market identifier (e.g., 'BTC-AUD')
            amount: Amount in base currency (BTC)
        """
        payload = {
            'marketId': market_id,
            'amount': str(amount),
            'type': 'Market',
            'side': 'Bid'  # Bid = Buy, Ask = Sell
        }
        return self.__make_http_call('POST', self.api_key, self.private_key, '/v3/orders', None, payload)

    def place_limit_buy_order(self, market_id, amount, price):
        """Place a limit buy order"""
        payload = {
            'marketId': market_id,
            'price': str(price),
            'amount': str(amount),
            'type': 'Limit',
            'side': 'Bid'
        }
        return self.__make_http_call('POST', self.api_key, self.private_key, '/v3/orders', None, payload)

    def cancel_order(self, order_id):
        """Cancel an order by ID"""
        query_string = f'id={order_id}'
        return self.__make_http_call('DELETE', self.api_key, self.private_key, '/v3/orders', query_string)

    def __make_http_call(self, method, apiKey, privateKey, path, queryString, data=None):
        """Make HTTP call to BTCMarkets API"""
        if data is not None:
            data = json.dumps(data, separators=(',', ':'))  # Compact JSON

        headers = self.___build_headers(method, apiKey, privateKey, path, data)

        if queryString is None:
            full_path = path
        else:
            full_path = path + '?' + queryString

        try:
            http_request = Request(self.base_url + full_path, None, headers, method=method)

            if method == 'POST' or method == 'PUT':
                if data:
                    response = urlopen(http_request, data=bytes(data, encoding="utf-8"))
                else:
                    response = urlopen(http_request)
            else:
                response = urlopen(http_request)

            response_data = json.loads(str(response.read(), "utf-8"))
            logging.debug(f"API Response: {method} {path} -> {response.code}")
            return response_data

        except HTTPError as e:
            try:
                error_data = json.loads(e.read().decode('utf-8'))
                if hasattr(e, 'code'):
                    error_data['statusCode'] = e.code
                logging.error(f"API HTTP Error: {e.code} - {error_data}")
                return error_data
            except:
                logging.error(f"API HTTP Error: {e.code} - {e.reason}")
                return {'error': f'HTTP {e.code}: {e.reason}', 'statusCode': e.code}

        except URLError as e:
            logging.error(f"API URL Error: {e}")
            return {'error': f'Network error: {e.reason}'}
        except Exception as e:
            logging.error(f"API Unexpected Error: {e}")
            return {'error': f'Unexpected error: {str(e)}'}

    def ___build_headers(self, method, api_key, private_key, path, data):
        """Build authentication headers"""
        now = str(int(time.time() * 1000))
        message = method + path + now
        if data is not None:
            message += data

        signature = self.__sign_message(private_key, message)
        headers = {
            "Accept": "application/json",
            "Accept-Charset": "UTF-8",
            "Content-Type": "application/json",
            "BM-AUTH-APIKEY": api_key,
            "BM-AUTH-TIMESTAMP": now,
            "BM-AUTH-SIGNATURE": signature,
            "User-Agent": "BTC-Accumulation-Bot/2.0"
        }
        return headers

    def __sign_message(self, private_key, message):
        """Sign message using HMAC-SHA512"""
        signature = base64.b64encode(hmac.new(
            private_key, message.encode('utf-8'), digestmod=hashlib.sha512).digest())
        signature = signature.decode('utf8')
        return signature


class BTCAccumulationBot:
    """BTC Accumulation Bot using proven BTCMarkets client"""

    def __init__(self):
        # Validate configuration on startup
        Config.validate()
        self.config = Config()
        self.client = BTCMarketsClient(self.config.BTCMARKETS_API_KEY, self.config.BTCMARKETS_PRIVATE_KEY)

        # Market configuration
        self.market_id = 'BTC-AUD'
        self.min_btc_order = 0.001  # Minimum BTC order size

    def get_current_price(self) -> float:
        """Get current BTC price"""
        try:
            ticker = self.client.get_ticker(self.market_id)

            # Check for API error
            if 'error' in ticker or 'statusCode' in ticker:
                raise Exception(f"API Error: {ticker.get('error', ticker)}")

            price = float(ticker['lastPrice'])
            logging.debug(f"Current BTC price: ${price:,.2f} AUD")
            return price

        except Exception as e:
            logging.error(f"Failed to get current price: {e}")
            raise

    def get_mayer_multiple(self) -> float:
        """Calculate Mayer Multiple using 200-day MA"""
        try:
            # Get 200 days of daily candles
            candles = self.client.get_candles(self.market_id, '1d', 200)

            # Check for API error
            if 'error' in candles or 'statusCode' in candles:
                raise Exception(f"Candles API Error: {candles.get('error', candles)}")

            if not candles or len(candles) == 0:
                raise Exception("No candle data received")

            # Extract closing prices (BTCMarkets returns newest first, so reverse)
            prices = [float(candle[4]) for candle in reversed(candles)]

            if len(prices) < 50:  # Need at least 50 days for meaningful MA
                raise Exception(f"Insufficient price data: only {len(prices)} days available")

            # Calculate 200-day moving average (or available data)
            ma_period = min(200, len(prices))
            ma_200 = np.mean(prices[-ma_period:])
            current_price = self.get_current_price()

            mayer_multiple = current_price / ma_200

            logging.info(f"📊 {ma_period}-day MA: ${ma_200:,.2f}")
            logging.info(f"📊 Current Price: ${current_price:,.2f}")
            logging.info(f"📊 Mayer Multiple: {mayer_multiple:.3f}")

            return mayer_multiple

        except Exception as e:
            logging.error(f"Failed to calculate Mayer Multiple: {e}")
            raise

    def get_fear_greed_index(self) -> int:
        """Get Fear & Greed Index with robust error handling"""
        try:
            url = "https://api.alternative.me/fng/"
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            data = response.json()
            fear_greed_value = int(data['data'][0]['value'])

            logging.info(f"😱 Fear & Greed Index: {fear_greed_value}")
            return fear_greed_value

        except requests.exceptions.Timeout:
            logging.warning("Fear & Greed Index timeout - using neutral value")
            return 50
        except requests.exceptions.RequestException as e:
            logging.warning(f"Fear & Greed Index network error: {e} - using neutral value")
            return 50
        except (KeyError, ValueError, IndexError) as e:
            logging.warning(f"Fear & Greed Index parse error: {e} - using neutral value")
            return 50
        except Exception as e:
            logging.warning(f"Fear & Greed Index unexpected error: {e} - using neutral value")
            return 50

    def calculate_buy_amount(self) -> Tuple[float, str]:
        """Calculate buy amount using Mayer Multiple + Fear & Greed strategy"""
        try:
            logging.info(f"calculate_buy_amount::maximum buy amount: ${self.config.MAX_WEEKLY_AMOUNT:.2f} AUD")
            logging.info(f"calculate_buy_amount::minimum buy amount: ${self.config.MIN_WEEKLY_AMOUNT:.2f} AUD")

            mayer = self.get_mayer_multiple()
            fear_greed = self.get_fear_greed_index()

            base_amount = self.config.BASE_WEEKLY_AMOUNT
            multiplier = 1.0

            # Enhanced Mayer Multiple + Fear & Greed strategy
            if mayer < 0.8 and fear_greed < 25:
                multiplier = 4.0  # Perfect storm
                signal = f"🚀 PERFECT STORM: Mayer {mayer:.3f} + F&G {fear_greed}"
            elif mayer < 0.8 and fear_greed < 35:
                multiplier = 3.5  # Extreme oversold with fear
                signal = f"🔥 EXTREME OVERSOLD + FEAR: Mayer {mayer:.3f} + F&G {fear_greed}"
            elif mayer < 0.8:
                multiplier = 3.0  # Extreme oversold
                signal = f"🔥 EXTREME OVERSOLD: Mayer {mayer:.3f}"
            elif mayer < 1.0 and fear_greed < 30:
                multiplier = 2.5  # Undersold + fear
                signal = f"💎 UNDERSOLD + FEAR: Mayer {mayer:.3f} + F&G {fear_greed}"
            elif mayer < 1.0:
                multiplier = 1.8  # Standard undersold
                signal = f"📈 UNDERSOLD: Mayer {mayer:.3f}"
            elif mayer < 1.2 and fear_greed < 40:
                multiplier = 1.2  # Fair value with some fear
                signal = f"⚖️ FAIR VALUE + FEAR: Mayer {mayer:.3f} + F&G {fear_greed}"
            elif mayer > 2.4:
                multiplier = 0.0  # Extreme bubble
                signal = f"🛑 EXTREME BUBBLE: Mayer {mayer:.3f} - STOP buying"
            elif mayer > 1.6:
                multiplier = 0.2  # Minimal buying when overbought
                signal = f"⚠️ OVERBOUGHT: Mayer {mayer:.3f}"
            else:
                signal = f"⚖️ FAIR VALUE: Mayer {mayer:.3f}"

            final_amount = base_amount * multiplier
            final_amount = max(min(final_amount, self.config.MAX_WEEKLY_AMOUNT),
                               self.config.MIN_WEEKLY_AMOUNT if multiplier > 0 else 0)

            logging.info(f"calculate_buy_amount:signal - {signal}")
            logging.info(f"💰 Calculated buy amount: ${final_amount:.2f} AUD (multiplier: {multiplier:.1f}x)")

            return final_amount, signal

        except Exception as e:
            logging.error(f"Failed to calculate buy amount: {e}")
            raise

    def get_account_balance(self) -> Dict[str, float]:
        """Get account balances - FIXED for correct API response format"""
        try:
            balances = self.client.get_account_balances()

            # Check for API error
            if 'error' in balances or 'statusCode' in balances:
                raise Exception(f"Balance API Error: {balances.get('error', balances)}")

            # BTCMarkets v3 API returns array of balance objects with this format:
            # [
            #   {
            #     "assetName": "LTC",
            #     "balance": "5",
            #     "available": "5",
            #     "locked": "0"
            #   },
            #   {
            #     "assetName": "ETH",
            #     "balance": "1.07583642",
            #     "available": "1.0",
            #     "locked": "0.07583642"
            #   }
            # ]

            if not isinstance(balances, list):
                logging.error(f"Unexpected balance response format: {type(balances)} - {balances}")
                return {}

            balance_info = {}

            for balance in balances:
                # Check if balance item has expected structure
                if not isinstance(balance, dict):
                    logging.warning(f"Unexpected balance item format: {type(balance)} - {balance}")
                    continue

                # Extract asset name and available balance
                asset_name = balance.get('assetName')
                available_balance = balance.get('available', balance.get('balance', '0'))

                if asset_name and available_balance is not None:
                    try:
                        balance_info[asset_name] = float(available_balance)
                        logging.debug(f"Parsed balance: {asset_name} = {available_balance}")
                    except (ValueError, TypeError) as e:
                        logging.warning(f"Could not parse balance for {asset_name}: {available_balance} - {e}")
                        balance_info[asset_name] = 0.0
                else:
                    logging.warning(f"Missing required fields in balance item: {balance}")

            logging.info(f"✅ Successfully parsed {len(balance_info)} account balances")
            logging.debug(f"Balances: {balance_info}")
            return balance_info

        except Exception as e:
            logging.error(f"Error getting account balance: {str(e)}")
            logging.error(f"Exception type: {type(e).__name__}")
            return {}

    def execute_buy_order(self, amount_aud: float) -> Dict:
        """Execute market buy order using official client"""
        if amount_aud < self.config.MIN_WEEKLY_AMOUNT:
            logging.info(f"Amount ${amount_aud:.2f} below minimum ${self.config.MIN_WEEKLY_AMOUNT}, skipping")
            return {'success': False, 'reason': 'Amount below minimum'}

        try:
            # Check account balance first
            balances = self.get_account_balance()
            aud_balance = balances.get('AUD', 0)

            if aud_balance < amount_aud:
                logging.warning(f"Insufficient AUD balance: ${aud_balance:.2f} < ${amount_aud:.2f}")
                return {'success': False, 'reason': f'Insufficient balance: ${aud_balance:.2f}'}

            # Get current price for amount calculation
            current_price = self.get_current_price()
            btc_amount = amount_aud / current_price

            # Validate minimum order size
            # if btc_amount < self.min_btc_order:
            #     logging.warning(f"BTC amount {btc_amount:.8f} below minimum {self.min_btc_order} BTC")
            #     return {'success': False, 'reason': f'Order too small: {btc_amount:.8f} BTC < {self.min_btc_order} BTC'}

            # Place market buy order using official client
            logging.info(f"🔄 Placing market buy order: {btc_amount:.8f} BTC (~${amount_aud:.2f} AUD)")

            order_result = self.client.place_market_buy_order(self.market_id, f"{btc_amount:.8f}")

            # Check for order errors
            if 'error' in order_result or 'statusCode' in order_result:
                error_msg = order_result.get('error', f"HTTP {order_result.get('statusCode')}")
                logging.error(f"❌ Order failed: {error_msg}")
                return {'success': False, 'reason': error_msg}

            # Log successful order
            order_id = order_result.get('orderId', 'N/A')
            order_status = order_result.get('status', 'Unknown')

            logging.info(f"✅ Order placed successfully!")
            logging.info(f"📋 Order ID: {order_id}")
            logging.info(f"📊 Status: {order_status}")
            logging.info(f"📦 Amount: {btc_amount:.8f} BTC")
            logging.info(f"💵 Estimated Cost: ${amount_aud:.2f} AUD")
            logging.info(f"📈 Price: ${current_price:,.2f} AUD")

            return {
                'success': True,
                'btc_amount': btc_amount,
                'aud_amount': amount_aud,
                'order_id': order_id,
                'order_status': order_status,
                'price': current_price,
                'order_details': order_result
            }

        except Exception as e:
            logging.error(f"❌ Order execution error: {str(e)}")
            return {'success': False, 'reason': str(e)}

    def get_portfolio_summary(self) -> Optional[Dict]:
        """Get portfolio summary with error handling"""
        try:
            balances = self.get_account_balance()
            current_price = self.get_current_price()

            btc_balance = balances.get('BTC', 0)
            aud_balance = balances.get('AUD', 0)
            btc_value_aud = btc_balance * current_price
            total_portfolio = btc_value_aud + aud_balance

            return {
                'btc_balance': btc_balance,
                'btc_value_aud': btc_value_aud,
                'aud_balance': aud_balance,
                'total_portfolio_aud': total_portfolio,
                'current_btc_price': current_price
            }
        except Exception as e:
            logging.error(f"Error getting portfolio summary: {str(e)}")
            return None

    def test_api_connection(self) -> bool:
        """Test API connection and credentials"""
        try:
            logging.info("🔍 Testing API connection...")

            # Test public endpoint (ticker)
            ticker = self.client.get_ticker(self.market_id)
            if 'error' in ticker or 'statusCode' in ticker:
                logging.error(f"❌ Public API test failed: {ticker}")
                return False

            # Test private endpoint (balances)
            balances = self.client.get_account_balances()
            if 'error' in balances or 'statusCode' in balances:
                logging.error(f"❌ Private API test failed: {balances}")
                return False

            # Log balance test results
            if isinstance(balances, list) and len(balances) > 0:
                logging.info(f"✅ API connection test successful - found {len(balances)} asset balances")
            else:
                logging.warning("⚠️ API connection successful but no balances found")

            return True

        except Exception as e:
            logging.error(f"❌ API connection test failed: {e}")
            return False

    def run(self):
        """Main execution function with comprehensive error handling"""
        logging.info("=" * 70)
        logging.info("🚀 BTC Accumulation Bot v3.1 - FIXED API Integration")
        logging.info(f"⏰ Execution Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S AEST')}")
        logging.info(f"🎯 Market: {self.market_id}")
        logging.info("=" * 70)

        try:
            # Test API connection first
            if not self.test_api_connection():
                raise Exception("API connection test failed")

            # Get current metrics
            logging.info("📊 Calculating market signals...")
            buy_amount, signal = self.calculate_buy_amount()

            current_price = self.get_current_price()
            logging.info(f"💰 Current BTC Price: ${current_price:,.2f} AUD")

            # Get portfolio summary
            portfolio = self.get_portfolio_summary()
            if portfolio:
                logging.info("-" * 50)
                logging.info("📋 CURRENT PORTFOLIO")
                logging.info(f"🪙 BTC Holdings: {portfolio['btc_balance']:.8f} BTC")
                logging.info(f"💰 BTC Value: ${portfolio['btc_value_aud']:,.2f} AUD")
                logging.info(f"💵 AUD Balance: ${portfolio['aud_balance']:,.2f} AUD")
                logging.info(f"📈 Total Portfolio: ${portfolio['total_portfolio_aud']:,.2f} AUD")
                logging.info("-" * 50)

            # Execute strategy
            if buy_amount > 0:
                logging.info("🎯 EXECUTING BUY STRATEGY")
                result = self.execute_buy_order(buy_amount)

                if result['success']:
                    logging.info("=" * 50)
                    logging.info("✅ BTC PURCHASE SUCCESSFUL!")
                    logging.info(f"📦 Purchased: {result['btc_amount']:.8f} BTC")
                    logging.info(f"💵 Amount: ${result['aud_amount']:.2f} AUD")
                    logging.info(f"📊 Price: ${result['price']:,.2f} AUD")
                    logging.info(f"🔗 Order ID: {result.get('order_id', 'N/A')}")
                    logging.info(f"📊 Status: {result.get('order_status', 'N/A')}")
                    logging.info("=" * 50)
                else:
                    logging.error("=" * 50)
                    logging.error("❌ BTC PURCHASE FAILED!")
                    logging.error(f"🚨 Reason: {result['reason']}")
                    logging.error("=" * 50)
            else:
                logging.info("=" * 50)
                logging.info("⏸️ NO PURCHASE TODAY")
                logging.info("🎯 Strategy: Waiting for better entry point")
                logging.info("📊 The bot is working correctly - patience pays off!")
                logging.info("=" * 50)

            # Final portfolio summary
            final_portfolio = self.get_portfolio_summary()
            if final_portfolio:
                logging.info("-" * 50)
                logging.info("📋 FINAL PORTFOLIO SUMMARY")
                logging.info(f"🪙 BTC: {final_portfolio['btc_balance']:.8f} BTC")
                logging.info(f"💰 BTC Value: ${final_portfolio['btc_value_aud']:,.2f} AUD")
                logging.info(f"💵 AUD: ${final_portfolio['aud_balance']:,.2f} AUD")
                logging.info(f"📊 Total: ${final_portfolio['total_portfolio_aud']:,.2f} AUD")
                logging.info("-" * 50)

        except Exception as e:
            logging.error("=" * 50)
            logging.error("🚨 CRITICAL ERROR!")
            logging.error(f"Error Type: {type(e).__name__}")
            logging.error(f"Error Message: {str(e)}")
            logging.error("Please check the configuration and API credentials.")
            logging.error("=" * 50)
            raise

        logging.info("🏁 Bot execution completed successfully")
        logging.info("=" * 70)


if __name__ == "__main__":
    # Create logs directory if it doesn't exist
    os.makedirs('logs', exist_ok=True)

    try:
        # Run the bot
        bot = BTCAccumulationBot()
        bot.run()
    except KeyboardInterrupt:
        logging.info("🛑 Bot execution interrupted by user")
    except Exception as e:
        logging.error(f"🚨 Fatal error: {e}")
        raise