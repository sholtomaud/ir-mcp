import sys
import os
import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ir_client import IndependentReserveWebSocketClient

class TestIndependentReserveWebSocketClient(unittest.TestCase):
    def setUp(self):
        self.client = IndependentReserveWebSocketClient()

    def test_handle_messages(self):
        async def run_test():
            messages = [
                {"n": "ticker-xbt-usd", "o": {"PrimaryCurrencyCode": "Xbt", "SecondaryCurrencyCode": "Usd", "LastPrice": 50000.0}},
                {"n": "orderbook-eth-aud", "o": {"PrimaryCurrencyCode": "Eth", "SecondaryCurrencyCode": "Aud", "BuyOrders": [{"Price": 3000, "Volume": 10}]}},
                {"n": "recenttrades-btc-usd", "o": {"PrimaryCurrencyCode": "Btc", "SecondaryCurrencyCode": "Usd", "Trades": [{"Price": 60000, "Volume": 0.5}]}},
                {"e": "error", "o": "Invalid currency pair"},
            ]

            for msg in messages:
                await self.client._handle_message(msg)

            # Check that the data was cached correctly
            self.assertIn("xbtusd", self.client.tickers)
            self.assertEqual(self.client.tickers["xbtusd"]["LastPrice"], 50000.0)

            self.assertIn("ethaud", self.client.order_books)
            self.assertEqual(self.client.order_books["ethaud"]["BuyOrders"][0]["Price"], 3000)

            self.assertIn("btcusd", self.client.recent_trades)
            self.assertEqual(self.client.recent_trades["btcusd"]["Trades"][0]["Price"], 60000)

        asyncio.run(run_test())

if __name__ == '__main__':
    unittest.main()
